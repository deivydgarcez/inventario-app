from fastapi import APIRouter, Depends
from app.database import get_connection, fetchall_as_dict
from app.security import get_current_user
from app.models.schemas import DepositoResponse

router = APIRouter(prefix="/depositos", tags=["Depósitos"])


@router.get("", response_model=list[DepositoResponse])
def listar_depositos(current_user: dict = Depends(get_current_user)):
    with get_connection() as con:
        cur = con.cursor()
        cur.execute(
            """
            SELECT CDDEPOSITO, DEPOSITO
            FROM DEPOSITO
            WHERE INATIVO = 0 OR INATIVO IS NULL
            ORDER BY DEPOSITO
            """
        )
        return fetchall_as_dict(cur)
