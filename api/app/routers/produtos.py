from fastapi import APIRouter, Depends, HTTPException, status, Query
from app.database import get_connection, fetchone_as_dict, fetchall_as_dict
from app.security import get_current_user
from app.models.schemas import ProdutoResponse

router = APIRouter(prefix="/produtos", tags=["Produtos"])


@router.get("/barcode/{codigo}", response_model=ProdutoResponse)
def buscar_por_barcode(
    codigo: str,
    cddeposito: int = Query(..., description="Depósito para consultar estoque"),
    current_user: dict = Depends(get_current_user),
):
    with get_connection() as con:
        cur = con.cursor()
        cur.execute(
            """
            SELECT FIRST 1
                P.CDPRODUTO,
                P.PRODUTO,
                P.CODIGOBARRA,
                M.QTDEATUAL
            FROM PRODUTO P
            LEFT JOIN MOVIMENTO M
                ON M.CDPRODUTO = CAST(P.CDPRODUTO AS VARCHAR(10))
               AND M.CDDEPOSITO = ?
            WHERE P.CODIGOBARRA = ?
              AND (P.INATIVO IS NULL OR P.INATIVO = 0)
            """,
            (cddeposito, codigo),
        )
        produto = fetchone_as_dict(cur)

        if not produto:
            cur.execute(
                """
                SELECT FIRST 1
                    P.CDPRODUTO,
                    P.PRODUTO,
                    PC.CODBARRA AS CODIGOBARRA,
                    M.QTDEATUAL
                FROM PRODUTO_CODBARRA PC
                JOIN PRODUTO P ON P.CDPRODUTO = PC.CDPRODUTO
                LEFT JOIN MOVIMENTO M
                    ON M.CDPRODUTO = CAST(P.CDPRODUTO AS VARCHAR(10))
                   AND M.CDDEPOSITO = ?
                WHERE PC.CODBARRA = ?
                  AND (P.INATIVO IS NULL OR P.INATIVO = 0)
                """,
                (cddeposito, codigo),
            )
            produto = fetchone_as_dict(cur)

    if not produto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Produto com código de barras '{codigo}' não encontrado",
        )

    return produto


@router.get("/busca", response_model=list[ProdutoResponse])
def buscar_por_descricao(
    q: str = Query(..., min_length=2, description="Texto para buscar na descrição"),
    cddeposito: int = Query(..., description="Depósito para consultar estoque"),
    current_user: dict = Depends(get_current_user),
):
    with get_connection() as con:
        cur = con.cursor()
        cur.execute(
            """
            SELECT FIRST 50
                P.CDPRODUTO,
                P.PRODUTO,
                P.CODIGOBARRA,
                M.QTDEATUAL
            FROM PRODUTO P
            LEFT JOIN MOVIMENTO M
                ON M.CDPRODUTO = CAST(P.CDPRODUTO AS VARCHAR(10))
               AND M.CDDEPOSITO = ?
            WHERE UPPER(P.PRODUTO) CONTAINING UPPER(?)
              AND (P.INATIVO IS NULL OR P.INATIVO = 0)
            ORDER BY P.PRODUTO
            """,
            (cddeposito, q),
        )
        return fetchall_as_dict(cur)
