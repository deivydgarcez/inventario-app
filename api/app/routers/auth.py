import time
import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, status
from app.database import get_connection, fetchall_as_dict, fetchone_as_dict
from app.security import create_token, get_current_user
from app.models.schemas import LoginRequest, TokenResponse, UsuarioMobile, SenhaMobileRequest

router = APIRouter(prefix="/auth", tags=["Autenticação"])

_ROLES = {1: "admin", 2: "gerente", 3: "operador"}
MI_LOGIN = "MI"

# Burst protection em memória (sobrevive apenas enquanto o serviço está rodando)
_tentativas: dict[str, list[float]] = {}
_bloqueados: dict[str, float] = {}
MAX_TENTATIVAS_BURST = 5
JANELA_BURST_SEGUNDOS = 60
BLOQUEIO_BURST_SEGUNDOS = 60

# Bloqueio gradativo persistente no banco
# (limiar de falhas nas últimas 2h → segundos de bloqueio)
_ESCALAS = [
    (7,  7 * 60),
    (6,  6 * 60),
    (5,  5 * 60),
    (4,  4 * 60),
    (3,  3 * 60),
    (2,  2 * 60),
    (1,  1 * 60),
]
_JANELA_CONTAGEM_MIN = 120


def _duracao_bloqueio(total_falhas: int) -> int:
    for limiar, duracao in _ESCALAS:
        if total_falhas >= limiar:
            return duracao
    return 0


def _fmt_restante(segundos: int) -> str:
    if segundos >= 60:
        return f"{segundos // 60} minuto(s)"
    return f"{segundos} segundo(s)"


def _role(idgrupo):
    return _ROLES.get(idgrupo or 3, "operador")


def _is_mi(user: dict) -> bool:
    return user.get("login", "").upper() == MI_LOGIN


def _pode_gerir(user: dict) -> bool:
    return _is_mi(user) or user.get("mobile_admin") == 1


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, request: Request):
    ip = request.client.host if request.client else "unknown"
    user_key = f"user:{body.login.lower()}"
    agora = time.time()

    def _checar_burst(chave: str):
        if chave in _bloqueados:
            if agora < _bloqueados[chave]:
                restante = int(_bloqueados[chave] - agora)
                raise HTTPException(
                    status_code=429,
                    detail=f"Muitas tentativas incorretas. Aguarde {_fmt_restante(restante)}.",
                )
            del _bloqueados[chave]
            _tentativas.pop(chave, None)

    _checar_burst(ip)
    _checar_burst(user_key)

    # Bloqueio gradativo persistente no banco (sobrevive a reinicialização do serviço)
    try:
        with get_connection() as con:
            cur = con.cursor()
            cur.execute(
                "SELECT COUNT(*), MAX(DATA_HORA) FROM LOG_INVENTARIO "
                "WHERE TIPO = 'LOGIN_FALHOU' AND LOGIN_USUARIO = ? "
                "AND DATA_HORA > DATEADD(MINUTE, ?, CURRENT_TIMESTAMP)",
                (body.login.lower(), -_JANELA_CONTAGEM_MIN),
            )
            row = cur.fetchone()
            total_falhas = row[0] or 0
            ultima_falha: datetime.datetime | None = row[1]

        duracao = _duracao_bloqueio(total_falhas)
        if duracao > 0 and ultima_falha:
            segundos_passados = (datetime.datetime.now() - ultima_falha).total_seconds()
            if segundos_passados < duracao:
                restante = int(duracao - segundos_passados)
                raise HTTPException(
                    status_code=429,
                    detail=f"Muitas tentativas incorretas. Aguarde {_fmt_restante(restante)}.",
                )
    except HTTPException:
        raise
    except Exception:
        pass

    # Limpa entradas antigas de memória para evitar vazamento
    for chave in (ip, user_key):
        _tentativas[chave] = [t for t in _tentativas.get(chave, []) if agora - t < JANELA_BURST_SEGUNDOS]
        if not _tentativas[chave]:
            _tentativas.pop(chave, None)

    with get_connection() as con:
        cur = con.cursor()
        cur.execute(
            "SELECT IDUSUARIO, LOGIN, NOMECOMPLETO, IDGRUPO, "
            "COALESCE(MOBILE_ADMIN, 0) AS MOBILE_ADMIN "
            "FROM USUARIOS "
            "WHERE LOWER(LOGIN) = LOWER(?) "
            "AND (SENHAMOBILE = ? OR SENHA = ?) "
            "AND (INATIVO IS NULL OR INATIVO = 0)",
            (body.login, body.senha, body.senha),
        )
        user = fetchone_as_dict(cur)

    if not user:
        for chave in (ip, user_key):
            _tentativas.setdefault(chave, []).append(agora)
            if len(_tentativas[chave]) >= MAX_TENTATIVAS_BURST:
                _bloqueados[chave] = agora + BLOQUEIO_BURST_SEGUNDOS
                _tentativas.pop(chave, None)
        # SEC-3: grava falha no banco — persiste entre reinicios do serviço
        try:
            with get_connection() as log_con:
                log_con.cursor().execute(
                    "INSERT INTO LOG_INVENTARIO (TIPO, LOGIN_USUARIO, MOTIVO, DATA_HORA) "
                    "VALUES ('LOGIN_FALHOU', ?, ?, CURRENT_TIMESTAMP)",
                    (body.login.lower(), f"IP: {ip}"),
                )
        except Exception:
            pass
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Login ou senha inválidos")

    for chave in (ip, user_key):
        _tentativas.pop(chave, None)
        _bloqueados.pop(chave, None)

    # Limpa falhas da janela de contagem ao logar com sucesso (zera a escala gradativa)
    try:
        with get_connection() as log_con:
            log_con.cursor().execute(
                "DELETE FROM LOG_INVENTARIO "
                "WHERE TIPO = 'LOGIN_FALHOU' AND LOGIN_USUARIO = ? "
                "AND DATA_HORA > DATEADD(MINUTE, ?, CURRENT_TIMESTAMP)",
                (body.login.lower(), -_JANELA_CONTAGEM_MIN),
            )
    except Exception:
        pass

    is_mi = user["login"].upper() == MI_LOGIN
    mobile_admin = 1 if is_mi else (user.get("mobile_admin") or 0)
    role = _role(user["idgrupo"])

    token = create_token({
        "sub": str(user["idusuario"]),
        "login": user["login"],
        "role": role,
        "idgrupo": user["idgrupo"] or 3,
        "mobile_admin": mobile_admin,
    })
    return TokenResponse(
        access_token=token,
        usuario=user["login"],
        nome=user["nomecompleto"] or user["login"],
        role=role,
        mobile_admin=mobile_admin,
    )


@router.get("/usuarios", response_model=list[UsuarioMobile])
def listar_usuarios(current_user: dict = Depends(get_current_user)):
    if not _pode_gerir(current_user):
        raise HTTPException(status_code=403, detail="Sem permissão")
    with get_connection() as con:
        cur = con.cursor()
        cur.execute(
            "SELECT IDUSUARIO, LOGIN, NOMECOMPLETO, IDGRUPO, INATIVO, "
            "CASE WHEN SENHAMOBILE IS NOT NULL AND SENHAMOBILE <> '' THEN 1 ELSE 0 END AS TEM_MOBILE, "
            "COALESCE(MOBILE_ADMIN, 0) AS MOBILE_ADMIN "
            "FROM USUARIOS WHERE LOGIN IS NOT NULL "
            "AND (INATIVO IS NULL OR INATIVO = 0) "
            "ORDER BY IDGRUPO, LOGIN"
        )
        return fetchall_as_dict(cur)


@router.put("/usuarios/{idusuario}/senha-mobile")
def definir_senha_mobile(
    idusuario: int,
    body: SenhaMobileRequest,
    current_user: dict = Depends(get_current_user),
):
    if not _pode_gerir(current_user):
        raise HTTPException(status_code=403, detail="Sem permissão")
    with get_connection() as con:
        cur = con.cursor()
        cur.execute("SELECT LOGIN FROM USUARIOS WHERE IDUSUARIO = ?", (idusuario,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
        if row[0].upper() == MI_LOGIN and not _is_mi(current_user):
            raise HTTPException(status_code=403, detail="Usuário MI não pode ser alterado")
        cur.execute(
            "UPDATE USUARIOS SET SENHAMOBILE = ? WHERE IDUSUARIO = ?",
            (body.senha or None, idusuario),
        )
    return {"mensagem": "Senha mobile atualizada"}


@router.put("/usuarios/{idusuario}/toggle-admin")
def toggle_admin_mobile(
    idusuario: int,
    current_user: dict = Depends(get_current_user),
):
    if not _is_mi(current_user):
        raise HTTPException(status_code=403, detail="Apenas o usuário MI pode delegar administração")
    with get_connection() as con:
        cur = con.cursor()
        cur.execute(
            "SELECT LOGIN, COALESCE(MOBILE_ADMIN, 0) FROM USUARIOS WHERE IDUSUARIO = ?",
            (idusuario,),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
        if row[0].upper() == MI_LOGIN:
            raise HTTPException(status_code=400, detail="Não é possível alterar o usuário MI")
        novo = 0 if row[1] == 1 else 1
        cur.execute(
            "UPDATE USUARIOS SET MOBILE_ADMIN = ? WHERE IDUSUARIO = ?",
            (novo, idusuario),
        )
    return {"mobile_admin": novo}
