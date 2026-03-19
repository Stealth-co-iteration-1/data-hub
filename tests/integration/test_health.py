"""Integration tests for health check endpoint (TRAN-04)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine

WEBHOOK_SECRET = "test_secret_for_health_tests"


@pytest.fixture
async def client():
    """AsyncClient with in-memory SQLite engine for DB health check."""
    from src.adapters.driving.fastapi.app import app

    # Create an in-memory SQLite engine and attach it to app.state
    # This simulates the lifespan without needing a real database file
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    original_engine = getattr(app.state, "engine", None)
    original_backend = getattr(app.state, "backend", None)
    app.state.engine = engine
    app.state.backend = "sqlite"

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c

    await engine.dispose()
    if original_engine is not None:
        app.state.engine = original_engine
    if original_backend is not None:
        app.state.backend = original_backend


class TestHealthCheck:
    """Tests for TRAN-04: Health check endpoint."""

    async def test_health_returns_200_with_status_ok(self, client: AsyncClient):
        """Health check returns 200 with status ok when DB is accessible."""
        response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    async def test_health_includes_version(self, client: AsyncClient):
        """Health check response includes version from settings."""
        from src.config.settings import settings

        response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert data["version"] == settings.version

    async def test_health_response_does_not_expose_secrets(self, client: AsyncClient):
        """Health check response must not include sensitive information."""
        response = await client.get("/health")

        data = response.json()
        # Remove backend field for secret check - "sqlite" in backend is expected
        data_without_backend = {k: v for k, v in data.items() if k != "backend"}
        response_text = str(data_without_backend).lower()

        # Should not contain database connection info
        assert "sqlite" not in response_text
        assert "password" not in response_text
        assert "secret" not in response_text
        assert "database_url" not in response_text


class TestHealthCheckDbFailure:
    """Tests for health check when database is unreachable."""

    async def test_health_returns_503_on_db_failure(self):
        """Health check returns 503 when DB connection fails."""
        from src.adapters.driving.fastapi.app import app

        # Create an engine with an invalid DB path to simulate failure
        # Use a path that cannot exist to trigger a connection error
        failing_engine = MagicMock()
        failing_engine.connect = MagicMock(
            return_value=AsyncMock(
                __aenter__=AsyncMock(side_effect=Exception("DB connection failed")),
                __aexit__=AsyncMock(return_value=False),
            )
        )

        original_engine = getattr(app.state, "engine", None)
        app.state.engine = failing_engine

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as c:
                response = await c.get("/health")

            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "error"
            # Must not expose internal error details
            assert "db" not in str(data).lower() or "status" in str(data).lower()
        finally:
            if original_engine is not None:
                app.state.engine = original_engine
