from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, depositos, produtos, inventario, operadores, sessao, dispositivos
from app.migrations import run_migrations
from app.licenca import validar_licenca


@asynccontextmanager
async def lifespan(app: FastAPI):
    validar_licenca()
    run_migrations()
    yield


app = FastAPI(
    title="Inventário API",
    description="API para contagem de inventário integrada ao Firebird (miautomec)",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://127.0.0.1"],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(depositos.router)
app.include_router(produtos.router)
app.include_router(inventario.router)
app.include_router(operadores.router)
app.include_router(sessao.router)
app.include_router(dispositivos.router)


@app.get("/", tags=["Health"])
def health():
    return {"status": "ok"}


@app.get("/ping", tags=["Health"])
def ping():
    return {"status": "ok"}


@app.get("/db-ping", tags=["Health"])
def db_ping():
    from app.database import get_connection
    try:
        with get_connection() as con:
            cur = con.cursor()
            cur.execute("SELECT 1 FROM RDB$DATABASE")
            cur.fetchone()
        return {"status": "ok"}
    except Exception:
        return {"status": "error"}
