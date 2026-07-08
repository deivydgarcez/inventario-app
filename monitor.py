"""
Monitor de banco Firebird — Invec
Atualiza a cada 4s. Pressione Ctrl+C para sair.
"""
import os
import time
from datetime import datetime
from firebird.driver import connect

DB = r"C:\Administracao\DB\MIAUTOMEC.FDB"
USER = "SYSDBA"
PASSWORD = "masterkey"
INTERVALO = 4


def hdr(titulo):
    print(f"\n{'='*62}")
    print(f"  {titulo}")
    print(f"{'='*62}")


def tabela(cur, sql, larg, params=()):
    cur.execute(sql, params)
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    print("  ".join(c.ljust(larg[i]) for i, c in enumerate(cols)))
    print("  ".join("-" * larg[i] for i in range(len(cols))))
    for row in rows:
        print("  ".join(str(v if v is not None else "").ljust(larg[i]) for i, v in enumerate(row)))
    if not rows:
        print("  (sem registros)")
    return rows


def monitorar():
    ciclo = 0
    while True:
        ciclo += 1
        ts = datetime.now().strftime("%H:%M:%S")
        os.system("cls")
        print(f"Monitor Invec  {ts}  (ciclo {ciclo})   Ctrl+C para sair\n")

        try:
            con = connect(database=DB, user=USER, password=PASSWORD)
            cur = con.cursor()

            # 1. Sessões abertas
            hdr("SESSOES ABERTAS (INVENTARIO_SESSAO)")
            rows_sessao = tabela(cur, """
                SELECT SESSION_ID, CDDEPOSITO, USUARIO, OPERADOR, STATUS, INICIO
                FROM INVENTARIO_SESSAO
                WHERE STATUS = 'ABERTA'
                ORDER BY INICIO DESC ROWS 10
            """, [36, 10, 12, 12, 10, 22])

            # 2. Itens bipados na sessão atual (INVENTARIO_TEMP)
            hdr("INVENTARIO_TEMP — scans da sessao")
            tabela(cur, """
                SELECT T.CDPRODUTO,
                       SUBSTRING(P.PRODUTO FROM 1 FOR 35) AS DESCRICAO,
                       T.QTDE, T.QTDEATUAL_SNAP, T.CDDEPOSITO, T.SESSION_ID
                FROM INVENTARIO_TEMP T
                LEFT JOIN PRODUTO P ON P.CDPRODUTO = T.CDPRODUTO
                ORDER BY T.CDPRODUTO ROWS 20
            """, [10, 35, 8, 14, 10, 36])

            # 3. MOVIMENTO — estoque atual dos produtos que estão na sessão
            hdr("MOVIMENTO — estoque atual (produtos na sessao)")
            tabela(cur, """
                SELECT M.CDPRODUTO, M.CDDEPOSITO, M.QTDEATUAL, M.DTALTER
                FROM MOVIMENTO M
                WHERE M.CDPRODUTO IN (
                    SELECT DISTINCT CDPRODUTO FROM INVENTARIO_TEMP
                )
                ORDER BY M.CDPRODUTO ROWS 20
            """, [10, 10, 14, 22])

            # 4. INVENTARIO — ultima consolidação gravada
            hdr("INVENTARIO — ultima consolidacao (top 10)")
            tabela(cur, """
                SELECT I.CDPRODUTO,
                       SUBSTRING(P.PRODUTO FROM 1 FOR 30) AS DESCRICAO,
                       I.CDDEPOSITO, I.QTDE, I.DATA, I.OPERADOR
                FROM INVENTARIO I
                LEFT JOIN PRODUTO P ON P.CDPRODUTO = I.CDPRODUTO
                ORDER BY I.DATA DESC ROWS 10
            """, [10, 30, 10, 8, 22, 12])

            # 5. MOV_PRODUTO — últimas 8 movimentações (qualquer tipo)
            hdr("MOV_PRODUTO — ultimas 8 movimentacoes")
            tabela(cur, """
                SELECT M.CDPRODUTO, M.CDDEPOSITO, M.TIPOMOVIMENTO,
                       M.QTENTRADA, M.QTSAIDA, M.QTDANTERIOR,
                       SUBSTRING(COALESCE(M.HISTORICO,'') FROM 1 FOR 25) AS HISTORICO,
                       M.DTALTER
                FROM MOV_PRODUTO M
                ORDER BY M.DTALTER DESC ROWS 8
            """, [10, 10, 14, 10, 10, 12, 27, 22])

            con.close()

        except Exception as e:
            print(f"\n[ERRO] {e}")

        time.sleep(INTERVALO)


if __name__ == "__main__":
    try:
        monitorar()
    except KeyboardInterrupt:
        print("\n\nMonitor encerrado.")
