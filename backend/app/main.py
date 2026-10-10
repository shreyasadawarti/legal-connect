import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.config import settings, validate_production_settings
from app.db.session import (
    check_connection,
    dispose_engine,
    ensure_database_exists,
    init_schema,
)
from app.middleware.rate_limit import limiter
from app.routers import (
    admin,
    ai,
    appointments,
    auth,
    complaints,
    conversations,
    documents,
    legal_categories,
    lawyers,
    messages,
    notifications,
    payments,
    reviews,
    users,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("legalconnect")


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_production_settings()
    logger.info("Starting up %s (env=%s)", settings.app_name, settings.app_env)
    try:
        await ensure_database_exists()
        if settings.auto_create_tables:
            await init_schema()
        logger.info(
            "MySQL ready at %s:%s/%s",
            settings.mysql_host,
            settings.mysql_port,
            settings.mysql_database,
        )
    except Exception:
        # Startup stays non-fatal: /api/v1/health reports the real state and
        # individual routes surface a clear 503 instead of the process dying.
        logger.exception("Database initialisation failed; continuing in degraded mode")
    yield
    await dispose_engine()
    logger.info("Shutdown complete")


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description=(
        "Legal Connect – AI-Powered Legal Assistance Platform API. "
        "All endpoints are under /api/v1. Interactive docs at /docs and /redoc."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def _rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests. Please try again later."},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(lawyers.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(appointments.router, prefix="/api/v1")
app.include_router(notifications.router, prefix="/api/v1")
app.include_router(complaints.router, prefix="/api/v1")
app.include_router(reviews.router, prefix="/api/v1")
app.include_router(payments.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")
app.include_router(legal_categories.router, prefix="/api/v1")
app.include_router(conversations.router, prefix="/api/v1")
app.include_router(messages.router, prefix="/api/v1")
app.include_router(ai.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")


@app.websocket("/api/v1/ws")
async def websocket_chat(websocket: WebSocket) -> None:
    from app.websocket.manager import websocket_endpoint

    await websocket_endpoint(websocket)


@app.get("/")
async def root():
    return {
        "app": settings.app_name,
        "docs": "/docs",
        "health": "/api/v1/health",
        "api_base": "/api/v1",
    }


@app.get("/api/v1/health")
async def health():
    db_ok = await check_connection()
    services = {"api": "ok"}
    services["mysql"] = "ok" if db_ok else "unavailable"
    overall = "ok" if db_ok else "degraded"
    return {"status": overall, "services": services}
