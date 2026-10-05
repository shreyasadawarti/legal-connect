"""Test fixtures backed by a real MySQL database.

There is no in-memory fake any more. Each test runs against
`legal_connect_test`, whose tables are dropped and recreated before the test so
every case starts from a known-empty schema. That is stricter than the old
fake: SQL type coercion, unique constraints, foreign keys, CASCADE deletes and
transaction rollback are all genuinely exercised, which an in-memory
dictionary never could.

`legal_connect` (the development database) is never touched -- the engine below
is built from `mysql_test_database`, and `mysql_database` is asserted to differ.
"""

import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.db.base import Base
from app.db.models import *  # noqa: F401,F403  (registers every table)
from app.db import models as _models  # noqa: F401
from app.dependencies import require_db
from app.db.session import set_session_factory_override
from app.main import app

TEST_DATABASE = os.getenv("MYSQL_TEST_DATABASE", "legal_connect_test")


def _test_url() -> str:
    return (
        f"mysql+asyncmy://{settings.mysql_user}:{settings.mysql_password}"
        f"@{settings.mysql_host}:{settings.mysql_port}/{TEST_DATABASE}"
        f"?charset={settings.mysql_charset}"
    )


def _server_url() -> str:
    return (
        f"mysql+asyncmy://{settings.mysql_user}:{settings.mysql_password}"
        f"@{settings.mysql_host}:{settings.mysql_port}/?charset={settings.mysql_charset}"
    )


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


# pytest-asyncio runs each test in its own event loop (see pytest.ini's
# `asyncio_default_fixture_loop_scope = function`), so the engine must be
# function-scoped too -- a session-scoped engine would be bound to a closed
# loop. The one-off CREATE DATABASE is memoised so it only happens once.
_test_db_ready = False


@pytest_asyncio.fixture
async def _engine():
    global _test_db_ready

    if TEST_DATABASE == settings.mysql_database:
        raise RuntimeError(
            "Refusing to run tests against the development database. "
            "Set MYSQL_TEST_DATABASE to something other than "
            f"{settings.mysql_database}."
        )

    if not _test_db_ready:
        from sqlalchemy import text

        admin_engine = create_async_engine(_server_url(), future=True)
        async with admin_engine.connect() as conn:
            await conn.execute(
                text(
                    f"CREATE DATABASE IF NOT EXISTS `{TEST_DATABASE}` "
                    "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
            )
            await conn.commit()
        await admin_engine.dispose()
        _test_db_ready = True

    engine = create_async_engine(_test_url(), pool_pre_ping=True, future=True)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    set_session_factory_override(factory)
    try:
        yield engine
    finally:
        set_session_factory_override(None)
        await engine.dispose()


@pytest_asyncio.fixture
async def db(_engine) -> AsyncSession:
    """A session on a freshly rebuilt schema."""
    async with _engine.begin() as conn:
        # Drop order is handled by SQLAlchemy; CASCADE clears the children.
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(_engine, expire_on_commit=False, class_=AsyncSession)
    session = factory()
    try:
        yield session
    finally:
        await session.close()


@pytest_asyncio.fixture
async def client(db):
    """An HTTP client whose routes use the real MySQL test database."""

    async def _override():
        # Mirrors the real `require_db`: commit when the handler succeeds and roll
        # back when it raises, so a 4xx/5xx response leaves no partial rows behind.
        # Reusing the test session keeps assertions able to see the request's writes.
        try:
            yield db
        except Exception:
            await db.rollback()
            raise
        else:
            await db.commit()

    app.dependency_overrides[require_db] = _override
    # Test helpers seed/assert directly, so they need the same session the routes
    # use without having to introspect the override (which may be a generator).
    app.state.test_db_session = db

    # Disable slowapi rate limiting so tests are not throttled by cumulative
    # per-IP counters across a shared app instance.
    limiter = app.state.limiter
    was_enabled = getattr(limiter, "enabled", True)
    try:
        limiter.enabled = False
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()
        app.state.test_db_session = None
        try:
            limiter.enabled = was_enabled
        except Exception:  # noqa: BLE001
            pass