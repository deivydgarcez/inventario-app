from fastapi import APIRouter, Depends, HTTPException, status
from app.database import get_connection, fetchall_as_dict, fetchone_as_dict
from app.security import get_current_user
from app.models.schemas import OperadorResponse, OperadorRequest

router = APIRouter(prefix="/operadores", tags=["Operadores"])


@router.get("", response_model=list[OperadorResponse])
def listar_operadores(current_user: dict = Depends(get_current_user)):
    with get_connection() as con:
        cur = con.cursor()
        cur.execute("SELECT ID, NOME, ATIVO FROM OPERADORES_APP ORDER BY NOME")
        return fetchall_as_dict(cur)


def _exige_gerente(current_user: dict):
    if (current_user.get("idgrupo") or 3) not in (1, 2):
        raise HTTPException(status_code=403, detail="Apenas gerentes e administradores podem gerenciar operadores")


@router.post("", response_model=OperadorResponse, status_code=201)
def criar_operador(
    body: OperadorRequest,
    current_user: dict = Depends(get_current_user),
):
    _exige_gerente(current_user)
    with get_connection() as con:
        cur = con.cursor()
        cur.execute(
            "INSERT INTO OPERADORES_APP (NOME, ATIVO) VALUES (?, 1) RETURNING ID, NOME, ATIVO",
            (body.nome.strip(),),
        )
        row = fetchone_as_dict(cur)
    return row


@router.put("/{operador_id}/toggle", response_model=OperadorResponse)
def toggle_operador(
    operador_id: int,
    current_user: dict = Depends(get_current_user),
):
    _exige_gerente(current_user)
    with get_connection() as con:
        cur = con.cursor()
        cur.execute(
            "UPDATE OPERADORES_APP SET ATIVO = CASE WHEN ATIVO = 1 THEN 0 ELSE 1 END "
            "WHERE ID = ? RETURNING ID, NOME, ATIVO",
            (operador_id,),
        )
        row = fetchone_as_dict(cur)
        if not row:
            raise HTTPException(status_code=404, detail="Operador não encontrado")
    return row
