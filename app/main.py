"""
CortexFlow FastAPI application entrypoint.

Wires CORS, logging, exception handlers, lifespan (bucket + collection init),
health/readiness, and the v1 router tree.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from app.api.v1.artifacts import router as artifacts_router
from app.api.v1.auth import router as auth_router
from app.api.v1.chat import router as chat_router
from app.api.v1.documents import router as documents_router
from app.api.v1.memory import router as memory_router
from app.api.v1.notebooks import router as notebooks_router
from app.api.v1.search import router as search_router
from app.api.v1.workspaces import router as workspaces_router
from app.core.config import settings
from app.core.exceptions import install_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.redis import close_redis
from app.services.storage import storage


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[no-untyped-def]
    configure_logging()
    log = get_logger("app.main")
    log.info("Starting {} ({})", settings.app_name, settings.env)

    # Best-effort infra init (dev convenience; prod does this in migrations)
    try:
        storage.ensure_bucket()
    except Exception as exc:
        log.warning("MinIO init skipped: {}", exc)
    try:
        from app.services.vector import vector

        await vector.ensure_collection()
    except Exception as exc:
        log.warning("Qdrant init skipped: {}", exc)

    yield
    await close_redis()
    log.info("Shutdown complete.")


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="Production-grade AI research platform.",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
install_exception_handlers(app)

# Prometheus metrics at /metrics
app.mount("/metrics", make_asgi_app())

# ── Routers ──────────────────────────────────────────────────
PREFIX = settings.api_prefix
app.include_router(auth_router, prefix=PREFIX)
app.include_router(workspaces_router, prefix=PREFIX)
app.include_router(notebooks_router, prefix=PREFIX)
app.include_router(documents_router, prefix=PREFIX)
app.include_router(chat_router, prefix=PREFIX)
app.include_router(search_router, prefix=PREFIX)
app.include_router(memory_router, prefix=PREFIX)
app.include_router(artifacts_router, prefix=PREFIX)


@app.get("/health", tags=["meta"])
async def health():
    return {"status": "ok", "version": settings.version, "env": settings.env}


@app.get("/ready", tags=["meta"])
async def ready():
    return {"status": "ready"}
