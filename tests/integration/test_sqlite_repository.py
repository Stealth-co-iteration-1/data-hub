"""Integration tests for SQLiteDataRepository.

Tests repository contract against real SQLite database.
"""
import pytest


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
