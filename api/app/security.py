import secrets
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from dotenv import load_dotenv
import os

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
