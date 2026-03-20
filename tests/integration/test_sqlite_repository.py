"""Integration tests for SQLiteDataRepository.

Tests repository contract against real SQLite database.
"""
import pytest

from src.adapters.driven.sqlite.repository import SQLiteDataRepository


class TestSQLiteDataRepository:
    """Tests for SQLiteDataRepository implementation."""

    async def test_add_and_get_roundtrip(self, repository):
        """Data written can be retrieved with same content (PERS-01, VERF-01)."""
        data = {"name": "Alice", "email": "alice@example.com"}

        record_id = await repository.add(
            model="contacts",
            connection_id="nango_hubspot_123",
            data=data,
        )

        retrieved = await repository.get("contacts", record_id)
        assert retrieved == data

    async def test_get_nonexistent_returns_none(self, repository):
        """Get with nonexistent ID returns None."""
        result = await repository.get("contacts", "nonexistent-id")
        assert result is None

    async def test_get_wrong_model_returns_none(self, repository):
        """Get with correct ID but wrong model returns None."""
        data = {"name": "Bob"}
        record_id = await repository.add(model="contacts", connection_id="src", data=data)

        result = await repository.get("products", record_id)
        assert result is None

    async def test_idempotent_add_same_event_id(self, repository):
        """Same event_id inserted twice creates only one record (PERS-04)."""
        data = {"event_id": "evt_abc123", "name": "Charlie"}

        # First insert
        id1 = await repository.add(model="contacts", connection_id="src", data=data)

        # Second insert with same event_id - should not raise, should return new id
        id2 = await repository.add(model="contacts", connection_id="src", data=data)

        # But only one record should exist - first one wins
        first = await repository.get("contacts", id1)
        assert first is not None

        # Second ID should not retrieve the same data (duplicate was skipped)
        # The second add returns a new ID but doesn't actually insert
        second = await repository.get("contacts", id2)
        # Second record was not inserted due to idempotency
        assert second is None

    async def test_add_without_event_id(self, repository):
        """Add without event_id works (no idempotency check)."""
        data = {"name": "David"}

        id1 = await repository.add(model="contacts", connection_id="src", data=data)
        id2 = await repository.add(model="contacts", connection_id="src", data=data)

        # Both should be inserted (no event_id = no idempotency)
        assert id1 != id2
        assert await repository.get("contacts", id1) == data
        assert await repository.get("contacts", id2) == data


async def test_query_returns_all_records_for_model(repository: SQLiteDataRepository) -> None:
    """Query without filters returns all records for model."""
    await repository.add("contacts", "conn1", {"name": "Alice"})
    await repository.add("contacts", "conn2", {"name": "Bob"})
    await repository.add("orders", "conn1", {"amount": 100})  # Different model

    results = await repository.query("contacts")

    assert len(results) == 2
    names = [r["name"] for r in results]
    assert "Alice" in names
    assert "Bob" in names


async def test_query_with_connection_id_filter(repository: SQLiteDataRepository) -> None:
    """Query with connection_id filter returns only matching records."""
    await repository.add("contacts", "conn1", {"name": "Alice"})
    await repository.add("contacts", "conn2", {"name": "Bob"})
    await repository.add("contacts", "conn1", {"name": "Carol"})

    results = await repository.query("contacts", filters={"connection_id": "conn1"})

    assert len(results) == 2
    names = [r["name"] for r in results]
    assert "Alice" in names
    assert "Carol" in names
    assert "Bob" not in names


async def test_query_respects_limit(repository: SQLiteDataRepository) -> None:
    """Query respects limit parameter."""
    for i in range(10):
        await repository.add("contacts", f"conn{i}", {"name": f"User{i}"})

    results = await repository.query("contacts", limit=5)

    assert len(results) == 5


async def test_query_returns_empty_when_no_matches(repository: SQLiteDataRepository) -> None:
    """Query returns empty list when no records match."""
    await repository.add("contacts", "conn1", {"name": "Alice"})

    results = await repository.query("contacts", filters={"connection_id": "nonexistent"})

    assert results == []


async def test_query_returns_system_fields(repository: SQLiteDataRepository) -> None:
    """Query returns system fields (id, connection_id, model, created_at) alongside data.

    Per CONTEXT.md locked decision: "Include system fields in results"
    """
    await repository.add("contacts", "conn1", {"name": "Alice", "email": "alice@example.com"})

    results = await repository.query("contacts")

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


async def test_query_ignores_non_connection_id_filters(repository: SQLiteDataRepository) -> None:
    """Query ignores filters other than connection_id (no JSON field filtering in v1).

    Per CONTEXT.md locked decision: "no filtering on raw JSON data fields"
    """
    await repository.add("contacts", "conn1", {"name": "Alice", "status": "active"})
    await repository.add("contacts", "conn2", {"name": "Bob", "status": "inactive"})

    # Try to filter on 'status' (a JSON field) - should be ignored
    results = await repository.query("contacts", filters={"status": "active"})

    # All records returned because JSON field filtering is not supported
    assert len(results) == 2
