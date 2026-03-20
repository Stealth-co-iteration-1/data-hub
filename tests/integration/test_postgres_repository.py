"""Integration tests for PostgresDataRepository.

Tests repository contract against PostgreSQL database.
Skipped if PostgreSQL is not available (CI will run with real PostgreSQL).
"""
import os

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.adapters.driven.postgresql.repository import PostgresDataRepository
from src.adapters.driven.sqlite.models import Base
from src.kernel.ports.repository import DataRepository


# Skip all tests if no PostgreSQL URL provided
POSTGRES_URL = os.environ.get("TEST_POSTGRES_URL")
pytestmark = pytest.mark.skipif(
    POSTGRES_URL is None,
    reason="TEST_POSTGRES_URL not set - PostgreSQL tests skipped",
)


@pytest.fixture
async def pg_engine():
    """Create PostgreSQL engine for testing."""
    engine = create_async_engine(POSTGRES_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    # Clean up tables after test
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def pg_session_factory(pg_engine) -> async_sessionmaker[AsyncSession]:
    """Create session factory from test engine."""
    return async_sessionmaker(pg_engine, expire_on_commit=False)


@pytest.fixture
async def pg_repository(pg_session_factory, pg_engine) -> PostgresDataRepository:
    """Create PostgresDataRepository instance for testing."""
    return PostgresDataRepository(pg_session_factory, pg_engine)


class TestPostgresDataRepositoryProtocol:
    """Verify PostgresDataRepository implements DataRepository Protocol."""

    async def test_implements_protocol(self, pg_repository):
        """PostgresDataRepository is a valid DataRepository."""
        assert isinstance(pg_repository, DataRepository)


class TestPostgresDataRepository:
    """Tests for PostgresDataRepository implementation."""

    async def test_add_and_get_roundtrip(self, pg_repository):
        """Data written can be retrieved with same content."""
        data = {"name": "Alice", "email": "alice@example.com"}

        record_id = await pg_repository.add(
            model="contacts",
            connection_id="nango_hubspot_123",
            data=data,
        )

        retrieved = await pg_repository.get("contacts", record_id)
        assert retrieved == data

    async def test_get_nonexistent_returns_none(self, pg_repository):
        """Get with nonexistent ID returns None."""
        result = await pg_repository.get("contacts", "nonexistent-id")
        assert result is None

    async def test_get_wrong_model_returns_none(self, pg_repository):
        """Get with correct ID but wrong model returns None."""
        data = {"name": "Bob"}
        record_id = await pg_repository.add(model="contacts", connection_id="src", data=data)

        result = await pg_repository.get("products", record_id)
        assert result is None

    async def test_idempotent_add_same_event_id(self, pg_repository):
        """Same event_id inserted twice creates only one record (PGRS-03)."""
        data = {"event_id": "evt_abc123", "name": "Charlie"}

        # First insert
        id1 = await pg_repository.add(model="contacts", connection_id="src", data=data)

        # Second insert with same event_id - should not raise, should return new id
        id2 = await pg_repository.add(model="contacts", connection_id="src", data=data)

        # But only one record should exist - first one wins
        first = await pg_repository.get("contacts", id1)
        assert first is not None

        # Second ID should not retrieve the same data (duplicate was skipped)
        second = await pg_repository.get("contacts", id2)
        assert second is None

    async def test_add_without_event_id(self, pg_repository):
        """Add without event_id works (no idempotency check)."""
        data = {"name": "David"}

        id1 = await pg_repository.add(model="contacts", connection_id="src", data=data)
        id2 = await pg_repository.add(model="contacts", connection_id="src", data=data)

        # Both should be inserted (no event_id = no idempotency)
        assert id1 != id2
        assert await pg_repository.get("contacts", id1) == data
        assert await pg_repository.get("contacts", id2) == data

    async def test_engine_property_accessible(self, pg_repository):
        """Engine property is accessible for health checks."""
        engine = pg_repository.engine
        assert engine is not None
        # Verify it's a working engine
        async with engine.connect() as conn:
            from sqlalchemy import text
            result = await conn.execute(text("SELECT 1"))
            assert result.scalar() == 1


async def test_query_returns_all_records_for_model(pg_repository: PostgresDataRepository) -> None:
    """Query without filters returns all records for model."""
    await pg_repository.add("contacts", "conn1", {"name": "Alice"})
    await pg_repository.add("contacts", "conn2", {"name": "Bob"})
    await pg_repository.add("orders", "conn1", {"amount": 100})  # Different model

    results = await pg_repository.query("contacts")

    assert len(results) == 2
    names = [r["name"] for r in results]
    assert "Alice" in names
    assert "Bob" in names


async def test_query_with_connection_id_filter(pg_repository: PostgresDataRepository) -> None:
    """Query with connection_id filter returns only matching records."""
    await pg_repository.add("contacts", "conn1", {"name": "Alice"})
    await pg_repository.add("contacts", "conn2", {"name": "Bob"})
    await pg_repository.add("contacts", "conn1", {"name": "Carol"})

    results = await pg_repository.query("contacts", filters={"connection_id": "conn1"})

    assert len(results) == 2
    names = [r["name"] for r in results]
    assert "Alice" in names
    assert "Carol" in names
    assert "Bob" not in names


async def test_query_respects_limit(pg_repository: PostgresDataRepository) -> None:
    """Query respects limit parameter."""
    for i in range(10):
        await pg_repository.add("contacts", f"conn{i}", {"name": f"User{i}"})

    results = await pg_repository.query("contacts", limit=5)

    assert len(results) == 5


async def test_query_returns_empty_when_no_matches(pg_repository: PostgresDataRepository) -> None:
    """Query returns empty list when no records match."""
    await pg_repository.add("contacts", "conn1", {"name": "Alice"})

    results = await pg_repository.query("contacts", filters={"connection_id": "nonexistent"})

    assert results == []


async def test_query_returns_system_fields(pg_repository: PostgresDataRepository) -> None:
    """Query returns system fields (id, connection_id, model, created_at) alongside data.

    Per CONTEXT.md locked decision: "Include system fields in results"
    """
    await pg_repository.add("contacts", "conn1", {"name": "Alice", "email": "alice@example.com"})

    results = await pg_repository.query("contacts")

    assert len(results) == 1
    record = results[0]
    # System fields must be present
    assert "id" in record
    assert "connection_id" in record
    assert record["connection_id"] == "conn1"
    assert "model" in record
    assert record["model"] == "contacts"
    assert "created_at" in record
    # Data payload fields also present
    assert record["name"] == "Alice"
    assert record["email"] == "alice@example.com"


async def test_query_ignores_non_connection_id_filters(pg_repository: PostgresDataRepository) -> None:
    """Query ignores filters other than connection_id (no JSON field filtering in v1).

    Per CONTEXT.md locked decision: "no filtering on raw JSON data fields"
    """
    await pg_repository.add("contacts", "conn1", {"name": "Alice", "status": "active"})
    await pg_repository.add("contacts", "conn2", {"name": "Bob", "status": "inactive"})

    # Try to filter on 'status' (a JSON field) - should be ignored
    results = await pg_repository.query("contacts", filters={"status": "active"})

    # All records returned because JSON field filtering is not supported
    assert len(results) == 2
