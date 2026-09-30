from fastapi import APIRouter, Depends, HTTPException
from app.database import get_connection, fetchall_as_dict
from app.security import get_current_user
from app.models.schemas import DispositivoResponse
from app.notificacoes import notificar_dispositivo_removido

router = APIRouter(prefix="/admin", tags=["Dispositivos"])

_MI_LOGIN = "MI"


def _pode_gerir(current_user: dict) -> bool:
    return (
        current_user.get("login", "").upper() == _MI_LOGIN
        or current_user.get("mobile_admin") == 1
    )


@router.get("/dispositivos", response_model=list[DispositivoResponse])
def listar_dispositivos(current_user: dict = Depends(get_current_user)):
    if not _pode_gerir(current_user):
        raise HTTPException(status_code=403, detail="Sem permissão")
    with get_connection() as con:
        cur = con.cursor()
        cur.execute(
            "SELECT ID, DEVICE_ID, NOME_DISPOSITIVO, PRIMEIRO_ACESSO, ULTIMO_ACESSO "
            "FROM DISPOSITIVOS_AUTORIZADOS "
            "ORDER BY ULTIMO_ACESSO DESC"
        )
        return fetchall_as_dict(cur)


@router.delete("/dispositivos/{dispositivo_id}")
def remover_dispositivo(
    dispositivo_id: int,
    current_user: dict = Depends(get_current_user),
):
    if not _pode_gerir(current_user):
        raise HTTPException(status_code=403, detail="Sem permissão")
    with get_connection() as con:
        cur = con.cursor()
        cur.execute(
            "SELECT ID, DEVICE_ID, NOME_DISPOSITIVO FROM DISPOSITIVOS_AUTORIZADOS WHERE ID = ?",
            (dispositivo_id,)
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Dispositivo não encontrado")
        _, device_id, device_name = row
        cur.execute(
            "DELETE FROM DISPOSITIVOS_AUTORIZADOS WHERE ID = ?",
            (dispositivo_id,)
        )
    notificar_dispositivo_removido(device_id, device_name or "", current_user.get("login", ""))
    return {"mensagem": "Dispositivo removido"}
