from fastapi import APIRouter, Depends, HTTPException
from app.database import get_connection, fetchall_as_dict, fetchone_as_dict
from app.security import get_current_user
from app.models.schemas import IniciarSessaoRequest, SessaoResponse

router = APIRouter(prefix="/sessao", tags=["Sessão Offline"])


@router.post("/iniciar", response_model=SessaoResponse)
def iniciar_sessao(
    body: IniciarSessaoRequest,
    current_user: dict = Depends(get_current_user),
):
    """Registra uma sessão de inventário offline. Idempotente: retorna a existente se já criada.
    FRAUDE-4: registra log se há outras sessões ABERTA para o mesmo depósito."""
    with get_connection() as con:
        cur = con.cursor()
        cur.execute(
            "SELECT SESSION_ID, CDDEPOSITO, OPERADOR, USUARIO, STATUS, INICIO "
            "FROM INVENTARIO_SESSAO WHERE SESSION_ID = ?",
            (body.session_id,),
        )
        row = fetchone_as_dict(cur)
        if row:
            return SessaoResponse(**row)

        # FRAUDE-4: verifica sessões paralelas antes de criar a nova
        cur.execute(
            "SELECT COUNT(*) FROM INVENTARIO_SESSAO "
            "WHERE CDDEPOSITO = ? AND STATUS = 'ABERTA' AND SESSION_ID <> ?",
            (body.cddeposito, body.session_id),
        )
        paralelas = cur.fetchone()[0] or 0

        cur.execute(
            "INSERT INTO INVENTARIO_SESSAO (SESSION_ID, CDDEPOSITO, OPERADOR, USUARIO, STATUS) "
            "VALUES (?, ?, ?, ?, 'ABERTA')",
            (body.session_id, body.cddeposito, body.operador, current_user.get("login", "")),
        )

        if paralelas > 0:
            try:
                cur.execute(
                    """
                    INSERT INTO LOG_INVENTARIO
                        (TIPO, CDDEPOSITO, OPERADOR, LOGIN_USUARIO, MOTIVO, SESSION_ID, DATA_HORA)
                    VALUES ('ALERTA', ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    (body.cddeposito, body.operador, current_user.get("login", ""),
                     f"Nova sessão iniciada com {paralelas} sessão(ões) ainda ABERTA(s) para o depósito",
                     body.session_id),
                )
            except Exception:
                pass

    with get_connection() as con:
        cur = con.cursor()
        cur.execute(
            "SELECT SESSION_ID, CDDEPOSITO, OPERADOR, USUARIO, STATUS, INICIO "
            "FROM INVENTARIO_SESSAO WHERE SESSION_ID = ?",
            (body.session_id,),
        )
        result = fetchone_as_dict(cur)
        if not result:
            raise HTTPException(status_code=500, detail="Erro ao criar sessão")
        return SessaoResponse(**result)


@router.post("/{session_id}/encerrar")
def encerrar_sessao(
    session_id: str,
    current_user: dict = Depends(get_current_user),
):
    """BUG-2: Encerra sessão sem consolidar (abandono). Garante que o STATUS não fica ABERTA indefinidamente."""
    with get_connection() as con:
        cur = con.cursor()
        cur.execute(
            "UPDATE INVENTARIO_SESSAO SET STATUS = 'ENCERRADA', FIM = CURRENT_TIMESTAMP "
            "WHERE SESSION_ID = ? AND STATUS = 'ABERTA'",
            (session_id,),
        )
        if cur.rowcount == 0:
            cur.execute(
                "SELECT STATUS FROM INVENTARIO_SESSAO WHERE SESSION_ID = ?",
                (session_id,),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Sessão não encontrada")
            return {"mensagem": f"Sessão já está com status '{row[0]}'"}

    try:
        from app.routers.inventario import _registrar_log
        _registrar_log(
            "ENCERRAMENTO",
            login_usuario=current_user.get("login", ""),
            motivo="Sessão encerrada pelo dispositivo sem consolidação",
            session_id=session_id,
        )
    except Exception:
        pass

    return {"mensagem": "Sessão encerrada"}


@router.get("/{cddeposito}", response_model=list[SessaoResponse])
def listar_sessoes(
    cddeposito: int,
    current_user: dict = Depends(get_current_user),
):
    """Lista sessões abertas para o depósito (de todos os dispositivos)."""
    with get_connection() as con:
        cur = con.cursor()
        cur.execute(
            "SELECT SESSION_ID, CDDEPOSITO, OPERADOR, USUARIO, STATUS, INICIO "
            "FROM INVENTARIO_SESSAO "
            "WHERE CDDEPOSITO = ? AND STATUS = 'ABERTA' "
            "ORDER BY INICIO DESC",
            (cddeposito,),
        )
        return fetchall_as_dict(cur)
