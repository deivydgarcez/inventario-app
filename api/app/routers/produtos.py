import math
from fastapi import APIRouter, Depends, HTTPException, status, Query
from app.database import get_connection, fetchone_as_dict, fetchall_as_dict
from app.security import get_current_user
from app.models.schemas import ProdutoResponse, CatalogoResponse, ProdutoCatalogoItem

router = APIRouter(prefix="/produtos", tags=["Produtos"])


def _barcode_variants(codigo: str) -> list[str]:
    """EAN-13 (13 dígitos com zero inicial) e UPC-A (12 dígitos) representam o mesmo código.
    Scanners podem retornar qualquer um dos formatos independentemente do que o ERP gravou."""
    variants = [codigo]
    if codigo.isdigit():
        if len(codigo) == 13 and codigo.startswith("0"):
            variants.append(codigo[1:])   # EAN-13 → UPC-A
        elif len(codigo) == 12:
            variants.append("0" + codigo) # UPC-A → EAN-13
    return variants


@router.get("/barcode/{codigo}", response_model=ProdutoResponse)
def buscar_por_barcode(
    codigo: str,
    cddeposito: int = Query(..., description="Depósito para consultar estoque"),
    current_user: dict = Depends(get_current_user),
):
    variants = _barcode_variants(codigo)
    placeholders = ", ".join(["?" for _ in variants])

    with get_connection() as con:
        cur = con.cursor()
        cur.execute(
            f"""
            SELECT FIRST 1
                P.CDPRODUTO,
                P.PRODUTO,
                P.CODIGOBARRA,
                M.QTDEATUAL,
                P.INATIVO
            FROM PRODUTO P
            LEFT JOIN MOVIMENTO M
                ON M.CDPRODUTO = CAST(P.CDPRODUTO AS VARCHAR(10))
               AND M.CDDEPOSITO = ?
            WHERE P.CODIGOBARRA IN ({placeholders})
            """,
            (cddeposito, *variants),
        )
        produto = fetchone_as_dict(cur)

        if not produto:
            cur.execute(
                f"""
                SELECT FIRST 1
                    P.CDPRODUTO,
                    P.PRODUTO,
                    PC.CODBARRA AS CODIGOBARRA,
                    M.QTDEATUAL,
                    P.INATIVO
                FROM PRODUTO_CODBARRA PC
                JOIN PRODUTO P ON P.CDPRODUTO = PC.CDPRODUTO
                LEFT JOIN MOVIMENTO M
                    ON M.CDPRODUTO = CAST(P.CDPRODUTO AS VARCHAR(10))
                   AND M.CDDEPOSITO = ?
                WHERE PC.CODBARRA IN ({placeholders})
                """,
                (cddeposito, *variants),
            )
            produto = fetchone_as_dict(cur)

    if not produto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Produto com código de barras '{codigo}' não encontrado",
        )

    if produto.get("inativo") == -1:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto inativo",
        )

    return produto


@router.get("/{cddeposito}/catalogo", response_model=CatalogoResponse)
def catalogo_offline(
    cddeposito: int,
    pagina: int = Query(default=1, ge=1),
    limite: int = Query(default=500, ge=1, le=1000),
    current_user: dict = Depends(get_current_user),
):
    """Retorna o catálogo completo de produtos do depósito para cache offline."""
    skip = (pagina - 1) * limite
    with get_connection() as con:
        cur = con.cursor()
        # PERF-1: COUNT como soma de dois scalars — evita materializar o UNION inteiro só para contar
        cur.execute(
            "SELECT "
            "(SELECT COUNT(*) FROM PRODUTO WHERE (INATIVO IS NULL OR INATIVO = 0) "
            " AND CODIGOBARRA IS NOT NULL AND TRIM(CODIGOBARRA) <> '') + "
            "(SELECT COUNT(*) FROM PRODUTO_CODBARRA PC "
            " JOIN PRODUTO P ON P.CDPRODUTO = PC.CDPRODUTO "
            " WHERE (P.INATIVO IS NULL OR P.INATIVO = 0)) "
            "FROM RDB$DATABASE"
        )
        total = cur.fetchone()[0] or 0

        cur.execute(
            """
            SELECT FIRST ? SKIP ?
                cdproduto, produto, codigobarra, qtdeatual
            FROM (
                SELECT
                    P.CDPRODUTO                     AS cdproduto,
                    P.PRODUTO                       AS produto,
                    P.CODIGOBARRA                   AS codigobarra,
                    COALESCE(M.QTDEATUAL, 0)        AS qtdeatual
                FROM PRODUTO P
                LEFT JOIN MOVIMENTO M
                    ON M.CDPRODUTO = CAST(P.CDPRODUTO AS VARCHAR(10))
                   AND M.CDDEPOSITO = ?
                WHERE (P.INATIVO IS NULL OR P.INATIVO = 0)
                  AND P.CODIGOBARRA IS NOT NULL AND TRIM(P.CODIGOBARRA) <> ''

                UNION

                SELECT
                    P.CDPRODUTO                     AS cdproduto,
                    P.PRODUTO                       AS produto,
                    PC.CODBARRA                     AS codigobarra,
                    COALESCE(M.QTDEATUAL, 0)        AS qtdeatual
                FROM PRODUTO_CODBARRA PC
                JOIN PRODUTO P ON P.CDPRODUTO = PC.CDPRODUTO
                LEFT JOIN MOVIMENTO M
                    ON M.CDPRODUTO = CAST(P.CDPRODUTO AS VARCHAR(10))
                   AND M.CDDEPOSITO = ?
                WHERE (P.INATIVO IS NULL OR P.INATIVO = 0)
            )
            ORDER BY produto
            """,
            (limite, skip, cddeposito, cddeposito),
        )
        rows = fetchall_as_dict(cur)

    itens = [
        ProdutoCatalogoItem(
            cdproduto=r["cdproduto"],
            produto=r["produto"],
            codigobarra=r.get("codigobarra"),
            qtdeatual=float(r["qtdeatual"] or 0),
        )
        for r in rows
    ]
    paginas = max(1, math.ceil(total / limite))
    return CatalogoResponse(itens=itens, total=total, pagina=pagina, paginas=paginas)


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
