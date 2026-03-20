import asyncio
import os
from logging.config import fileConfig

from dotenv import load_dotenv
from sqlalchemy import pool

# Load .env file before reading DATABASE_URL
load_dotenv()
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# Import ORM models so Alembic can detect them
from src.adapters.driven.sqlite.models import Base

target_metadata = Base.metadata


# CRITICAL: Read DATABASE_URL from environment first
# This allows the same migrations to run against SQLite or PostgreSQL
# based on environment configuration, without modifying alembic.ini
def get_database_url() -> str:
    """Get database URL from environment or fall back to alembic.ini.

    Priority:
    1. DATABASE_URL environment variable
    2. sqlalchemy.url from alembic.ini

    Returns normalized URL with async driver.
    """
    env_url = os.environ.get("DATABASE_URL")
    if env_url:
        # Normalize URL for async driver
        if env_url.startswith("sqlite://") and "+aiosqlite" not in env_url:
            return env_url.replace("sqlite://", "sqlite+aiosqlite://", 1)
        if env_url.startswith("postgresql://") and "+asyncpg" not in env_url:
            return env_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if env_url.startswith("postgres://"):
            return env_url.replace("postgres://", "postgresql+asyncpg://", 1)
        return env_url

    # Fall back to alembic.ini
    return config.get_main_option("sqlalchemy.url")


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Override sqlalchemy.url in config section with environment URL
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_database_url()

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
