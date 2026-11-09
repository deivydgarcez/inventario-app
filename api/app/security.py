import secrets
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import bcrypt as _bcrypt_lib
from dotenv import load_dotenv
import os


# bcrypt direto (sem passlib): passlib 1.7.4 quebra com bcrypt >= 4.1
# ("password cannot be longer than 72 bytes") e travava o cadastro da senha mobile
# e a autorizacao do supervisor. Hashes $2b$ antigos continuam validos.
def _bcrypt_bytes(senha: str) -> bytes:
    return (senha or "").encode("utf-8")[:72]


def hash_senha(senha: str) -> str:
    return _bcrypt_lib.hashpw(_bcrypt_bytes(senha), _bcrypt_lib.gensalt()).decode("ascii")


def verificar_senhamobile(senha_digitada: str, valor_banco: str | None) -> bool:
    if not valor_banco:
        return False
    if valor_banco.startswith(("$2b$", "$2a$", "$2y$")):
        try:
            return _bcrypt_lib.checkpw(_bcrypt_bytes(senha_digitada), valor_banco.encode("ascii"))
        except (ValueError, TypeError):
            return False
    return valor_banco == senha_digitada

load_dotenv()

_raw_secret = os.getenv("JWT_SECRET", "")
if not _raw_secret or _raw_secret == "troque-esta-chave-secreta-em-producao":
    SECRET_KEY = secrets.token_hex(32)
    print(
        "[INVEC AVISO] JWT_SECRET nao configurado no .env — usando chave temporaria. "
        "Todos os usuarios precisarao fazer login novamente apos reiniciar o servidor. "
        "Configure JWT_SECRET no arquivo .env para evitar isso."
    )
else:
    SECRET_KEY = _raw_secret

ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", 2880))

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def create_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + timedelta(minutes=EXPIRE_MINUTES)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
