import os
import threading
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.database import get_connection, fetchall_as_dict, fetchone_as_dict
from app.security import get_current_user
from app.models.schemas import (
    BipagemRequest, BipagemResponse, EditarBipagemRequest,
    ItemRelatorio, ConsolidarRequest, ItemHistorico, LogItem, ResumoContagem,
)

router = APIRouter(prefix="/inventario", tags=["Inventário"])

ALERTA_MULTIPLO = 2.0
ALERTA_MINIMO   = 10.0

LIMIAR_RECONTAGEM         = 0.30  # 30% dos itens com divergência
LIMIAR_RECONTAGEM_MINIMO  = 5     # mínimo de 5 itens divergentes para exigir

PASTA_RELATORIOS = r"C:\Invec\relatorios"

_consolidando: set[int] = set()
_consolidando_lock = threading.Lock()


def _registrar_log(
    tipo: str,
    login_usuario: str,
    cddeposito: int = None,
    cdproduto: int = None,
    produto: str = None,
    operador: str = None,
    qtde_antes: float = None,
    qtde_depois: float = None,
    motivo: str = None,
    device_id: str = None,
):
    """Grava log em conexão separada — falha silenciosa para nunca travar a operação principal."""
    try:
        with get_connection() as log_con:
            cur = log_con.cursor()
            cur.execute(
                """
                INSERT INTO LOG_INVENTARIO
                    (TIPO, CDDEPOSITO, CDPRODUTO, PRODUTO, OPERADOR,
                     LOGIN_USUARIO, QTDE_ANTES, QTDE_DEPOIS, MOTIVO, DEVICE_ID, DATA_HORA)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (tipo, cddeposito, cdproduto, produto, operador,
                 login_usuario, qtde_antes, qtde_depois, motivo, device_id),
            )
    except Exception as e:
        print(f"[log] Falha ao gravar auditoria ({tipo}): {e}")


def _salvar_relatorio(
    cddeposito: int,
    operador: str,
    login_usuario: str,
    total: int,
    divergencias: int,
    supervisor: str,
    itens_divergentes: list[dict],
):
    """Salva relatório de consolidação em arquivo texto. Falha silenciosa."""
    try:
        os.makedirs(PASTA_RELATORIOS, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        caminho = os.path.join(PASTA_RELATORIOS, f"consolidacao_{ts}_dep{cddeposito}.txt")
        with open(caminho, "w", encoding="utf-8") as f:
            f.write("RELATORIO DE CONSOLIDACAO - INVEC\n")
            f.write("=" * 55 + "\n")
            f.write(f"Data/Hora  : {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
            f.write(f"Deposito   : {cddeposito}\n")
            f.write(f"Operador   : {operador or '-'}\n")
            f.write(f"Usuario    : {login_usuario}\n")
            f.write(f"Supervisor : {supervisor or 'Nao necessario'}\n")
            f.write(f"Total itens: {total}\n")
            f.write(f"Divergencias: {divergencias}\n")
            if itens_divergentes:
                f.write("\nITENS COM DIVERGENCIA\n")
                f.write("-" * 55 + "\n")
                f.write(f"{'Produto':<35} {'Sistema':>8} {'Contado':>8} {'Dif':>8}\n")
                f.write("-" * 55 + "\n")
                for item in itens_divergentes:
                    nome = str(item.get("produto", ""))[:35]
                    f.write(
                        f"{nome:<35} "
                        f"{item.get('qtde_sistema', 0):>8.0f} "
                        f"{item.get('qtde_contada', 0):>8.0f} "
                        f"{item.get('diferenca', 0):>+8.0f}\n"
                    )
    except Exception as e:
        print(f"[relatorio] Erro ao salvar relatorio de consolidacao: {e}")


@router.post("/bipagem", response_model=BipagemResponse)
def registrar_bipagem(
    body: BipagemRequest,
    current_user: dict = Depends(get_current_user),
):
    if body.qtde <= 0:
        raise HTTPException(status_code=400, detail="Quantidade deve ser maior que zero")

    nova_qtde = 0.0
    mensagem = ""
    nome_produto = f"#{body.cdproduto}"
    qtde_sistema = 0.0

    with get_connection() as con:
        cur = con.cursor()

        # Busca dados do produto antes de qualquer escrita
        cur.execute(
            "SELECT P.PRODUTO, "
            "(SELECT FIRST 1 M2.QTDEATUAL FROM MOVIMENTO M2 "
            " WHERE M2.CDPRODUTO = CAST(P.CDPRODUTO AS VARCHAR(10)) AND M2.CDDEPOSITO = ?) AS QTDEATUAL "
            "FROM PRODUTO P WHERE P.CDPRODUTO = ?",
            (body.cddeposito, body.cdproduto),
        )
        row_prod = fetchone_as_dict(cur)
        if not row_prod:
            raise HTTPException(status_code=404, detail=f"Produto #{body.cdproduto} não encontrado no sistema")
        nome_produto = row_prod["produto"]
        qtde_sistema = float(row_prod["qtdeatual"] or 0.0)

        # UPDATE atômico: evita race condition se dois celulares escaneiam o mesmo item simultaneamente
        cur.execute(
            "UPDATE INVENTARIO_TEMP SET QTDE = QTDE + ?, OPERADOR = ? "
            "WHERE CDPRODUTO = ? AND CDDEPOSITO = ? RETURNING QTDE",
            (body.qtde, body.operador, body.cdproduto, body.cddeposito),
        )
        row = cur.fetchone()
        if row:
            nova_qtde = float(row[0])
            mensagem = f"Quantidade atualizada para {nova_qtde}"
        else:
            nova_qtde = body.qtde
            # Primeiro scan deste produto: salva snapshot de QTDEATUAL agora.
            # Snapshot não é atualizado em scans subsequentes — queremos o valor
            # do momento da 1ª contagem, não da consolidação (podem chegar NFs entre os dois).
            cur.execute(
                "INSERT INTO INVENTARIO_TEMP (CDPRODUTO, CDDEPOSITO, QTDE, OPERADOR, QTDEATUAL_SNAP) "
                "VALUES (?, ?, ?, ?, ?)",
                (body.cdproduto, body.cddeposito, body.qtde, body.operador, qtde_sistema),
            )
            mensagem = "Bipagem registrada"

            # Detecta padrão de fraude: produto foi excluído da contagem na mesma sessão
            # e está sendo re-escaneado. Registra alerta independente da quantidade.
            cur.execute(
                "SELECT COUNT(*) FROM LOG_INVENTARIO "
                "WHERE TIPO = 'EXCLUSAO' AND CDPRODUTO = ? AND CDDEPOSITO = ? "
                "AND DATA_HORA > DATEADD(HOUR, -12, CURRENT_TIMESTAMP)",
                (body.cdproduto, body.cddeposito),
            )
            if (cur.fetchone()[0] or 0) > 0:
                _registrar_log(
                    "ALERTA_REESCAN",
                    login_usuario=current_user.get("login", ""),
                    cddeposito=body.cddeposito,
                    cdproduto=body.cdproduto,
                    produto=nome_produto,
                    operador=body.operador,
                    qtde_antes=qtde_sistema,
                    qtde_depois=nova_qtde,
                    motivo="Produto excluído da contagem e re-escaneado na mesma sessão",
                    device_id=body.device_id,
                )

    alerta = None
    if qtde_sistema >= ALERTA_MINIMO and nova_qtde > qtde_sistema * ALERTA_MULTIPLO:
        alerta = (
            f"Quantidade contada ({nova_qtde:.0f}) excede "
            f"{ALERTA_MULTIPLO:.0f}x o estoque do sistema ({qtde_sistema:.0f}). "
            "Confirme se está correto."
        )
        _registrar_log(
            "ALERTA",
            login_usuario=current_user.get("login", ""),
            cddeposito=body.cddeposito,
            cdproduto=body.cdproduto,
            produto=nome_produto,
            operador=body.operador,
            qtde_antes=qtde_sistema,
            qtde_depois=nova_qtde,
            motivo=alerta,
            device_id=body.device_id,
        )

    return BipagemResponse(
        cdproduto=body.cdproduto,
        cddeposito=body.cddeposito,
        qtde=body.qtde,
        nova_qtde=nova_qtde,
        mensagem=mensagem,
        alerta=alerta,
    )


@router.get("/relatorio/{cddeposito}", response_model=list[ItemRelatorio])
def relatorio_inventario(
    cddeposito: int,
    current_user: dict = Depends(get_current_user),
):
    with get_connection() as con:
        cur = con.cursor()
        # QTDE_SISTEMA usa o snapshot tirado no momento do 1º scan (QTDEATUAL_SNAP),
        # com fallback para MOVIMENTO.QTDEATUAL para linhas anteriores à migration.
        # Isso garante que o operador veja exatamente o mesmo valor que a consolidação vai usar.
        cur.execute(
            """
            SELECT
                P.CDPRODUTO,
                P.PRODUTO,
                P.CODIGOBARRA,
                COALESCE(IT.QTDEATUAL_SNAP,
                    (SELECT FIRST 1 M2.QTDEATUAL
                     FROM MOVIMENTO M2
                     WHERE M2.CDPRODUTO = CAST(P.CDPRODUTO AS VARCHAR(10))
                       AND M2.CDDEPOSITO = ?))   AS QTDE_SISTEMA,
                IT.QTDE                           AS QTDE_CONTADA,
                COALESCE(IT.QTDE, 0) - COALESCE(IT.QTDEATUAL_SNAP,
                    (SELECT FIRST 1 M3.QTDEATUAL
                     FROM MOVIMENTO M3
                     WHERE M3.CDPRODUTO = CAST(P.CDPRODUTO AS VARCHAR(10))
                       AND M3.CDDEPOSITO = ?),
                    0)                            AS DIFERENCA,
                IT.OPERADOR
            FROM PRODUTO P
            JOIN INVENTARIO_TEMP IT
                ON IT.CDPRODUTO = P.CDPRODUTO AND IT.CDDEPOSITO = ?
            ORDER BY P.PRODUTO
            """,
            (cddeposito, cddeposito, cddeposito),
        )
        return fetchall_as_dict(cur)


@router.get("/resumo/{cddeposito}", response_model=ResumoContagem)
def resumo_contagem(
    cddeposito: int,
    current_user: dict = Depends(get_current_user),
):
    with get_connection() as con:
        cur = con.cursor()

        # Produtos com estoque positivo no depósito que NÃO foram contados na sessão atual.
        # Usamos FIRST 50 na lista de nomes para não sobrecarregar a resposta.
        cur.execute(
            """
            SELECT COUNT(*) FROM MOVIMENTO M
            WHERE M.CDDEPOSITO = ? AND M.QTDEATUAL > 0
            """,
            (cddeposito,),
        )
        total_deposito = cur.fetchone()[0] or 0

        cur.execute(
            "SELECT COUNT(*) FROM INVENTARIO_TEMP WHERE CDDEPOSITO = ?",
            (cddeposito,),
        )
        contados = cur.fetchone()[0] or 0

        cur.execute(
            """
            SELECT FIRST 50 P.PRODUTO
            FROM MOVIMENTO M
            JOIN PRODUTO P ON CAST(P.CDPRODUTO AS VARCHAR(10)) = M.CDPRODUTO
            WHERE M.CDDEPOSITO = ? AND M.QTDEATUAL > 0
              AND NOT EXISTS (
                  SELECT 1 FROM INVENTARIO_TEMP IT
                  WHERE IT.CDPRODUTO = P.CDPRODUTO AND IT.CDDEPOSITO = ?
              )
            ORDER BY P.PRODUTO
            """,
            (cddeposito, cddeposito),
        )
        nomes = [row[0] for row in cur.fetchall()]

        nao_contados = max(0, total_deposito - contados)
        return ResumoContagem(
            total_deposito=total_deposito,
            contados=contados,
            nao_contados=nao_contados,
            produtos_nao_contados=nomes,
        )


@router.post("/consolidar")
def consolidar_inventario(
    body: ConsolidarRequest,
    current_user: dict = Depends(get_current_user),
):
    with _consolidando_lock:
        if body.cddeposito in _consolidando:
            raise HTTPException(
                status_code=409,
                detail="Já existe uma consolidação em andamento para este depósito. Aguarde.",
            )
        _consolidando.add(body.cddeposito)

    try:
        with get_connection() as con:
            cur = con.cursor()

            # IDUSUARIO do usuário autenticado para gravar em MOV_PRODUTO
            cur.execute(
                "SELECT IDUSUARIO FROM USUARIOS WHERE LOWER(LOGIN) = LOWER(?)",
                (current_user.get("login", ""),),
            )
            row_user = cur.fetchone()
            idusuario = row_user[0] if row_user else 1

            # Busca todos os itens com FATORCONV e VLCUSTO em uma única query
            cur.execute(
                """
                SELECT
                    IT.CDPRODUTO,
                    IT.CDDEPOSITO,
                    IT.QTDE                                      AS QTDE_CONTADA,
                    IT.OPERADOR,
                    CAST(IT.CDPRODUTO AS VARCHAR(10))            AS CDPRODUTO_STR,
                    COALESCE(P.CDUNIDADE, 'UN')                  AS CDUNIDADE,
                    COALESCE(P.PRODUTO, '')                      AS PRODUTO,
                    COALESCE(IT.QTDEATUAL_SNAP,
                        (SELECT FIRST 1 M2.QTDEATUAL
                         FROM MOVIMENTO M2
                         WHERE M2.CDPRODUTO = CAST(IT.CDPRODUTO AS VARCHAR(10))
                           AND M2.CDDEPOSITO = IT.CDDEPOSITO),
                        0)                                       AS QTDEATUAL,
                    COALESCE(
                        (SELECT FIRST 1 PP2.FATORCONV
                         FROM PRODUTOPRECO PP2
                         WHERE PP2.CDPRODUTO = CAST(IT.CDPRODUTO AS VARCHAR(10))
                           AND PP2.CDUNIDADE = P.CDUNIDADE
                           AND PP2.IDPRECO   = P.IDPRECO
                           AND PP2.FATORCONV > 0),
                        1)                                       AS FATORCONV,
                    COALESCE(
                        (SELECT FIRST 1 PP3.VLCUSTO
                         FROM PRODUTOPRECO PP3
                         WHERE PP3.CDPRODUTO = CAST(IT.CDPRODUTO AS VARCHAR(10))
                           AND PP3.CDUNIDADE = P.CDUNIDADE
                           AND PP3.IDPRECO   = P.IDPRECO),
                        0)                                       AS VLCUSTO
                FROM INVENTARIO_TEMP IT
                JOIN PRODUTO P ON P.CDPRODUTO = IT.CDPRODUTO
                WHERE IT.CDDEPOSITO = ?
                """,
                (body.cddeposito,),
            )
            itens = fetchall_as_dict(cur)

            total = len(itens)
            if total == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Nenhuma bipagem pendente para este depósito",
                )

            # Busca QTDEENTREGA por produto — aplicado sempre.
            # Produtos sem pedido pendente ficam com 0, tornando o cálculo idêntico ao sem CE.
            # Fórmula do Automec (GravaSaidas + IncluirRegistro aTp=4):
            # QTDEENTREGA = (QTDPRODUTO - QTD_VEND_FUT + QTD_VEND_FUT_LIB
            #                - QTDELIB - QTDENTREGAR - QTDENTCANCELADA - QTDCARREGADA) * FATORCONV
            qtde_entrega_map: dict[int, float] = {}
            try:
                cur.execute(
                    """
                    SELECT
                        CAST(B.CDPRODUTO AS INTEGER) AS CDPRODUTO,
                        SUM(
                            (COALESCE(B.QTDPRODUTO, 0) - COALESCE(B.QTD_VEND_FUT, 0)
                             + COALESCE(B.QTD_VEND_FUT_LIB, 0)
                             - COALESCE(B.QTDELIB, 0)
                             - COALESCE(B.QTDENTREGAR, 0)
                             - COALESCE(B.QTDENTCANCELADA, 0)
                             - COALESCE(B.QTDCARREGADA, 0)) * COALESCE(B.FATORCONV, 1)
                        ) AS QTDEENTREGA
                    FROM SAIDAPRODUTO B
                    JOIN SAIDAESTOQUE A ON A.NRPEDIDO = B.NRPEDIDO AND A.IDEMPRESA = B.IDEMPRESA
                    WHERE NOT (A.STATUS IN (2, 42))
                      AND B.STATUSSE <> 9
                      AND COALESCE(B.IDENTREGA, 0) NOT IN (0, 9999)
                      AND B.CDDEPOSITO = ?
                      AND A.DTSAIDA <= CURRENT_DATE
                    GROUP BY B.CDPRODUTO
                    """,
                    (body.cddeposito,),
                )
                for row in fetchall_as_dict(cur):
                    # Clamp para zero: cancelamentos/carregamentos podem exceder o pedido,
                    # resultando em valor negativo que corromperia QTSAIDA no trigger.
                    qtde_entrega_map[row["cdproduto"]] = max(0.0, float(row["qtdeentrega"] or 0))
            except Exception as e:
                # Tabelas SAIDAPRODUTO/SAIDAESTOQUE podem não existir em versões antigas do Automec.
                # Nesse caso, continua sem ajuste de entrega (comportamento equivalente a CE desativado).
                print(f"[consolidar] SAIDAPRODUTO indisponível, ignorando entregas pendentes: {e}")

            divergencias = 0
            for item in itens:
                qtde_atual = float(item["qtdeatual"] or 0)
                qtdeentrega = qtde_entrega_map.get(item["cdproduto"], 0.0)
                baseline = qtde_atual + qtdeentrega
                if abs(float(item["qtde_contada"] or 0) - baseline) > 0.001:
                    divergencias += 1

            # Recontagem obrigatória quando mais de 30% dos itens têm divergência
            if (
                divergencias >= LIMIAR_RECONTAGEM_MINIMO
                and (divergencias / total) >= LIMIAR_RECONTAGEM
                and not body.recontagem_confirmada
            ):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        f"{divergencias} de {total} itens "
                        f"({divergencias / total:.0%}) têm divergência. "
                        "Faça a recontagem antes de consolidar."
                    ),
                )

            if divergencias > 0:
                if not body.supervisor_login or not body.supervisor_senha:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Há {divergencias} divergências. Login de supervisor obrigatório para consolidar.",
                    )
                cur.execute(
                    "SELECT IDUSUARIO, LOGIN, IDGRUPO, SENHAMOBILE FROM USUARIOS "
                    "WHERE LOWER(LOGIN) = LOWER(?) "
                    "AND (INATIVO IS NULL OR INATIVO = 0)",
                    (body.supervisor_login,),
                )
                supervisor = fetchone_as_dict(cur)
                if not supervisor:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Credenciais do supervisor inválidas",
                    )
                senha_mobile = supervisor.get("senhamobile") or ""
                if not senha_mobile:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Supervisor não possui senha mobile configurada. Configure em Usuários.",
                    )
                if senha_mobile != body.supervisor_senha:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Credenciais do supervisor inválidas",
                    )
                if (supervisor.get("idgrupo") or 3) not in (1, 2):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Supervisor precisa ser gerente ou administrador",
                    )
                # Operadores (idgrupo=3) não podem ser o próprio supervisor —
                # precisam de um gerente/admin diferente para autorizar.
                # Gerentes e admins podem consolidar e autorizar com as próprias credenciais.
                quem_consolida_e_operador = (current_user.get("idgrupo") or 3) == 3
                mesmo_usuario = supervisor["login"].lower() == current_user.get("login", "").lower()
                if mesmo_usuario and quem_consolida_e_operador:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Operadores não podem autorizar a própria consolidação. Chame um gerente.",
                    )

            # Gera IDINVENTARIO UMA VEZ para toda a sessão de inventário.
            # Mesmo generator que o Automec usa (GEN_MOV_PRODUTO), igual ao Delphi GravarQuantidade.
            # O IDMOVIMENTO de cada linha é gerado automaticamente pelo trigger TG_ID_MOV_PRODUTO.
            cur.execute("SELECT GEN_ID(GEN_MOV_PRODUTO, 1) FROM RDB$DATABASE")
            idinventario = cur.fetchone()[0]

            cur2 = con.cursor()
            itens_divergentes = []

            for item in itens:
                cdproduto      = item["cdproduto"]
                cdproduto_str  = item["cdproduto_str"]
                qtde_contada   = float(item["qtde_contada"] or 0)
                qtde_atual     = float(item["qtdeatual"] or 0)
                fatorconv      = float(item["fatorconv"] or 1)
                vlcusto        = float(item["vlcusto"] or 0)
                cdunidade      = item["cdunidade"]
                operador_item  = item.get("operador") or body.operador or ""
                nome_produto   = item["produto"] or f"#{cdproduto}"
                qtdeentrega    = qtde_entrega_map.get(cdproduto, 0.0)

                qtdanterior = qtde_atual + qtdeentrega

                if qtdeentrega > 0:
                    # GravarMov_Produto_Entrega: há pedido pendente, QTSAIDA absorve a entrega
                    if qtde_contada > qtde_atual:
                        qtentrada = qtde_contada - qtde_atual
                        qtsaida   = qtdeentrega
                    elif qtde_contada < qtde_atual:
                        qtentrada = 0.0
                        qtsaida   = (qtde_atual - qtde_contada) + qtdeentrega
                    else:
                        qtentrada = 0.0
                        qtsaida   = qtdeentrega
                    vl_perda_ganho = None
                else:
                    # GravarMov_Produto: sem pedido pendente, ajuste simples
                    if qtde_contada > qtde_atual:
                        qtentrada = qtde_contada - qtde_atual
                        qtsaida   = 0.0
                    elif qtde_contada < qtde_atual:
                        qtentrada = 0.0
                        qtsaida   = qtde_atual - qtde_contada
                    else:
                        qtentrada = 0.0
                        qtsaida   = 0.0
                    vl_perda_ganho = round((qtde_contada - qtde_atual) * vlcusto, 2)

                if abs(qtde_contada - qtdanterior) > 0.001:
                    itens_divergentes.append({
                        "produto": nome_produto,
                        "qtde_sistema": qtdanterior,
                        "qtde_contada": qtde_contada,
                        "diferenca": qtde_contada - qtdanterior,
                    })

                # INSERT em MOV_PRODUTO — trigger TG_ID_MOV_PRODUTO gera IDMOVIMENTO automaticamente;
                # trigger TG_INSERT_MOV_PRODUTO atualiza MOVIMENTO.QTDEATUAL via QTDE_MOVIMENTO.
                if vl_perda_ganho is not None:
                    cur2.execute(
                        "INSERT INTO MOV_PRODUTO "
                        "(IDEMPRESA, CDPRODUTO, CDDEPOSITO, TIPOMOVIMENTO, CDNATOP, DTMOVIMENTO, HISTORICO, "
                        "FATORCONV, QTENTRADA, QTSAIDA, IDUSUARIO, CDUNIDADE, IDINVENTARIO, "
                        "QTDINVENTARIO, QTDANTERIOR, VL_PERDA_GANHO, SIST_ALT) "
                        "VALUES (?, ?, ?, 5, '0000', CURRENT_DATE, 'Ajuste na Tela de Inventário', "
                        "?, ?, ?, ?, ?, ?, ?, ?, ?, 'INV_APP')",
                        (body.idempresa, cdproduto_str, body.cddeposito, fatorconv,
                         qtentrada, qtsaida, idusuario, cdunidade, idinventario,
                         qtde_contada, qtdanterior, vl_perda_ganho),
                    )
                else:
                    cur2.execute(
                        "INSERT INTO MOV_PRODUTO "
                        "(IDEMPRESA, CDPRODUTO, CDDEPOSITO, TIPOMOVIMENTO, CDNATOP, DTMOVIMENTO, HISTORICO, "
                        "FATORCONV, QTENTRADA, QTSAIDA, IDUSUARIO, CDUNIDADE, IDINVENTARIO, "
                        "QTDINVENTARIO, QTDANTERIOR, SIST_ALT) "
                        "VALUES (?, ?, ?, 5, '0000', CURRENT_DATE, 'Ajuste na Tela de Inventário', "
                        "?, ?, ?, ?, ?, ?, ?, ?, 'INV_APP')",
                        (body.idempresa, cdproduto_str, body.cddeposito, fatorconv,
                         qtentrada, qtsaida, idusuario, cdunidade, idinventario,
                         qtde_contada, qtdanterior),
                    )

            cur2.execute(
                "DELETE FROM INVENTARIO_TEMP WHERE CDDEPOSITO = ?",
                (body.cddeposito,),
            )

        supervisor_label = f" (supervisor: {body.supervisor_login})" if body.supervisor_login else ""
        _registrar_log(
            "CONSOLIDACAO",
            login_usuario=current_user.get("login", ""),
            cddeposito=body.cddeposito,
            operador=body.operador,
            qtde_depois=float(total),
            motivo=f"{total} itens · {divergencias} divergências{supervisor_label} · inv#{idinventario}",
        )

        _salvar_relatorio(
            cddeposito=body.cddeposito,
            operador=body.operador or "",
            login_usuario=current_user.get("login", ""),
            total=total,
            divergencias=divergencias,
            supervisor=body.supervisor_login or "",
            itens_divergentes=itens_divergentes,
        )

        return {
            "mensagem": f"{total} itens consolidados com sucesso no depósito {body.cddeposito}",
            "idinventario": idinventario,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")
    finally:
        with _consolidando_lock:
            _consolidando.discard(body.cddeposito)


@router.get("/historico/{cddeposito}", response_model=list[ItemHistorico])
def historico_inventario(
    cddeposito: int,
    current_user: dict = Depends(get_current_user),
):
    # Usa MOV_PRODUTO (SIST_ALT='INV_APP') em vez de INVENTARIO para evitar o
    # problema do trigger TGUP_INVENTARIO_DTALTER que sobrescreve SIST_ALT para
    # 'LOCAL' em todo UPDATE, fazendo itens re-inventariados desaparecerem do histórico.
    with get_connection() as con:
        cur = con.cursor()
        cur.execute(
            """
            SELECT FIRST 500
                CAST(MP.CDPRODUTO AS INTEGER) AS CDPRODUTO,
                P.PRODUTO,
                MP.CDDEPOSITO,
                D.DEPOSITO,
                MP.QTDINVENTARIO    AS QTDE_CONTADA,
                MP.QTDANTERIOR      AS QTDE_SISTEMA,
                MP.DTMOVIMENTO      AS DATA,
                MP.HISTORICO        AS OPERADOR
            FROM MOV_PRODUTO MP
            JOIN PRODUTO P
                ON CAST(P.CDPRODUTO AS VARCHAR(10)) = MP.CDPRODUTO
            JOIN DEPOSITO D
                ON D.CDDEPOSITO = MP.CDDEPOSITO
            WHERE MP.CDDEPOSITO = ?
              AND MP.SIST_ALT = 'INV_APP'
              AND MP.TIPOMOVIMENTO = 5
            ORDER BY MP.DTMOVIMENTO DESC, MP.IDMOVIMENTO DESC
            """,
            (cddeposito,),
        )
        return fetchall_as_dict(cur)


@router.delete("/bipagem/{cdproduto}")
def remover_bipagem(
    cdproduto: int,
    cddeposito: int,
    motivo: Optional[str] = Query(default=None),
    device_id: Optional[str] = Query(default=None),
    current_user: dict = Depends(get_current_user),
):
    if not motivo or not motivo.strip():
        raise HTTPException(status_code=400, detail="Motivo é obrigatório para excluir uma bipagem")

    existente = None
    with get_connection() as con:
        cur = con.cursor()
        cur.execute(
            "SELECT IT.QTDE, P.PRODUTO FROM INVENTARIO_TEMP IT "
            "JOIN PRODUTO P ON P.CDPRODUTO = IT.CDPRODUTO "
            "WHERE IT.CDPRODUTO = ? AND IT.CDDEPOSITO = ?",
            (cdproduto, cddeposito),
        )
        existente = fetchone_as_dict(cur)
        cur.execute(
            "DELETE FROM INVENTARIO_TEMP WHERE CDPRODUTO = ? AND CDDEPOSITO = ?",
            (cdproduto, cddeposito),
        )

    if existente:
        _registrar_log(
            "EXCLUSAO",
            login_usuario=current_user.get("login", ""),
            cddeposito=cddeposito,
            cdproduto=cdproduto,
            produto=existente.get("produto"),
            qtde_antes=existente.get("qtde"),
            motivo=motivo,
            device_id=device_id,
        )

    return {"mensagem": "Bipagem removida"}


@router.put("/bipagem/{cdproduto}")
def editar_bipagem(
    cdproduto: int,
    body: EditarBipagemRequest,
    current_user: dict = Depends(get_current_user),
):
    if body.qtde < 0:
        raise HTTPException(status_code=400, detail="Quantidade não pode ser negativa")
    anterior = None
    snap = None
    with get_connection() as con:
        cur = con.cursor()
        cur.execute(
            "SELECT IT.QTDE, IT.QTDEATUAL_SNAP, P.PRODUTO FROM INVENTARIO_TEMP IT "
            "JOIN PRODUTO P ON P.CDPRODUTO = IT.CDPRODUTO "
            "WHERE IT.CDPRODUTO = ? AND IT.CDDEPOSITO = ?",
            (cdproduto, body.cddeposito),
        )
        anterior = fetchone_as_dict(cur)
        if not anterior:
            raise HTTPException(status_code=404, detail="Item não encontrado na contagem")
        snap = anterior.get("qtdeatual_snap")
        cur.execute(
            "UPDATE INVENTARIO_TEMP SET QTDE = ? WHERE CDPRODUTO = ? AND CDDEPOSITO = ?",
            (body.qtde, cdproduto, body.cddeposito),
        )

    qtde_antes = anterior.get("qtde") if anterior else None
    produto_nome = anterior.get("produto") if anterior else None

    # Padrão suspeito: edição faz a contagem coincidir exatamente com o estoque do sistema.
    # Indica possível tentativa de ocultar divergência real.
    tipo_log = "EDICAO"
    motivo_extra = ""
    if snap is not None and abs(body.qtde - float(snap)) < 0.001 and qtde_antes is not None:
        if abs(float(qtde_antes) - float(snap)) > 0.001:
            tipo_log = "EDICAO_SUSPEITA"
            motivo_extra = f" [ALERTA: contagem editada de {qtde_antes:.0f} para {body.qtde:.0f} coincidindo com sistema ({snap:.0f})]"

    _registrar_log(
        tipo_log,
        login_usuario=current_user.get("login", ""),
        cddeposito=body.cddeposito,
        cdproduto=cdproduto,
        produto=produto_nome,
        qtde_antes=qtde_antes,
        qtde_depois=body.qtde,
        motivo=(body.motivo or "") + motivo_extra,
        device_id=body.device_id,
    )

    return {"mensagem": f"Quantidade atualizada para {body.qtde}"}


@router.get("/log/{cddeposito}", response_model=list[LogItem])
def log_auditoria(
    cddeposito: int,
    limit: int = Query(default=200, le=500),
    current_user: dict = Depends(get_current_user),
):
    if (current_user.get("idgrupo") or 3) not in (1, 2):
        raise HTTPException(status_code=403, detail="Apenas gerentes e administradores podem acessar o log de auditoria")
    try:
        with get_connection() as con:
            cur = con.cursor()
            cur.execute(
                """
                SELECT FIRST ?
                    ID, TIPO, CDDEPOSITO, CDPRODUTO, PRODUTO, OPERADOR,
                    LOGIN_USUARIO, QTDE_ANTES, QTDE_DEPOIS, MOTIVO, DEVICE_ID, DATA_HORA
                FROM LOG_INVENTARIO
                WHERE CDDEPOSITO = ?
                ORDER BY DATA_HORA DESC
                """,
                (limit, cddeposito),
            )
            return fetchall_as_dict(cur)
    except Exception as e:
        print(f"[log_auditoria] {e}")
        return []
