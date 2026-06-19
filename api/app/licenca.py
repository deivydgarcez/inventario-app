import os
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
    # expira_em vazio ou ausente = licenca permanente

    return payload
