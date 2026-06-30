import os
import subprocess
from datetime import date
from jose import jwt, JWTError

# Chave pública RSA — usada apenas para VERIFICAR licenças.
# A chave privada correspondente está exclusivamente com a Pontual Tecnologia.
_CHAVE_PUBLICA = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA3lzXDIGB9SAYxnM69fU/
nVqlxyMFr+rzTg+NrTbcFco3Ow3Obr291Q06r7s+xJ8Dud5obrZXzs5Sfs9jcHfL
xQZHqX4YpbkWL66vk/tTjXYAZWC2jBtYAra0pEOI7XeraxMq8NSF/BJnSI7/E5i3
efBhuS018iJrF2bUkN1zXrYM5Gq/p8yrEGgNROqwKiZQlGnhQm8aK5X1YQglAEog
CJD1twqA3KWBSEx3ojKFgTRoeQGEw81SdfmX7K6NPbxIL3Md0cKPPNpsbJ9VS1Uy
XTZWEFt/FgSNMAzgecfXZdRtJsob5vA742EXC/31xgxB9O7t+FXquodUGxGmBU2j
OQIDAQAB
-----END PUBLIC KEY-----"""

_UUID_INVALIDOS = {
    "", "TO BE FILLED BY O.E.M.", "NOT APPLICABLE", "NONE", "N/A",
    "00000000-0000-0000-0000-000000000000",
    "FFFFFFFF-FFFF-FFFF-FFFF-FFFFFFFFFFFF",
}


def get_machine_id() -> str:
    """UUID do BIOS da máquina (Windows 10/11). Vazio se indisponível ou inválido."""
    # PowerShell CIM — funciona no Windows 10 e 11 (wmic foi removido no Win11)
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
             "-Command", "(Get-CimInstance -ClassName Win32_ComputerSystemProduct).UUID"],
            capture_output=True, text=True, timeout=10,
        )
        uid = r.stdout.strip().upper()
        if uid and uid not in _UUID_INVALIDOS and len(uid) >= 32:
            return uid
    except Exception:
        pass
    # wmic — fallback para Windows 10 sem PowerShell CIM configurado
    try:
        r = subprocess.run(
            ["wmic", "csproduct", "get", "uuid"],
            capture_output=True, text=True, timeout=5,
        )
        for linha in r.stdout.splitlines():
            uid = linha.strip().upper()
            if uid and uid != "UUID" and uid not in _UUID_INVALIDOS and len(uid) >= 32:
                return uid
    except Exception:
        pass
    return ""


def validar_licenca() -> dict:
    """
    Lê LICENSE_KEY do .env e valida contra a chave pública embutida.
    Levanta RuntimeError com mensagem clara se a licença for inválida ou ausente.
    Retorna o payload da licença se tudo estiver correto.
    """
    chave = os.getenv("LICENSE_KEY", "").strip()

    if not chave:
        raise RuntimeError(
            "Licenca nao encontrada.\n"
            "Configure LICENSE_KEY no arquivo .env.\n"
            "Entre em contato com a Pontual Tecnologia para obter sua licenca."
        )

    try:
        payload = jwt.decode(chave, _CHAVE_PUBLICA, algorithms=["RS256"])
    except JWTError as e:
        raise RuntimeError(
            f"Licenca invalida ou corrompida ({e}).\n"
            "Entre em contato com a Pontual Tecnologia."
        )

    expira_em = payload.get("expira_em", "")
    if expira_em and date.fromisoformat(expira_em) < date.today():
        raise RuntimeError(
            f"Licenca expirada em {expira_em}.\n"
            "Renove sua licenca com a Pontual Tecnologia."
        )

    # Vinculação por máquina: se a licença tem machine_id, verifica que é esta máquina
    machine_id_licenca = payload.get("machine_id", "").strip().upper()
    if machine_id_licenca:
        machine_id_atual = get_machine_id()
        if not machine_id_atual:
            raise RuntimeError(
                "Nao foi possivel verificar o identificador desta maquina.\n"
                "Esta licenca esta vinculada a um equipamento especifico.\n"
                "Entre em contato com a Pontual Tecnologia."
            )
        if machine_id_atual != machine_id_licenca:
            raise RuntimeError(
                "Esta licenca pertence a outro equipamento e nao pode ser reutilizada.\n"
                f"Maquina desta instalacao : {machine_id_atual}\n"
                f"Maquina da licenca       : {machine_id_licenca}\n"
                "Solicite uma nova licenca para este equipamento."
            )

    return payload
