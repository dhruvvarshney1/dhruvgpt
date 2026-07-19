"""Alembic async environment configuration.

Reads the database URL from ``app.config.settings`` instead of alembic.ini,
and uses the ``run_sync`` pattern for autogenerate against the async engine.
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.config import settings
from app.database import Base

# Import models so Base.metadata knows about them for autogenerate.
import app.models  # noqa: F401

# Alembic Config object — provides access to .ini values.
config = context.config

# Override the sqlalchemy.url from the ini with our settings value.
config.set_main_option("sqlalchemy.url", settings.database_url)

# Set up Python logging from the config file.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate support.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Configures the context with just a URL (no engine needed).
    Calls to ``context.execute()`` emit SQL to the script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    """Configure the context with the given connection and run migrations."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine and run migrations via ``run_sync``."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (async-compatible)."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
