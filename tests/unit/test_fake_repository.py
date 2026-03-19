"""Tests for FakeDataRepository Protocol compliance."""
import pytest

from src.kernel.ports.fake_repository import FakeDataRepository
from src.kernel.ports.repository import DataRepository


class TestFakeDataRepositoryProtocol:
    """Verify FakeDataRepository implements DataRepository Protocol."""

    def test_fake_repository_implements_protocol(self):
        """FakeDataRepository is a valid DataRepository."""
        repo = FakeDataRepository()
        assert isinstance(repo, DataRepository)

    async def test_add_and_get_roundtrip(self):
        """Data written can be retrieved."""
        repo = FakeDataRepository()
        data = {"name": "Test", "value": 42}

        record_id = await repo.add("test_model", "conn_1", data)
        retrieved = await repo.get("test_model", record_id)

        assert retrieved == data

    async def test_get_wrong_model_returns_none(self):
        """Get with wrong model returns None."""
        repo = FakeDataRepository()
        data = {"name": "Test"}

        record_id = await repo.add("model_a", "conn_1", data)
        result = await repo.get("model_b", record_id)

        assert result is None

    async def test_idempotent_add_with_event_id(self):
        """Same event_id creates only one record."""
        repo = FakeDataRepository()
        data = {"event_id": "evt_123", "name": "Test"}

        id1 = await repo.add("test", "conn", data)
        id2 = await repo.add("test", "conn", data)

        # First exists, second was skipped
        assert await repo.get("test", id1) is not None
        assert await repo.get("test", id2) is None

    async def test_query_returns_matching_records(self):
        """Query returns records matching model."""
        repo = FakeDataRepository()
        await repo.add("contacts", "conn", {"name": "Alice"})
        await repo.add("contacts", "conn", {"name": "Bob"})
        await repo.add("products", "conn", {"name": "Widget"})

        results = await repo.query("contacts")

        assert len(results) == 2
        names = [r["name"] for r in results]
        assert "Alice" in names
        assert "Bob" in names

    async def test_query_with_filters(self):
        """Query filters by column value."""
        repo = FakeDataRepository()
        await repo.add("contacts", "conn", {"name": "Alice", "city": "NYC"})
        await repo.add("contacts", "conn", {"name": "Bob", "city": "LA"})

        results = await repo.query("contacts", filters={"city": "NYC"})

        assert len(results) == 1
        assert results[0]["name"] == "Alice"

    async def test_query_respects_limit(self):
        """Query returns at most limit records."""
        repo = FakeDataRepository()
        for i in range(10):
            await repo.add("items", "conn", {"index": i})

        results = await repo.query("items", limit=3)

        assert len(results) == 3
