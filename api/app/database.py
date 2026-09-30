from contextlib import contextmanager
from firebird.driver import connect, driver_config
from firebird.driver.types import DatabaseError
from dotenv import load_dotenv
import os
import time

load_dotenv()

FB_HOST = os.getenv("FB_HOST", "localhost")
FB_DATABASE = os.getenv("FB_DATABASE")
FB_USER = os.getenv("FB_USER", "SYSDBA")
FB_PASSWORD = os.getenv("FB_PASSWORD", "masterkey")

_fb_client = os.getenv("FB_CLIENT_LIB")
if _fb_client and os.path.exists(_fb_client):
    driver_config.fb_client_library.value = _fb_client


def _dsn() -> str:
    if FB_HOST and FB_HOST not in ("localhost", "127.0.0.1"):
        return f"{FB_HOST}:{FB_DATABASE}"
    return FB_DATABASE


@contextmanager
def get_connection():
    con = None
    for attempt in range(3):
        try:
            con = connect(
                database=_dsn(),
                user=FB_USER,
                password=FB_PASSWORD,
            )
            break
        except DatabaseError as e:
            if "unavailable database" in str(e).lower() and attempt < 2:
                time.sleep(0.5 * (attempt + 1))
                continue
            raise
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
