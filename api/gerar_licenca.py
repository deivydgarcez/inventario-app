"""
Gerador de licencas Invec — Pontual Tecnologia
USO: python gerar_licenca.py
ATENCAO: mantenha licenca_privada.pem em local seguro e nunca distribua.
"""
import sys
import os
from datetime import date, timedelta
from jose import jwt

CHAVE_PRIVADA_PATH = os.path.join(os.path.dirname(__file__), "licenca_privada.pem")


def main():
    if not os.path.exists(CHAVE_PRIVADA_PATH):
        print(f"ERRO: Chave privada nao encontrada em {CHAVE_PRIVADA_PATH}")
        sys.exit(1)

    with open(CHAVE_PRIVADA_PATH, "r") as f:
        chave_privada = f.read()

    print("=" * 55)
    print("  GERADOR DE LICENCAS INVEC — Pontual Tecnologia")
    print("=" * 55)

    cliente    = input("Nome do cliente      : ").strip()
    cnpj       = input("CNPJ                 : ").strip()
    meses_str  = input("Validade (meses, Enter = sem validade): ").strip()
    machine_id = input("ID da maquina (Enter = sem vinculo)   : ").strip().upper()

    hoje = date.today()
    expiracao = (hoje + timedelta(days=30 * int(meses_str))).isoformat() if meses_str else ""

    payload = {
        "produto"    : "Invec",
        "cliente"    : cliente,
        "cnpj"       : cnpj,
        "emitida_em" : hoje.isoformat(),
        "expira_em"  : expiracao,
    }
    if machine_id:
        payload["machine_id"] = machine_id

    token = jwt.encode(payload, chave_privada, algorithm="RS256")

    print()
    print("=" * 55)
    print(f"  Cliente    : {cliente}")
    print(f"  CNPJ       : {cnpj}")
    print(f"  Emitida    : {hoje.isoformat()}")
    print(f"  Expira     : {expiracao if expiracao else 'Sem validade'}")
    print(f"  Maquina    : {machine_id if machine_id else 'Sem vinculo (reutilizavel)'}")
    print("=" * 55)
    print()
    print("Adicione a linha abaixo no arquivo .env do cliente:")
    print()
    print(f"LICENSE_KEY={token}")
    print()


if __name__ == "__main__":
    main()
