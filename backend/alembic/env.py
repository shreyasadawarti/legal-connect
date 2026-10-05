"""Alembic environment for Legal Connect.

The database URL comes from the application settings rather than alembic.ini, so
credentials live in `.env` (gitignored) and are never committed to the repo.
Migrations run through the async `asyncmy` driver, which means `run_sync` wraps
the sync Alembic calls.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy.pool import NullPool

from app.config import settings
from app.db import models as _models  # noqa: F401  (importing registers the tables)
from app.db.base import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Autogenerate compares against the real model metadata.
target_metadata = Base.metadata


def _database_url() -> str:
    # `alembic.ini` has no sqlalchemy.url on purpose -- see module docstring.
    return config.get_main_option("sqlalchemy.url") or settings.mysql_dsn


def run_migrations_offline() -> None:
    """Emit SQL to stdout without connecting to the database."""
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def _do_run_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        render_as_batch=False,
    )

    with context.begin_transaction():
        context.run_migrations()


async def _run_async_migrations() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = _database_url()
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(_do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        # Normal CLI invocation: we own the loop.
        asyncio.run(_run_async_migrations())
        return

    # Called from inside a running loop -- `upgrade_schema()` in app.db.session
    # does this so the seeding scripts can migrate without a subprocess. Alembic
    # expects to drive its own loop, so run it on a separate thread instead of
    # nesting one.
    with ThreadPoolExecutor(max_workers=1) as pool:
        pool.submit(asyncio.run, _run_async_migrations()).result()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()