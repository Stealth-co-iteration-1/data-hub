"""Integration test fixtures for SQLite adapter.

Provides in-memory SQLite database per test for isolation.
"""
import os

# Set required environment variables BEFORE any imports that trigger Settings
os.environ.setdefault("NANGO_WEBHOOK_SECRET", "test_secret_for_integration_tests")

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.adapters.driven.sqlite.models import Base
from src.adapters.driven.sqlite.session import create_engine, create_session_factory


@pytest.fixture
async def engine():
    """Create in-memory SQLite engine per test."""
    eng = create_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest.fixture
async def session_factory(engine) -> async_sessionmaker[AsyncSession]:
    """Create session factory from test engine."""
    return create_session_factory(engine)


@pytest.fixture
async def repository(session_factory):
    """Create repository instance for testing."""
    from src.adapters.driven.sqlite.repository import SQLiteDataRepository
    return SQLiteDataRepository(session_factory)
