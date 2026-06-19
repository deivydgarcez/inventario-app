import time
from fastapi import APIRouter, Depends, HTTPException, Request, status
from app.database import get_connection, fetchall_as_dict, fetchone_as_dict
from app.security import create_token, get_current_user
from app.models.schemas import LoginRequest, TokenResponse, UsuarioMobile, SenhaMobileRequest

router = APIRouter(prefix="/auth", tags=["Autenticação"])

_ROLES = {1: "admin", 2: "gerente", 3: "operador"}
MI_LOGIN = "MI"

_tentativas: dict[str, list[float]] = {}   # chave: IP ou "user:LOGIN"
_bloqueados: dict[str, float] = {}         # chave: IP ou "user:LOGIN"
MAX_TENTATIVAS = 5
JANELA_SEGUNDOS = 60
BLOQUEIO_SEGUNDOS = 300


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

    def _checar_bloqueio(chave: str):
        if chave in _bloqueados:
            if agora < _bloqueados[chave]:
                restante = int(_bloqueados[chave] - agora)
                raise HTTPException(
                    status_code=429,
                    detail=f"Muitas tentativas incorretas. Tente novamente em {restante} segundos.",
                )
            del _bloqueados[chave]
            _tentativas.pop(chave, None)

    _checar_bloqueio(ip)
    _checar_bloqueio(user_key)

    # Limpa entradas antigas para evitar vazamento de memória
    for chave in (ip, user_key):
        _tentativas[chave] = [t for t in _tentativas.get(chave, []) if agora - t < JANELA_SEGUNDOS]
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
            if len(_tentativas[chave]) >= MAX_TENTATIVAS:
                _bloqueados[chave] = agora + BLOQUEIO_SEGUNDOS
                _tentativas.pop(chave, None)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Login ou senha inválidos")

    for chave in (ip, user_key):
        _tentativas.pop(chave, None)
        _bloqueados.pop(chave, None)

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
