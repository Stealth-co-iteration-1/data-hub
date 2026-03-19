"""Async SQLite session factory.

Creates one AsyncEngine and provides session factories for the repository.
Use one engine per process, one session per request/operation.
"""
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def create_engine(database_url: str, echo: bool = False) -> AsyncEngine:
    """Create an async SQLite engine.

    Args:
        database_url: SQLite URL (e.g., "sqlite+aiosqlite:///./data.db" or "sqlite+aiosqlite:///:memory:")
        echo: If True, log all SQL statements

    Returns:
        AsyncEngine configured for SQLite
    """
    return create_async_engine(database_url, echo=echo)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create a session factory from an engine.

    Args:
        engine: AsyncEngine to bind sessions to

    Returns:
        Session factory that creates AsyncSession instances

    Note:
        expire_on_commit=False prevents MissingGreenlet errors when
        accessing attributes after commit in async context.
    """
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
