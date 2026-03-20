"""Integration tests for POST /query/{model} endpoint."""
import pytest
from httpx import ASGITransport, AsyncClient

from src.adapters.driving.fastapi.app import app
from src.adapters.driving.fastapi.dependencies import get_query_handler
from src.kernel.handlers.query_handler import QueryHandler
from tests.unit.fakes import FakeDataRepository


def make_fake_repository() -> FakeDataRepository:
    """Create a fresh FakeDataRepository for test isolation."""
    return FakeDataRepository()


@pytest.fixture
async def repo_and_client():
    """AsyncClient with query handler overridden to use FakeDataRepository."""
    fake_repo = make_fake_repository()

    async def fake_query_handler():
        return QueryHandler(repository=fake_repo)

    app.dependency_overrides[get_query_handler] = fake_query_handler

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield fake_repo, c

    app.dependency_overrides.clear()


class TestQueryEndpoint:
    """Tests for /query/{model} endpoint."""

    async def test_query_returns_records_for_model_with_system_fields(
        self, repo_and_client
    ) -> None:
        """POST /query/{model} returns records with system fields."""
        repo, client = repo_and_client

        await repo.add("test_contacts", "conn1", {"name": "Alice"})
        await repo.add("test_contacts", "conn2", {"name": "Bob"})

        response = await client.post("/query/test_contacts", json={})

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "count" in data
        assert "limit" in data
        assert "has_more" in data
        # No offset in response (deferred)
        assert "offset" not in data
        assert data["count"] == 2
        # Verify system fields in results
        for record in data["data"]:
            assert "id" in record
            assert "connection_id" in record
            assert "model" in record
            assert "created_at" in record

    async def test_query_with_connection_id_filter(self, repo_and_client) -> None:
        """Query with connection_id filter returns only matching records."""
        repo, client = repo_and_client

        await repo.add("filter_contacts", "conn1", {"name": "Alice"})
        await repo.add("filter_contacts", "conn2", {"name": "Bob"})
        await repo.add("filter_contacts", "conn1", {"name": "Carol"})

        response = await client.post(
            "/query/filter_contacts",
            json={"filters": {"connection_id": "conn1"}},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        names = [r["name"] for r in data["data"]]
        assert "Alice" in names
        assert "Carol" in names
        assert "Bob" not in names

    async def test_non_connection_id_filters_ignored(self, repo_and_client) -> None:
        """Non-connection_id filters are ignored (no JSON field filtering in v1).

        Per CONTEXT.md locked decision: "no filtering on raw JSON data fields"
        """
        repo, client = repo_and_client

        await repo.add("json_filter_test", "conn1", {"name": "Alice", "status": "active"})
        await repo.add("json_filter_test", "conn2", {"name": "Bob", "status": "inactive"})

        # Try to filter on 'status' (a JSON field) - should be ignored
        response = await client.post(
            "/query/json_filter_test",
            json={"filters": {"status": "active"}},
        )

        assert response.status_code == 200
        data = response.json()
        # All records returned because JSON field filtering is not supported
        assert data["count"] == 2

    async def test_invalid_model_name_returns_400(self, repo_and_client) -> None:
        """Invalid model name returns 400 with Problem Details."""
        _, client = repo_and_client

        response = await client.post("/query/INVALID!", json={})

        assert response.status_code == 400
        data = response.json()
        assert data["type"] == "urn:data-hub:error:invalid-model"
        assert data["title"] == "Invalid Model Name"
        assert data["status"] == 400
        assert "INVALID!" in data["detail"]

    async def test_filter_value_over_256_chars_returns_400(self, repo_and_client) -> None:
        """Filter value over 256 chars returns 400."""
        _, client = repo_and_client

        long_value = "x" * 300

        response = await client.post(
            "/query/contacts",
            json={"filters": {"connection_id": long_value}},
        )

        assert response.status_code == 400
        data = response.json()
        assert data["type"] == "urn:data-hub:error:filter-value-too-long"
        assert data["title"] == "Filter Value Too Long"
        assert "256" in data["detail"]

    async def test_limit_is_capped_at_max(self, repo_and_client) -> None:
        """Limit is capped at MAX_QUERY_LIMIT (1000)."""
        _, client = repo_and_client

        response = await client.post(
            "/query/contacts",
            json={"limit": 5000},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 1000  # Capped at MAX_QUERY_LIMIT

    async def test_empty_results_return_200(self, repo_and_client) -> None:
        """Empty results return 200 with empty data array."""
        _, client = repo_and_client

        response = await client.post("/query/nonexistent_model", json={})

        assert response.status_code == 200
        data = response.json()
        assert data["data"] == []
        assert data["count"] == 0
        assert data["has_more"] is False

    async def test_sql_injection_in_filter_not_executed(self, repo_and_client) -> None:
        """SQL injection attempt in filter value is not executed."""
        repo, client = repo_and_client

        await repo.add("secure_model", "conn1", {"name": "Safe"})

        # Try SQL injection in filter value
        injection = "'; DROP TABLE data_records; --"
        response = await client.post(
            "/query/secure_model",
            json={"filters": {"connection_id": injection}},
        )

        # Should not crash - injection treated as literal string
        assert response.status_code == 200
        data = response.json()
        # Injection value won't match any record (it's parameterized)
        assert data["count"] == 0

    async def test_has_more_true_when_more_records_exist(self, repo_and_client) -> None:
        """has_more is true when more records exist beyond limit."""
        repo, client = repo_and_client

        for i in range(5):
            await repo.add("hasmore_model", f"conn{i}", {"index": i})

        response = await client.post(
            "/query/hasmore_model",
            json={"limit": 3},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 3
        assert data["has_more"] is True


async def test_model_name_with_numbers_valid(repo_and_client) -> None:
    """Model name with numbers (like hubspot_contact_v2) is valid."""
    _, client = repo_and_client
    response = await client.post("/query/hubspot_contact_v2", json={})
    assert response.status_code == 200


async def test_model_name_with_underscore_valid(repo_and_client) -> None:
    """Model name with underscores is valid."""
    _, client = repo_and_client
    response = await client.post("/query/my_model_name", json={})
    assert response.status_code == 200


async def test_model_name_uppercase_invalid(repo_and_client) -> None:
    """Model name with uppercase letters is invalid."""
    _, client = repo_and_client
    response = await client.post("/query/MyModel", json={})
    assert response.status_code == 400


async def test_model_name_starting_with_number_invalid(repo_and_client) -> None:
    """Model name starting with number is invalid."""
    _, client = repo_and_client
    response = await client.post("/query/123model", json={})
    assert response.status_code == 400
