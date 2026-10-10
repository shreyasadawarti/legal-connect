"""Async SQLAlchemy engine, session factory and FastAPI dependency.

The whole application is written with `async def`, so this uses SQLAlchemy's
asyncio support over the `asyncmy` driver. That keeps every repository, service
and WebSocket handler `await`-ing exactly as before -- only the internals of the
repositories changed.

Engine creation is lazy so that importing the app never opens a connection, and
connection failures surface as a clear configuration error rather than a crash
when a route actually needs the database.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator, Optional

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings
from app.db.base import Base

# Importing the models registers every table on Base.metadata.
from app.db import models as _models  # noqa: F401

logger = logging.getLogger("legalconnect.database")

_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None

# Test seam. `session_scope` is used by scripts, seeding, WebSocket handlers and
# anything outside the request cycle, so it has to be redirectable to the test
# database. Without this the suite would silently write to the development
# database instead of `MYSQL_TEST_DATABASE`.
_session_factory_override: Optional[async_sessionmaker[AsyncSession]] = None


def set_session_factory_override(
    factory: Optional[async_sessionmaker[AsyncSession]],
) -> None:
    """Override the session factory used by `session_scope`. Tests only."""
    global _session_factory_override
    _session_factory_override = factory


def get_engine() -> AsyncEngine:
    """Return the process-wide async engine, creating it on first use."""
    global _engine, _session_factory
    if _engine is None:
        _engine = create_async_engine(
            settings.mysql_dsn,
            pool_pre_ping=True,
            pool_recycle=1800,
            pool_size=10,
            max_overflow=20,
            future=True,
            connect_args=settings.mysql_connect_args,
        )
        _session_factory = async_sessionmaker(
            _engine, expire_on_commit=False, class_=AsyncSession
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    if _session_factory_override is not None:
        return _session_factory_override
    get_engine()
    assert _session_factory is not None
    return _session_factory


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    """Standalone session for scripts, seeding and WebSocket handlers.

    Commits when the block finishes cleanly and rolls back if it raises, so
    callers get the same all-or-nothing guarantee as the request-scoped
    `get_session` dependency.
    """
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding a request-scoped session."""
    factory = get_session_factory()
    session = factory()
    try:
        yield session
    finally:
        await session.close()


async def ensure_database_exists() -> None:
    """Create the target schema if it is missing.

    Uses CREATE DATABASE IF NOT EXISTS, so it is safe to run against an existing
    database and never destroys data.
    """
    if settings.mysql_skip_database_creation:
        logger.info(
            "Skipping database creation for '%s' (MYSQL_SKIP_DATABASE_CREATION is set)",
            settings.mysql_database,
        )
        return
    server_engine = create_async_engine(
        settings.mysql_server_dsn,
        future=True,
        connect_args=settings.mysql_connect_args,
    )
    try:
        async with server_engine.connect() as conn:
            # Checked first rather than relying on CREATE DATABASE IF NOT EXISTS:
            # MySQL still raises a note-level warning when the schema is present,
            # which surfaces as noise on every script run and on every startup.
            exists = await conn.scalar(
                text("SELECT 1 FROM information_schema.schemata WHERE schema_name = :name"),
                {"name": settings.mysql_database},
            )
            if not exists:
                await conn.execute(
                    text(
                        f"CREATE DATABASE `{settings.mysql_database}` "
                        "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                    )
                )
                await conn.commit()
                logger.info("Created database '%s'", settings.mysql_database)
            else:
                logger.info("Database '%s' is present", settings.mysql_database)
    finally:
        await server_engine.dispose()


async def init_schema() -> None:
    """Create any missing tables.

    `create_all` only issues CREATE TABLE for tables that are absent; it never
    drops or alters what already exists. Real schema changes go through Alembic.
    """
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Schema verified: %d tables", len(Base.metadata.tables))


def upgrade_schema() -> None:
    """Bring the database up to head by running the Alembic migrations.

    Used by the maintenance scripts so a fresh checkout can be seeded without a
    separate manual `alembic upgrade head` step. Alembic is invoked through its
    programmatic API, and `run_async` is not used because the script already owns
    the event loop.
    """
    from alembic import command
    from alembic.config import Config

    backend_dir = Path(__file__).resolve().parents[2]
    ini_path = backend_dir / "alembic.ini"
    if not ini_path.exists():
        raise RuntimeError(f"Alembic config not found at {ini_path}")

    config = Config(str(ini_path))
    config.set_main_option("script_location", str(backend_dir / "alembic"))
    command.upgrade(config, "head")
    logger.info("Schema upgraded to head")


async def check_connection() -> bool:
    """Return True when MySQL answers a trivial query. Never raises."""
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError as exc:
        logger.warning("MySQL connectivity check failed: %s", exc)
        return False


async def dispose_engine() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        logger.info("MySQL connection pool disposed")
    _engine = None
    _session_factory = None