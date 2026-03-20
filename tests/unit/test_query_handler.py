"""Unit tests for QueryHandler."""
import pytest

from src.kernel.handlers import QueryHandler
from src.kernel.queries import MAX_QUERY_LIMIT, QueryData

from .fakes import FakeDataRepository


class TestQueryHandler:
    """Tests for QueryHandler."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.repository = FakeDataRepository()
        self.handler = QueryHandler(repository=self.repository)

    @pytest.mark.asyncio
    async def test_handle_calls_repository_query(self) -> None:
        """Handler should call repository.query with correct params."""
        query = QueryData(
            model="contacts",
            filters={"connection_id": "abc"},
            limit=50,
        )

        await self.handler.handle(query)

        assert len(self.repository.query_calls) == 1
        model, filters, limit = self.repository.query_calls[0]
        assert model == "contacts"
        assert filters == {"connection_id": "abc"}
        assert limit == 50

    @pytest.mark.asyncio
    async def test_handle_enforces_max_limit(self) -> None:
        """Handler should cap limit at MAX_QUERY_LIMIT."""
        query = QueryData(
            model="contacts",
            limit=5000,  # Way over MAX_QUERY_LIMIT
        )

        await self.handler.handle(query)

        _, _, limit = self.repository.query_calls[0]
        assert limit == MAX_QUERY_LIMIT
        assert limit == 1000

    @pytest.mark.asyncio
    async def test_handle_returns_results(self) -> None:
        """Handler should return results from repository."""
        # Pre-populate repository
        await self.repository.add("contacts", "conn1", {"name": "Alice"})
        await self.repository.add("contacts", "conn2", {"name": "Bob"})

        query = QueryData(model="contacts")
        results = await self.handler.handle(query)

        assert len(results) == 2
        names = [r["name"] for r in results]
        assert "Alice" in names
        assert "Bob" in names

    @pytest.mark.asyncio
    async def test_handle_with_no_filters(self) -> None:
        """Handler should pass None filters correctly."""
        query = QueryData(model="contacts")

        await self.handler.handle(query)

        _, filters, _ = self.repository.query_calls[0]
        assert filters is None
