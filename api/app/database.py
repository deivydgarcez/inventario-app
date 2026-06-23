from contextlib import contextmanager
from firebird.driver import connect, driver_config
from dotenv import load_dotenv
import os

load_dotenv()

FB_HOST = os.getenv("FB_HOST", "localhost")
FB_DATABASE = os.getenv("FB_DATABASE")
FB_USER = os.getenv("FB_USER", "SYSDBA")
FB_PASSWORD = os.getenv("FB_PASSWORD", "masterkey")
if not os.getenv("FB_PASSWORD") or FB_PASSWORD == "masterkey":
    print(
        "[INVEC AVISO] FB_PASSWORD nao configurado no .env — usando senha padrao 'masterkey'. "
        "Configure FB_PASSWORD no .env se o banco Firebird usar senha diferente."
    )


def _dsn() -> str:
    if FB_HOST and FB_HOST not in ("localhost", "127.0.0.1"):
        return f"{FB_HOST}:{FB_DATABASE}"
    return FB_DATABASE


@contextmanager
def get_connection():
    con = connect(
        database=_dsn(),
        user=FB_USER,
        password=FB_PASSWORD,
    )
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def fetchall_as_dict(cursor) -> list[dict]:
    columns = [d[0].lower() for d in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def fetchone_as_dict(cursor) -> dict | None:
    columns = [d[0].lower() for d in cursor.description]
    row = cursor.fetchone()
    return dict(zip(columns, row)) if row else None
