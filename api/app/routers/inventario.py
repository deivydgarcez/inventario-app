import os
import secrets
import threading
import time
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.database import get_connection, fetchall_as_dict, fetchone_as_dict
from app.security import get_current_user
from app.models.schemas import (
    BipagemRequest, BipagemResponse, EditarBipagemRequest,
    ItemRelatorio, ConsolidarRequest, ItemHistorico, LogItem, ResumoContagem,
    LoteBipagemRequest, LoteSyncResponse, SupervisorPreAuthRequest,
)

router = APIRouter(prefix="/inventario", tags=["Inventário"])

ALERTA_MULTIPLO = 2.0
ALERTA_MINIMO   = 10.0

LIMIAR_RECONTAGEM        = 0.30
LIMIAR_RECONTAGEM_MINIMO = 5

PASTA_RELATORIOS = os.path.join(os.getenv("INVEC_DATA_DIR", r"C:\Invec"), "relatorios")

_IDEMPRESA_FALLBACK = int(os.getenv("IDEMPRESA", 1))

# BANCO-1: lock em memória (guarda primário dentro do processo)
_consolidando: set[int] = set()
_consolidando_lock = threading.Lock()

# ─── helper SAIDAPRODUTO: adapta ao schema do Automec instalado ──────────────
# QTD_VEND_FUT_LIB não existe em versões antigas do Automec; detecta uma vez e cacheia.
_saidaproduto_tem_qtd_fut_lib: bool | None = None

_SQL_ENTREGA = """
    SELECT CAST(B.CDPRODUTO AS INTEGER) AS CDPRODUTO,
        SUM((COALESCE(B.QTDPRODUTO, 0) - COALESCE(B.QTD_VEND_FUT, 0)
             + COALESCE(B.QTD_VEND_FUT_LIB, 0)
             - COALESCE(B.QTDELIB, 0) - COALESCE(B.QTDENTREGAR, 0)
             - COALESCE(B.QTDENTCANCELADA, 0) - COALESCE(B.QTDCARREGADA, 0)
            ) * COALESCE(B.FATORCONV, 1)) AS QTDEENTREGA
    FROM SAIDAPRODUTO B
    JOIN SAIDAESTOQUE A ON A.NRPEDIDO = B.NRPEDIDO AND A.IDEMPRESA = B.IDEMPRESA
    WHERE NOT (A.STATUS IN (2, 42)) AND B.STATUSSE <> 9
      AND COALESCE(B.IDENTREGA, 0) NOT IN (0, 9999)
      AND B.CDDEPOSITO = ? AND A.DTSAIDA <= CURRENT_DATE
    GROUP BY B.CDPRODUTO
"""

_SQL_ENTREGA_COMPAT = """
    SELECT CAST(B.CDPRODUTO AS INTEGER) AS CDPRODUTO,
        SUM((COALESCE(B.QTDPRODUTO, 0) - COALESCE(B.QTD_VEND_FUT, 0)
             - COALESCE(B.QTDELIB, 0) - COALESCE(B.QTDENTREGAR, 0)
             - COALESCE(B.QTDENTCANCELADA, 0) - COALESCE(B.QTDCARREGADA, 0)
            ) * COALESCE(B.FATORCONV, 1)) AS QTDEENTREGA
    FROM SAIDAPRODUTO B
    JOIN SAIDAESTOQUE A ON A.NRPEDIDO = B.NRPEDIDO AND A.IDEMPRESA = B.IDEMPRESA
    WHERE NOT (A.STATUS IN (2, 42)) AND B.STATUSSE <> 9
      AND COALESCE(B.IDENTREGA, 0) NOT IN (0, 9999)
      AND B.CDDEPOSITO = ? AND A.DTSAIDA <= CURRENT_DATE
    GROUP BY B.CDPRODUTO
"""


def _calcular_delta_estoque(
    qtde_contada: float,
    qtde_atual: float,
    qtdeentrega: float,
    vlcusto: float,
) -> tuple[float, float, float, float, float]:
    """
    Calcula os campos de movimentação para MOV_PRODUTO a partir dos valores de contagem.

    Retorna: (qtdanterior, qtentrada, qtsaida, vl_perda_ganho, baseline_report)

    - qtdanterior  = MOVIMENTO.QTDEATUAL real (nunca inclui qtdeentrega)
    - qtentrada    = ganho de estoque disponível
    - qtsaida      = perda de estoque disponível
    - vl_perda_ganho = valor financeiro do ajuste
    - baseline_report = qtde_atual + qtdeentrega (usado no relatório de divergências)
    """
    qtdanterior = qtde_atual
    baseline_report = qtde_atual + qtdeentrega

    if qtdeentrega > 0:
        effective = qtde_contada - qtdeentrega
        if effective > qtde_atual:
            qtentrada = effective - qtde_atual
            qtsaida   = 0.0
        elif effective < qtde_atual:
            qtentrada = 0.0
            qtsaida   = qtde_atual - effective
        else:
            qtentrada = 0.0
            qtsaida   = 0.0
        vl_perda_ganho = round((effective - qtde_atual) * vlcusto, 2)
    else:
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

    return qtdanterior, qtentrada, qtsaida, vl_perda_ganho, baseline_report


def _buscar_qtde_entrega(con, cddeposito: int) -> dict[int, float]:
    """
    Retorna mapa cdproduto → qtde em entrega (SAIDAPRODUTO com IDENTREGA ativo).
    Detecta automaticamente se QTD_VEND_FUT_LIB existe neste Automec e cacheia o resultado.
    """
    global _saidaproduto_tem_qtd_fut_lib

    def _executar(sql: str) -> dict[int, float]:
        c = con.cursor()
        c.execute(sql, (cddeposito,))
        resultado: dict[int, float] = {}
        for row in fetchall_as_dict(c):
            val = max(0.0, float(row["qtdeentrega"] or 0))
            if val > 0:
                resultado[row["cdproduto"]] = val
        return resultado

    if _saidaproduto_tem_qtd_fut_lib is False:
        return _executar(_SQL_ENTREGA_COMPAT)

    try:
        resultado = _executar(_SQL_ENTREGA)
        _saidaproduto_tem_qtd_fut_lib = True
        return resultado
    except Exception:
        if _saidaproduto_tem_qtd_fut_lib is None:
            try:
                resultado = _executar(_SQL_ENTREGA_COMPAT)
                _saidaproduto_tem_qtd_fut_lib = False
                print("[inventario] SAIDAPRODUTO.QTD_VEND_FUT_LIB ausente neste Automec — calculo adaptado")
                return resultado
            except Exception as e2:
                raise e2
        raise

# SEC-2: tokens de pré-autenticação de supervisor {token: {login, idgrupo, expires}}
_supervisor_tokens: dict[str, dict] = {}
_supervisor_tokens_lock = threading.Lock()
_SUPERVISOR_TOKEN_TTL = 300  # 5 minutos

# SEC-5: rate limit no pré-auth do supervisor (mesmo esquema do login)
_sup_tentativas: dict[str, list[float]] = {}
_sup_bloqueados: dict[str, float] = {}
_SUP_MAX_TENTATIVAS = 5
_SUP_JANELA_SEGUNDOS = 60
_SUP_BLOQUEIO_SEGUNDOS = 300


# ── Helpers internos ──────────────────────────────────────────────────────────

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
    session_id: str = None,
):
    """Grava log em conexão separada — falha silenciosa para nunca travar a operação principal."""
    try:
        with get_connection() as log_con:
            cur = log_con.cursor()
            cur.execute(
                """
                INSERT INTO LOG_INVENTARIO
                    (TIPO, CDDEPOSITO, CDPRODUTO, PRODUTO, OPERADOR,
                     LOGIN_USUARIO, QTDE_ANTES, QTDE_DEPOIS, MOTIVO, DEVICE_ID, SESSION_ID, DATA_HORA)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (tipo, cddeposito, cdproduto, produto, operador,
                 login_usuario, qtde_antes, qtde_depois, motivo, device_id, session_id),
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


def _verificar_acesso_deposito(current_user: dict, cddeposito: int) -> None:
    """FRAUDE-3: valida que o usuário tem permissão para o depósito.
    MI é superadmin — acesso irrestrito. Admins (idgrupo=1) e gerentes (idgrupo=2) também.
    Operadores sem restrições cadastradas têm acesso total (backward compat)."""
    if current_user.get("login", "").upper() == "MI":
        return
    idgrupo = current_user.get("idgrupo") or 3
    if idgrupo in (1, 2):
        return
    idusuario = current_user.get("sub")
    if not idusuario:
        return
    try:
        with get_connection() as con:
            cur = con.cursor()
            cur.execute(
                "SELECT COUNT(*) FROM USUARIO_DEPOSITO WHERE IDUSUARIO = ?",
                (int(idusuario),),
            )
            total_restricoes = cur.fetchone()[0] or 0
            if total_restricoes == 0:
                return  # sem restrições → acesso total (backward compat)
            cur.execute(
                "SELECT COUNT(*) FROM USUARIO_DEPOSITO WHERE IDUSUARIO = ? AND CDDEPOSITO = ?",
                (int(idusuario), cddeposito),
            )
            if (cur.fetchone()[0] or 0) == 0:
                raise HTTPException(
                    status_code=403,
                    detail="Sem permissão para este depósito",
                )
    except HTTPException:
        raise
    except Exception as e:
        # Só ignora se a tabela ainda não existe (migration pendente no primeiro startup)
        if "unknown" not in str(e).lower() and "not found" not in str(e).lower():
            raise HTTPException(status_code=500, detail="Erro ao verificar permissão de depósito")


def _validar_supervisor_token(token: str) -> dict:
    """SEC-2: valida token de pré-autenticação do supervisor."""
    with _supervisor_tokens_lock:
        data = _supervisor_tokens.get(token)
        if not data or data["expires"] < time.time():
            _supervisor_tokens.pop(token, None)
            raise HTTPException(
                status_code=401,
                detail="Token de supervisor inválido ou expirado. Solicite nova pré-autenticação.",
            )
        _supervisor_tokens.pop(token)  # token de uso único
        return data


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/supervisor/pre-auth")
def supervisor_pre_auth(
    body: SupervisorPreAuthRequest,
    current_user: dict = Depends(get_current_user),
):
    """SEC-2: Supervisor autentica previamente e recebe token válido por 5 min.
    O token é usado no consolidar em vez de enviar a senha em texto plano."""
    # SEC-5: rate limit por login do supervisor (mesmo esquema do /auth/login)
    agora = time.time()
    chave = f"sup:{body.login.lower()}"
    if chave in _sup_bloqueados:
        if agora < _sup_bloqueados[chave]:
            restante = int(_sup_bloqueados[chave] - agora)
            raise HTTPException(
                status_code=429,
                detail=f"Muitas tentativas. Tente novamente em {restante} segundos.",
            )
        del _sup_bloqueados[chave]
        _sup_tentativas.pop(chave, None)
    _sup_tentativas[chave] = [
        t for t in _sup_tentativas.get(chave, []) if agora - t < _SUP_JANELA_SEGUNDOS
    ]

    with get_connection() as con:
        cur = con.cursor()
        cur.execute(
            "SELECT IDUSUARIO, LOGIN, IDGRUPO, SENHAMOBILE FROM USUARIOS "
            "WHERE LOWER(LOGIN) = LOWER(?) AND (INATIVO IS NULL OR INATIVO = 0)",
            (body.login,),
        )
        sup = fetchone_as_dict(cur)

    senha_mobile = (sup.get("senhamobile") or "") if sup else ""
    credenciais_ok = sup and senha_mobile and senha_mobile == body.senha

    if not credenciais_ok:
        _sup_tentativas.setdefault(chave, []).append(agora)
        if len(_sup_tentativas[chave]) >= _SUP_MAX_TENTATIVAS:
            _sup_bloqueados[chave] = agora + _SUP_BLOQUEIO_SEGUNDOS
            _sup_tentativas.pop(chave, None)
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    _sup_tentativas.pop(chave, None)
    _sup_bloqueados.pop(chave, None)

    is_mi_sup = sup.get("login", "").upper() == "MI"
    if not is_mi_sup and (sup.get("idgrupo") or 3) not in (1, 2):
        raise HTTPException(status_code=403, detail="Supervisor precisa ser gerente ou administrador")

    # MI é sempre tratado como admin (idgrupo=1) mesmo que o banco Automec tenha outro grupo
    idgrupo_efetivo = 1 if is_mi_sup else (sup.get("idgrupo") or 3)

    token = secrets.token_hex(24)
    with _supervisor_tokens_lock:
        # Limpa tokens expirados
        expirados = [k for k, v in _supervisor_tokens.items() if v["expires"] < time.time()]
        for k in expirados:
            del _supervisor_tokens[k]
        _supervisor_tokens[token] = {
            "login": sup["login"],
            "idgrupo": idgrupo_efetivo,
            "expires": time.time() + _SUPERVISOR_TOKEN_TTL,
        }

    return {"supervisor_token": token, "expira_em_segundos": _SUPERVISOR_TOKEN_TTL}


@router.post("/bipagem", response_model=BipagemResponse)
def registrar_bipagem(
    body: BipagemRequest,
    current_user: dict = Depends(get_current_user),
):
    _verificar_acesso_deposito(current_user, body.cddeposito)

    if body.qtde <= 0:
        raise HTTPException(status_code=400, detail="Quantidade deve ser maior que zero")

    # Idempotência por scan_id: se o scan já foi processado (ex: timeout de rede), retorna qtde atual
    if body.scan_id:
        try:
            with get_connection() as con:
                cur = con.cursor()
                cur.execute("SELECT COUNT(*) FROM SCANS_PROCESSADOS WHERE SCAN_ID = ?", (body.scan_id,))
                if cur.fetchone()[0] > 0:
                    cur.execute(
                        "SELECT COALESCE(QTDE, 0) FROM INVENTARIO_TEMP "
                        "WHERE CDPRODUTO = ? AND CDDEPOSITO = ? AND SESSION_ID = ?",
                        (body.cdproduto, body.cddeposito, body.session_id),
                    )
                    row = cur.fetchone()
                    nova_qtde = float(row[0]) if row else body.qtde
                    return BipagemResponse(
                        cdproduto=body.cdproduto, cddeposito=body.cddeposito,
                        qtde=body.qtde, nova_qtde=nova_qtde,
                        mensagem="Scan já processado (idempotente)", alerta=None,
                    )
        except Exception as e:
            print(f"[scan] idempotência check: {e}")

    # Verifica status da sessão e cria registro se não existir
    # (compatibilidade: usuário pode ter selecionado depósito offline e voltou a escanear online)
    if body.session_id:
        try:
            with get_connection() as con:
                cur = con.cursor()
                cur.execute(
                    "SELECT STATUS FROM INVENTARIO_SESSAO WHERE SESSION_ID = ?",
                    (body.session_id,),
                )
                row_s = cur.fetchone()
                if row_s:
                    st = (row_s[0] or "").upper()
                    if st in ("CONSOLIDADA", "ENCERRADA"):
                        raise HTTPException(
                            status_code=409,
                            detail=f"Sessão já foi {st.lower()} — nova bipagem rejeitada",
                        )
                else:
                    cur.execute(
                        "INSERT INTO INVENTARIO_SESSAO (SESSION_ID, CDDEPOSITO, USUARIO, STATUS) "
                        "VALUES (?, ?, ?, 'ABERTA')",
                        (body.session_id, body.cddeposito, current_user.get("login", "")),
                    )
        except HTTPException:
            raise
        except Exception as e:
            print(f"[bipagem] sessao init: {e}")

    nova_qtde = 0.0
    mensagem = ""
    nome_produto = f"#{body.cdproduto}"
    qtde_sistema = 0.0

    with get_connection() as con:
        cur = con.cursor()

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

        primeiro_scan_na_sessao = False

        if body.session_id:
            # Passo 1: acumular na linha já existente desta sessão (SOMA)
            cur.execute(
                "UPDATE INVENTARIO_TEMP SET QTDE = QTDE + ?, OPERADOR = ? "
                "WHERE CDPRODUTO = ? AND CDDEPOSITO = ? AND SESSION_ID = ? RETURNING QTDE",
                (body.qtde, body.operador, body.cdproduto, body.cddeposito, body.session_id),
            )
            row = cur.fetchone()
            if not row:
                # Passo 2: existe linha de outra sessão ou do Automec → assumir e SUBSTITUIR qty
                primeiro_scan_na_sessao = True
                cur.execute(
                    "UPDATE INVENTARIO_TEMP "
                    "SET QTDE = ?, SESSION_ID = ?, OPERADOR = ?, "
                    "QTDEATUAL_SNAP = COALESCE(QTDEATUAL_SNAP, ?), ORIGEM = 'INVEC' "
                    "WHERE CDPRODUTO = ? AND CDDEPOSITO = ? RETURNING QTDE",
                    (body.qtde, body.session_id, body.operador, qtde_sistema,
                     body.cdproduto, body.cddeposito),
                )
                row = cur.fetchone()
        else:
            cur.execute(
                "UPDATE INVENTARIO_TEMP SET QTDE = QTDE + ?, OPERADOR = ?, "
                "QTDEATUAL_SNAP = COALESCE(QTDEATUAL_SNAP, ?), ORIGEM = 'INVEC' "
                "WHERE CDPRODUTO = ? AND CDDEPOSITO = ? RETURNING QTDE",
                (body.qtde, body.operador, qtde_sistema, body.cdproduto, body.cddeposito),
            )
            row = cur.fetchone()
            if not row:
                primeiro_scan_na_sessao = True

        if row:
            nova_qtde = float(row[0])
            mensagem = "Bipagem registrada" if primeiro_scan_na_sessao else f"Quantidade atualizada para {nova_qtde}"
        else:
            primeiro_scan_na_sessao = True
            nova_qtde = body.qtde
            if body.session_id:
                cur.execute(
                    "INSERT INTO INVENTARIO_TEMP "
                    "(CDPRODUTO, CDDEPOSITO, QTDE, OPERADOR, QTDEATUAL_SNAP, SESSION_ID, ORIGEM) "
                    "VALUES (?, ?, ?, ?, ?, ?, 'INVEC')",
                    (body.cdproduto, body.cddeposito, body.qtde, body.operador, qtde_sistema, body.session_id),
                )
            else:
                cur.execute(
                    "INSERT INTO INVENTARIO_TEMP "
                    "(CDPRODUTO, CDDEPOSITO, QTDE, OPERADOR, QTDEATUAL_SNAP, ORIGEM) "
                    "VALUES (?, ?, ?, ?, ?, 'INVEC')",
                    (body.cdproduto, body.cddeposito, body.qtde, body.operador, qtde_sistema),
                )
            mensagem = "Bipagem registrada"

        if primeiro_scan_na_sessao:
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
                    cddeposito=body.cddeposito, cdproduto=body.cdproduto,
                    produto=nome_produto, operador=body.operador,
                    qtde_antes=qtde_sistema, qtde_depois=nova_qtde,
                    motivo="Produto excluído da contagem e re-escaneado na mesma sessão",
                    device_id=body.device_id, session_id=body.session_id,
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
            cddeposito=body.cddeposito, cdproduto=body.cdproduto,
            produto=nome_produto, operador=body.operador,
            qtde_antes=qtde_sistema, qtde_depois=nova_qtde,
            motivo=alerta, device_id=body.device_id, session_id=body.session_id,
        )

    # Registra scan_id para idempotência futura (ex: retry via lote)
    if body.scan_id:
        try:
            with get_connection() as con:
                cur = con.cursor()
                cur.execute(
                    "INSERT INTO SCANS_PROCESSADOS (SCAN_ID, SESSION_ID, CDPRODUTO) VALUES (?, ?, ?)",
                    (body.scan_id, body.session_id, body.cdproduto),
                )
        except Exception:
            pass

    return BipagemResponse(
        cdproduto=body.cdproduto,
        cddeposito=body.cddeposito,
        qtde=body.qtde,
        nova_qtde=nova_qtde,
        mensagem=mensagem,
        alerta=alerta,
    )


@router.post("/bipagem/lote", response_model=LoteSyncResponse)
def sincronizar_lote(
    body: LoteBipagemRequest,
    current_user: dict = Depends(get_current_user),
):
    _verificar_acesso_deposito(current_user, body.cddeposito)

    sincronizados = 0
    alertas: list[str] = []

    if body.lote_id:
        try:
            with get_connection() as con:
                cur = con.cursor()
                cur.execute(
                    "SELECT COUNT(*) FROM LOTES_SYNC_PROCESSADOS WHERE LOTE_ID = ?",
                    (body.lote_id,),
                )
                if cur.fetchone()[0] > 0:
                    return LoteSyncResponse(sincronizados=0, alertas=[])
        except Exception as e:
            print(f"[lote] idempotência check: {e}")

    try:
        with get_connection() as con:
            cur = con.cursor()
            cur.execute(
                "SELECT STATUS FROM INVENTARIO_SESSAO WHERE SESSION_ID = ?",
                (body.session_id,),
            )
            row = cur.fetchone()
            if row:
                status_sessao = (row[0] or "ABERTA").upper()
                if status_sessao in ("ENCERRADA", "CONSOLIDADA"):
                    raise HTTPException(
                        status_code=409,
                        detail=f"Sessão já está {status_sessao.lower()} — lote rejeitado para evitar dados fantasmas.",
                    )
            else:
                cur.execute(
                    "INSERT INTO INVENTARIO_SESSAO (SESSION_ID, CDDEPOSITO, USUARIO, STATUS) "
                    "VALUES (?, ?, ?, 'ABERTA')",
                    (body.session_id, body.cddeposito, current_user.get("login", "")),
                )
    except HTTPException:
        raise
    except Exception as e:
        print(f"[lote] INVENTARIO_SESSAO upsert: {e}")

    with get_connection() as con:
        cur = con.cursor()
        for item in body.bipagens:
            # Idempotência por scan_id: desconta scans já processados individualmente (ex: timeout de rede)
            net_qtde = item.qtde
            novos_scan_ids: list[str] = []
            if item.scan_ids:
                placeholders = ",".join(["?"] * len(item.scan_ids))
                try:
                    cur.execute(
                        f"SELECT COUNT(*) FROM SCANS_PROCESSADOS WHERE SCAN_ID IN ({placeholders})",
                        tuple(item.scan_ids),
                    )
                    ja_processados = cur.fetchone()[0] or 0
                    net_qtde = max(0.0, item.qtde - float(ja_processados))
                    # Scan_ids que são realmente novos (não estão em SCANS_PROCESSADOS)
                    cur.execute(
                        f"SELECT SCAN_ID FROM SCANS_PROCESSADOS WHERE SCAN_ID IN ({placeholders})",
                        tuple(item.scan_ids),
                    )
                    ja_ids = {r[0] for r in cur.fetchall()}
                    novos_scan_ids = [s for s in item.scan_ids if s not in ja_ids]
                except Exception as e:
                    print(f"[lote] scan_id dedup: {e}")
                    novos_scan_ids = list(item.scan_ids)

            if net_qtde == 0:
                sincronizados += 1
                # Registra novos scan_ids mesmo sem atualizar INVENTARIO_TEMP
                for sid in novos_scan_ids:
                    try:
                        cur.execute(
                            "INSERT INTO SCANS_PROCESSADOS (SCAN_ID, SESSION_ID, CDPRODUTO) VALUES (?, ?, ?)",
                            (sid, body.session_id, item.cdproduto),
                        )
                    except Exception:
                        pass
                continue

            # Passo 1: acumular na linha desta sessão (SOMA)
            cur.execute(
                "UPDATE INVENTARIO_TEMP SET QTDE = QTDE + ?, OPERADOR = ? "
                "WHERE CDPRODUTO = ? AND CDDEPOSITO = ? AND SESSION_ID = ? RETURNING QTDE",
                (net_qtde, item.operador, item.cdproduto, body.cddeposito, body.session_id),
            )
            row = cur.fetchone()
            if not row:
                # Passo 2: assumir linha de outra sessão/Automec → SUBSTITUIR qty
                cur.execute(
                    "UPDATE INVENTARIO_TEMP "
                    "SET QTDE = ?, SESSION_ID = ?, OPERADOR = ?, "
                    "QTDEATUAL_SNAP = COALESCE(QTDEATUAL_SNAP, ?), ORIGEM = 'INVEC' "
                    "WHERE CDPRODUTO = ? AND CDDEPOSITO = ? RETURNING QTDE",
                    (net_qtde, body.session_id, item.operador, item.qtde_sistema,
                     item.cdproduto, body.cddeposito),
                )
                row = cur.fetchone()
            if row:
                nova_qtde = float(row[0])
            else:
                nova_qtde = net_qtde
                cur.execute(
                    "INSERT INTO INVENTARIO_TEMP "
                    "(CDPRODUTO, CDDEPOSITO, QTDE, OPERADOR, QTDEATUAL_SNAP, SESSION_ID, ORIGEM) "
                    "VALUES (?, ?, ?, ?, ?, ?, 'INVEC')",
                    (item.cdproduto, body.cddeposito, net_qtde, item.operador,
                     item.qtde_sistema, body.session_id),
                )
            sincronizados += 1

            # Registra novos scan_ids para idempotência futura
            for sid in novos_scan_ids:
                try:
                    cur.execute(
                        "INSERT INTO SCANS_PROCESSADOS (SCAN_ID, SESSION_ID, CDPRODUTO) VALUES (?, ?, ?)",
                        (sid, body.session_id, item.cdproduto),
                    )
                except Exception:
                    pass

            if item.qtde_sistema >= ALERTA_MINIMO and nova_qtde > item.qtde_sistema * ALERTA_MULTIPLO:
                msg = (
                    f"Produto #{item.cdproduto} ({item.produto}): "
                    f"qtde {nova_qtde:.0f} excede {ALERTA_MULTIPLO:.0f}x o sistema ({item.qtde_sistema:.0f})"
                )
                alertas.append(msg)
                _registrar_log(
                    "ALERTA",
                    login_usuario=current_user.get("login", ""),
                    cddeposito=body.cddeposito, cdproduto=item.cdproduto,
                    produto=item.produto, operador=item.operador,
                    qtde_antes=item.qtde_sistema, qtde_depois=nova_qtde,
                    motivo=msg, device_id=item.device_id, session_id=body.session_id,
                )

    if body.lote_id:
        try:
            with get_connection() as con:
                cur = con.cursor()
                cur.execute(
                    "INSERT INTO LOTES_SYNC_PROCESSADOS (LOTE_ID, SESSION_ID) VALUES (?, ?)",
                    (body.lote_id, body.session_id),
                )
        except Exception:
            pass

    _registrar_log(
        "SYNC_LOTE",
        login_usuario=current_user.get("login", ""),
        cddeposito=body.cddeposito,
        qtde_depois=float(sincronizados),
        motivo=(
            f"Lote offline: {sincronizados} itens · session={body.session_id}"
            + (f" · lote={body.lote_id}" if body.lote_id else "")
        ),
        device_id=body.bipagens[0].device_id if body.bipagens else None,
        session_id=body.session_id,
    )

    return LoteSyncResponse(sincronizados=sincronizados, alertas=alertas)


@router.get("/relatorio/{cddeposito}", response_model=list[ItemRelatorio])
def relatorio_inventario(
    cddeposito: int,
    session_id: Optional[str] = Query(default=None),
    considerar_entrega: bool = Query(default=False),
    current_user: dict = Depends(get_current_user),
):
    _verificar_acesso_deposito(current_user, cddeposito)

    with get_connection() as con:
        cur = con.cursor()
        if session_id:
            session_filter = "AND IT.SESSION_ID = ?"
            params = (cddeposito, cddeposito, session_id)
        else:
            session_filter = "AND IT.SESSION_ID IS NULL"
            params = (cddeposito, cddeposito)
        cur.execute(
            f"""
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
                IT.OPERADOR
            FROM PRODUTO P
            JOIN INVENTARIO_TEMP IT
                ON IT.CDPRODUTO = P.CDPRODUTO AND IT.CDDEPOSITO = ?
            WHERE 1=1 {session_filter}
            ORDER BY P.PRODUTO
            """,
            params,
        )
        rows = fetchall_as_dict(cur)

        # Busca quantidades em entrega (SAIDAPRODUTO com IDENTREGA definido) quando flag ativo
        qtde_entrega_map: dict[int, float] = {}
        if considerar_entrega:
            try:
                qtde_entrega_map = _buscar_qtde_entrega(con, cddeposito)
            except Exception as e:
                print(f"[relatorio] SAIDAPRODUTO indisponível: {e}")

        result = []
        for row in rows:
            cdproduto = row["cdproduto"]
            qtde_sistema_base = float(row.get("qtde_sistema") or 0)
            qtde_entrega = qtde_entrega_map.get(cdproduto, 0.0)
            qtde_sistema_efetivo = qtde_sistema_base + qtde_entrega
            qtde_contada = float(row.get("qtde_contada") or 0)
            row["qtde_sistema"] = qtde_sistema_efetivo
            row["qtde_entrega"] = qtde_entrega if qtde_entrega > 0.001 else None
            row["diferenca"] = qtde_contada - qtde_sistema_efetivo
            result.append(row)

        return result


@router.get("/resumo/{cddeposito}", response_model=ResumoContagem)
def resumo_contagem(
    cddeposito: int,
    session_id: Optional[str] = Query(default=None),
    current_user: dict = Depends(get_current_user),
):
    _verificar_acesso_deposito(current_user, cddeposito)

    with get_connection() as con:
        cur = con.cursor()

        cur.execute(
            "SELECT COUNT(*) FROM MOVIMENTO M WHERE M.CDDEPOSITO = ? AND M.QTDEATUAL > 0",
            (cddeposito,),
        )
        total_deposito = cur.fetchone()[0] or 0

        if session_id:
            cur.execute(
                "SELECT COUNT(*) FROM INVENTARIO_TEMP WHERE CDDEPOSITO = ? AND SESSION_ID = ?",
                (cddeposito, session_id),
            )
        else:
            cur.execute(
                "SELECT COUNT(*) FROM INVENTARIO_TEMP WHERE CDDEPOSITO = ? AND SESSION_ID IS NULL",
                (cddeposito,),
            )
        contados = cur.fetchone()[0] or 0

        if session_id:
            nao_contados_filter = "AND IT.SESSION_ID = ?"
            nao_params = (cddeposito, cddeposito, session_id)
        else:
            nao_contados_filter = "AND IT.SESSION_ID IS NULL"
            nao_params = (cddeposito, cddeposito)
        cur.execute(
            f"""
            SELECT FIRST 50 P.PRODUTO
            FROM MOVIMENTO M
            JOIN PRODUTO P ON CAST(P.CDPRODUTO AS VARCHAR(10)) = M.CDPRODUTO
            WHERE M.CDDEPOSITO = ? AND M.QTDEATUAL > 0
              AND NOT EXISTS (
                  SELECT 1 FROM INVENTARIO_TEMP IT
                  WHERE IT.CDPRODUTO = P.CDPRODUTO AND IT.CDDEPOSITO = ?
                  {nao_contados_filter}
              )
            ORDER BY P.PRODUTO
            """,
            nao_params,
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
    _verificar_acesso_deposito(current_user, body.cddeposito)

    # BANCO-1: lock em memória (guarda primário no processo atual)
    with _consolidando_lock:
        if body.cddeposito in _consolidando:
            raise HTTPException(
                status_code=409,
                detail="Já existe uma consolidação em andamento para este depósito. Aguarde.",
            )
        _consolidando.add(body.cddeposito)

    db_lock_acquired = False
    try:
        # BANCO-1: lock persistente no banco — protege contra restart do serviço no meio
        if body.session_id:
            with get_connection() as con:
                cur = con.cursor()
                cur.execute(
                    "SELECT STATUS FROM INVENTARIO_SESSAO WHERE SESSION_ID = ?",
                    (body.session_id,),
                )
                row_sessao = cur.fetchone()
                if row_sessao:
                    status_atual = (row_sessao[0] or "").upper()
                    if status_atual == "CONSOLIDADA":
                        raise HTTPException(
                            status_code=409,
                            detail="Esta sessão já foi consolidada anteriormente.",
                        )
                    if status_atual == "CONSOLIDANDO":
                        raise HTTPException(
                            status_code=409,
                            detail="Consolidação já em andamento para esta sessão. Aguarde ou verifique o histórico.",
                        )
                    # STATUS IS NULL = linha criada antes da migration da coluna (tratada como ABERTA)
                    cur.execute(
                        "UPDATE INVENTARIO_SESSAO SET STATUS = 'CONSOLIDANDO' "
                        "WHERE SESSION_ID = ? AND (STATUS = 'ABERTA' OR STATUS IS NULL)",
                        (body.session_id,),
                    )
                    if cur.rowcount == 0:
                        raise HTTPException(
                            status_code=409,
                            detail="Não foi possível adquirir lock de consolidação. Tente novamente.",
                        )
                    db_lock_acquired = True

        with get_connection() as con:
            cur = con.cursor()

            cur.execute(
                "SELECT IDUSUARIO FROM USUARIOS WHERE LOWER(LOGIN) = LOWER(?)",
                (current_user.get("login", ""),),
            )
            row_user = cur.fetchone()
            idusuario = row_user[0] if row_user else 1

            # Lê IDEMPRESA diretamente do depósito — cada depósito pertence a uma empresa
            cur.execute("SELECT IDEMPRESA FROM DEPOSITO WHERE CDDEPOSITO = ?", (body.cddeposito,))
            row_dep = cur.fetchone()
            idempresa = int(row_dep[0]) if row_dep and row_dep[0] else _IDEMPRESA_FALLBACK

            if body.session_id:
                session_where = "AND IT.SESSION_ID = ?"
                itens_params = (body.cddeposito, body.session_id)
            else:
                session_where = "AND IT.SESSION_ID IS NULL"
                itens_params = (body.cddeposito,)

            # PERF-2: pré-busca QTDEATUAL de MOVIMENTO em uma única query antes do loop
            movimento_qtde: dict[str, float] = {}
            try:
                cur.execute(
                    "SELECT M.CDPRODUTO, M.QTDEATUAL FROM MOVIMENTO M WHERE M.CDDEPOSITO = ?",
                    (body.cddeposito,),
                )
                for row in cur.fetchall():
                    cprod = str(row[0])
                    if cprod not in movimento_qtde:
                        movimento_qtde[cprod] = float(row[1] or 0)
            except Exception as e:
                print(f"[consolidar] pre-fetch MOVIMENTO: {e}")

            cur.execute(
                f"""
                SELECT
                    IT.CDPRODUTO,
                    IT.CDDEPOSITO,
                    IT.QTDE                                      AS QTDE_CONTADA,
                    IT.OPERADOR,
                    CAST(IT.CDPRODUTO AS VARCHAR(10))            AS CDPRODUTO_STR,
                    COALESCE(P.CDUNIDADE, 'UN')                  AS CDUNIDADE,
                    COALESCE(P.PRODUTO, '')                      AS PRODUTO,
                    IT.QTDEATUAL_SNAP,
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
                WHERE IT.CDDEPOSITO = ? {session_where}
                """,
                itens_params,
            )
            itens = fetchall_as_dict(cur)

            total = len(itens)
            if total == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Nenhuma bipagem pendente para este depósito",
                )

            # FRAUDE-2: verifica se houve edições nesta sessão
            teve_edicoes = False
            if body.session_id:
                try:
                    cur.execute(
                        "SELECT COUNT(*) FROM LOG_INVENTARIO "
                        "WHERE SESSION_ID = ? AND TIPO IN ('EDICAO', 'EDICAO_SUSPEITA')",
                        (body.session_id,),
                    )
                    teve_edicoes = (cur.fetchone()[0] or 0) > 0
                except Exception:
                    pass

            qtde_entrega_map: dict[int, float] = {}
            if body.considerar_entrega:
                try:
                    qtde_entrega_map = _buscar_qtde_entrega(con, body.cddeposito)
                except Exception as e:
                    print(f"[consolidar] SAIDAPRODUTO indisponível, ignorando entregas pendentes: {e}")

            divergencias = 0
            for item in itens:
                # PERF-2: usa mapa pré-buscado em vez de subquery por item
                _snap = item.get("qtdeatual_snap")
                qtde_atual = float(_snap) if _snap is not None else float(movimento_qtde.get(item["cdproduto_str"], 0))
                qtdeentrega = qtde_entrega_map.get(item["cdproduto"], 0.0)
                baseline = qtde_atual + qtdeentrega
                if abs(float(item["qtde_contada"] or 0) - baseline) > 0.001:
                    divergencias += 1

            is_supervisor = (
                current_user.get("login", "").upper() == "MI"
                or (current_user.get("idgrupo") or 3) in (1, 2)
            )
            if (
                divergencias >= LIMIAR_RECONTAGEM_MINIMO
                and (divergencias / total) >= LIMIAR_RECONTAGEM
                and not body.recontagem_confirmada
                and not is_supervisor
            ):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        f"{divergencias} de {total} itens "
                        f"({divergencias / total:.0%}) têm divergência. "
                        "Faça a recontagem antes de consolidar."
                    ),
                )

            # FRAUDE-2: exige supervisor se houve edições, mesmo sem divergências aparentes
            supervisor_login_validado = None
            if divergencias > 0 or teve_edicoes:
                motivo_supervisor = (
                    f"Há {divergencias} divergências." if divergencias > 0 else ""
                )
                if teve_edicoes and divergencias == 0:
                    motivo_supervisor = "Houve edições de quantidade nesta sessão."

                # Admin/gerente/MI — auto-autoriza sem precisar de outro supervisor
                if is_supervisor:
                    supervisor_login_validado = current_user.get("login")
                # SEC-2: aceita supervisor_token (pré-autenticado) ou supervisor_senha (legado)
                elif body.supervisor_token:
                    token_data = _validar_supervisor_token(body.supervisor_token)
                    supervisor_login_validado = token_data["login"]
                    is_mi_sup = token_data.get("login", "").upper() == "MI"
                    if not is_mi_sup and token_data["idgrupo"] not in (1, 2):
                        raise HTTPException(
                            status_code=403,
                            detail="Supervisor precisa ser gerente ou administrador",
                        )
                    quem_consolida_operador = not is_supervisor
                    if supervisor_login_validado.lower() == current_user.get("login", "").lower() and quem_consolida_operador:
                        raise HTTPException(
                            status_code=400,
                            detail="Operadores não podem autorizar a própria consolidação.",
                        )
                elif body.supervisor_login and body.supervisor_senha:
                    cur.execute(
                        "SELECT IDUSUARIO, LOGIN, IDGRUPO, SENHAMOBILE FROM USUARIOS "
                        "WHERE LOWER(LOGIN) = LOWER(?) AND (INATIVO IS NULL OR INATIVO = 0)",
                        (body.supervisor_login,),
                    )
                    supervisor = fetchone_as_dict(cur)
                    if not supervisor:
                        raise HTTPException(status_code=401, detail="Credenciais do supervisor inválidas")
                    senha_mobile = supervisor.get("senhamobile") or ""
                    if not senha_mobile:
                        raise HTTPException(
                            status_code=403,
                            detail="Supervisor não possui senha mobile configurada.",
                        )
                    if senha_mobile != body.supervisor_senha:
                        raise HTTPException(status_code=401, detail="Credenciais do supervisor inválidas")
                    is_mi_sup = supervisor.get("login", "").upper() == "MI"
                    if not is_mi_sup and (supervisor.get("idgrupo") or 3) not in (1, 2):
                        raise HTTPException(
                            status_code=403,
                            detail="Supervisor precisa ser gerente ou administrador",
                        )
                    quem_consolida_operador = not is_supervisor
                    mesmo_usuario = supervisor["login"].lower() == current_user.get("login", "").lower()
                    if mesmo_usuario and quem_consolida_operador:
                        raise HTTPException(
                            status_code=400,
                            detail="Operadores não podem autorizar a própria consolidação.",
                        )
                    supervisor_login_validado = supervisor["login"]
                else:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"{motivo_supervisor} Supervisor obrigatório. Use pré-autenticação ou informe login e senha.",
                    )

            cur.execute("SELECT GEN_ID(GEN_MOV_PRODUTO, 1) FROM RDB$DATABASE")
            idinventario = cur.fetchone()[0]

            cur2 = con.cursor()
            itens_divergentes = []

            for item in itens:
                cdproduto     = item["cdproduto"]
                cdproduto_str = item["cdproduto_str"]
                qtde_contada  = float(item["qtde_contada"] or 0)
                # PERF-2: usa mapa pré-buscado
                _snap = item.get("qtdeatual_snap")
                qtde_atual    = float(_snap) if _snap is not None else float(movimento_qtde.get(cdproduto_str, 0))
                fatorconv     = float(item["fatorconv"] or 1)
                vlcusto       = float(item["vlcusto"] or 0)
                cdunidade     = item["cdunidade"]
                operador_item = item.get("operador") or body.operador or ""
                nome_produto  = item["produto"] or f"#{cdproduto}"
                qtdeentrega   = qtde_entrega_map.get(cdproduto, 0.0)

                qtdanterior, qtentrada, qtsaida, vl_perda_ganho, baseline_report = \
                    _calcular_delta_estoque(qtde_contada, qtde_atual, qtdeentrega, vlcusto)

                if abs(qtde_contada - baseline_report) > 0.001:
                    itens_divergentes.append({
                        "produto": nome_produto,
                        "qtde_sistema": baseline_report,
                        "qtde_contada": qtde_contada,
                        "diferenca": qtde_contada - baseline_report,
                    })

                if vl_perda_ganho is not None:
                    cur2.execute(
                        "INSERT INTO MOV_PRODUTO "
                        "(IDEMPRESA, CDPRODUTO, CDDEPOSITO, TIPOMOVIMENTO, CDNATOP, DTMOVIMENTO, HISTORICO, "
                        "FATORCONV, QTENTRADA, QTSAIDA, IDUSUARIO, CDUNIDADE, IDINVENTARIO, "
                        "QTDINVENTARIO, QTDANTERIOR, VL_PERDA_GANHO, SIST_ALT) "
                        "VALUES (?, ?, ?, 5, '0000', CURRENT_DATE, 'Ajuste na Tela de Inventário', "
                        "?, ?, ?, ?, ?, ?, ?, ?, ?, 'INV_APP')",
                        (idempresa, cdproduto_str, body.cddeposito, fatorconv,
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
                        (idempresa, cdproduto_str, body.cddeposito, fatorconv,
                         qtentrada, qtsaida, idusuario, cdunidade, idinventario,
                         qtde_contada, qtdanterior),
                    )

            if body.session_id:
                # BANCO-3: filtra ORIGEM='INVEC' para não apagar dados do Automec
                cur2.execute(
                    "DELETE FROM INVENTARIO_TEMP "
                    "WHERE CDDEPOSITO = ? AND SESSION_ID = ? AND (ORIGEM = 'INVEC' OR ORIGEM IS NULL)",
                    (body.cddeposito, body.session_id),
                )
                cur2.execute(
                    "UPDATE INVENTARIO_SESSAO SET STATUS = 'CONSOLIDADA', FIM = CURRENT_TIMESTAMP "
                    "WHERE SESSION_ID = ?",
                    (body.session_id,),
                )
                db_lock_acquired = False  # não precisa restaurar no finally
            else:
                cur2.execute(
                    "DELETE FROM INVENTARIO_TEMP "
                    "WHERE CDDEPOSITO = ? AND SESSION_ID IS NULL AND ORIGEM = 'INVEC'",
                    (body.cddeposito,),
                )

            supervisor_label = f" (supervisor: {supervisor_login_validado})" if supervisor_login_validado else ""
            if teve_edicoes and not divergencias:
                supervisor_label += " [edições detectadas na sessão]"

            cur2.execute(
                """
                INSERT INTO LOG_INVENTARIO
                    (TIPO, CDDEPOSITO, OPERADOR, LOGIN_USUARIO, QTDE_DEPOIS, MOTIVO, SESSION_ID, DATA_HORA)
                VALUES ('CONSOLIDACAO', ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (body.cddeposito, body.operador, current_user.get("login", ""),
                 float(total),
                 f"{total} itens · {divergencias} divergências{supervisor_label} · inv#{idinventario}"
                 + (f" · session={body.session_id}" if body.session_id else ""),
                 body.session_id),
            )

            # Auditoria extra quando supervisor autoriza sem recontagem
            if body.justificativa_sem_recontagem and divergencias > 0:
                cur2.execute(
                    """
                    INSERT INTO LOG_INVENTARIO
                        (TIPO, CDDEPOSITO, OPERADOR, LOGIN_USUARIO, MOTIVO, SESSION_ID, DATA_HORA)
                    VALUES ('CONSOLID_SEM_RECONTAGEM', ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    (body.cddeposito, body.operador, supervisor_login_validado or current_user.get("login", ""),
                     body.justificativa_sem_recontagem, body.session_id),
                )

        _salvar_relatorio(
            cddeposito=body.cddeposito,
            operador=body.operador or "",
            login_usuario=current_user.get("login", ""),
            total=total,
            divergencias=divergencias,
            supervisor=supervisor_login_validado or "",
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
        # BANCO-1: restaura STATUS='ABERTA' se o lock de banco foi adquirido mas a consolidação falhou
        if db_lock_acquired and body.session_id:
            try:
                with get_connection() as con:
                    cur = con.cursor()
                    cur.execute(
                        "UPDATE INVENTARIO_SESSAO SET STATUS = 'ABERTA' WHERE SESSION_ID = ? AND STATUS = 'CONSOLIDANDO'",
                        (body.session_id,),
                    )
            except Exception:
                pass


@router.get("/historico/{cddeposito}", response_model=list[ItemHistorico])
def historico_inventario(
    cddeposito: int,
    current_user: dict = Depends(get_current_user),
):
    _verificar_acesso_deposito(current_user, cddeposito)

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
                COALESCE(
                    (SELECT FIRST 1 LI.DATA_HORA
                     FROM LOG_INVENTARIO LI
                     WHERE LI.TIPO = 'CONSOLIDACAO'
                       AND LI.CDDEPOSITO = MP.CDDEPOSITO
                       AND LI.MOTIVO CONTAINING ('inv#' || CAST(MP.IDINVENTARIO AS VARCHAR(10)))
                     ORDER BY LI.DATA_HORA DESC),
                    CAST(MP.DTMOVIMENTO AS TIMESTAMP)
                )                   AS DATA,
                MP.HISTORICO        AS OPERADOR
            FROM MOV_PRODUTO MP
            JOIN PRODUTO P ON CAST(P.CDPRODUTO AS VARCHAR(10)) = MP.CDPRODUTO
            JOIN DEPOSITO D ON D.CDDEPOSITO = MP.CDDEPOSITO
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
    session_id: Optional[str] = Query(default=None),
    current_user: dict = Depends(get_current_user),
):
    _verificar_acesso_deposito(current_user, cddeposito)

    if not motivo or not motivo.strip():
        raise HTTPException(status_code=400, detail="Motivo é obrigatório para excluir uma bipagem")

    existente = None
    with get_connection() as con:
        cur = con.cursor()
        if session_id:
            cur.execute(
                "SELECT IT.QTDE, P.PRODUTO FROM INVENTARIO_TEMP IT "
                "JOIN PRODUTO P ON P.CDPRODUTO = IT.CDPRODUTO "
                "WHERE IT.CDPRODUTO = ? AND IT.CDDEPOSITO = ? AND IT.SESSION_ID = ?",
                (cdproduto, cddeposito, session_id),
            )
        else:
            cur.execute(
                "SELECT IT.QTDE, P.PRODUTO FROM INVENTARIO_TEMP IT "
                "JOIN PRODUTO P ON P.CDPRODUTO = IT.CDPRODUTO "
                "WHERE IT.CDPRODUTO = ? AND IT.CDDEPOSITO = ? AND IT.SESSION_ID IS NULL",
                (cdproduto, cddeposito),
            )
        existente = fetchone_as_dict(cur)
        if session_id:
            cur.execute(
                "DELETE FROM INVENTARIO_TEMP WHERE CDPRODUTO = ? AND CDDEPOSITO = ? AND SESSION_ID = ?",
                (cdproduto, cddeposito, session_id),
            )
        else:
            cur.execute(
                "DELETE FROM INVENTARIO_TEMP WHERE CDPRODUTO = ? AND CDDEPOSITO = ? AND SESSION_ID IS NULL",
                (cdproduto, cddeposito),
            )

    if existente:
        _registrar_log(
            "EXCLUSAO",
            login_usuario=current_user.get("login", ""),
            cddeposito=cddeposito, cdproduto=cdproduto,
            produto=existente.get("produto"),
            qtde_antes=existente.get("qtde"),
            motivo=motivo, device_id=device_id, session_id=session_id,
        )

    return {"mensagem": "Bipagem removida"}


@router.put("/bipagem/{cdproduto}")
def editar_bipagem(
    cdproduto: int,
    body: EditarBipagemRequest,
    current_user: dict = Depends(get_current_user),
):
    _verificar_acesso_deposito(current_user, body.cddeposito)

    if body.qtde < 0:
        raise HTTPException(status_code=400, detail="Quantidade não pode ser negativa")
    anterior = None
    snap = None
    with get_connection() as con:
        cur = con.cursor()
        if body.session_id:
            cur.execute(
                "SELECT IT.QTDE, IT.QTDEATUAL_SNAP, P.PRODUTO FROM INVENTARIO_TEMP IT "
                "JOIN PRODUTO P ON P.CDPRODUTO = IT.CDPRODUTO "
                "WHERE IT.CDPRODUTO = ? AND IT.CDDEPOSITO = ? AND IT.SESSION_ID = ?",
                (cdproduto, body.cddeposito, body.session_id),
            )
        else:
            cur.execute(
                "SELECT IT.QTDE, IT.QTDEATUAL_SNAP, P.PRODUTO FROM INVENTARIO_TEMP IT "
                "JOIN PRODUTO P ON P.CDPRODUTO = IT.CDPRODUTO "
                "WHERE IT.CDPRODUTO = ? AND IT.CDDEPOSITO = ? AND IT.SESSION_ID IS NULL",
                (cdproduto, body.cddeposito),
            )
        anterior = fetchone_as_dict(cur)
        if not anterior:
            raise HTTPException(status_code=404, detail="Item não encontrado na contagem")
        snap = anterior.get("qtdeatual_snap")
        if body.session_id:
            cur.execute(
                "UPDATE INVENTARIO_TEMP SET QTDE = ? WHERE CDPRODUTO = ? AND CDDEPOSITO = ? AND SESSION_ID = ?",
                (body.qtde, cdproduto, body.cddeposito, body.session_id),
            )
        else:
            cur.execute(
                "UPDATE INVENTARIO_TEMP SET QTDE = ? WHERE CDPRODUTO = ? AND CDDEPOSITO = ? AND SESSION_ID IS NULL",
                (body.qtde, cdproduto, body.cddeposito),
            )

    qtde_antes = anterior.get("qtde") if anterior else None
    produto_nome = anterior.get("produto") if anterior else None

    tipo_log = "EDICAO"
    motivo_extra = ""

    # Padrão suspeito: edição faz coincidir exatamente com o sistema
    if snap is not None and abs(body.qtde - float(snap)) < 0.001 and qtde_antes is not None:
        if abs(float(qtde_antes) - float(snap)) > 0.001:
            tipo_log = "EDICAO_SUSPEITA"
            motivo_extra = f" [ALERTA: contagem editada de {qtde_antes:.0f} para {body.qtde:.0f} coincidindo com sistema ({snap:.0f})]"

    # FRAUDE-1: redução > 30% por operador também é suspeita
    if tipo_log == "EDICAO" and qtde_antes is not None and float(qtde_antes) > 0:
        reducao = (float(qtde_antes) - body.qtde) / float(qtde_antes)
        if reducao > 0.30 and (current_user.get("idgrupo") or 3) == 3:
            tipo_log = "EDICAO_SUSPEITA"
            motivo_extra = f" [ALERTA: operador reduziu {reducao:.0%} da quantidade ({qtde_antes:.0f}→{body.qtde:.0f})]"

    _registrar_log(
        tipo_log,
        login_usuario=current_user.get("login", ""),
        cddeposito=body.cddeposito, cdproduto=cdproduto,
        produto=produto_nome, qtde_antes=qtde_antes, qtde_depois=body.qtde,
        motivo=(body.motivo or "") + motivo_extra,
        device_id=body.device_id, session_id=body.session_id,
    )

    return {"mensagem": f"Quantidade atualizada para {body.qtde}"}


@router.get("/log/{cddeposito}", response_model=list[LogItem])
def log_auditoria(
    cddeposito: int,
    limit: int = Query(default=200, le=500),
    current_user: dict = Depends(get_current_user),
):
    # MI é superadmin — acesso total ao log. Para os demais, exige gerente ou admin.
    is_mi = current_user.get("login", "").upper() == "MI"
    _role = current_user.get("role", "operador")
    idgrupo = current_user.get("idgrupo") or (1 if _role == "admin" else 2 if _role == "gerente" else 3)
    if not is_mi and idgrupo not in (1, 2):
        raise HTTPException(status_code=403, detail="Apenas gerentes e administradores podem acessar o log")
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
