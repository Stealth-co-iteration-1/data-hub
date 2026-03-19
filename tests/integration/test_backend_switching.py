"""Integration tests for backend switching via DATABASE_URL.

Tests CONF-01 and CONF-02:
- Repository factory creates correct adapter based on DATABASE_URL scheme
- SQLite and PostgreSQL adapters coexist without code changes to switch
"""
import os

import pytest
from httpx import ASGITransport, AsyncClient

from src.adapters.driven.repository_factory import create_repository


class TestBackendSwitchingFactory:
    """Test factory creates correct backend based on URL scheme."""

    def test_sqlite_url_creates_sqlite_backend(self):
        """SQLite URL creates SQLite backend (CONF-01)."""
        bundle = create_repository("sqlite+aiosqlite:///:memory:")

        assert bundle.backend == "sqlite"
        from src.adapters.driven.sqlite.repository import SQLiteDataRepository
        assert isinstance(bundle.repository, SQLiteDataRepository)

    @pytest.mark.skipif(
        not os.environ.get("TEST_POSTGRES_URL"),
        reason="TEST_POSTGRES_URL not set",
    )
    def test_postgresql_url_creates_postgresql_backend(self):
        """PostgreSQL URL creates PostgreSQL backend (CONF-01)."""
        bundle = create_repository(os.environ["TEST_POSTGRES_URL"])

        assert bundle.backend == "postgresql"
        from src.adapters.driven.postgresql.repository import PostgresDataRepository
        assert isinstance(bundle.repository, PostgresDataRepository)


class TestBackendSwitchingApp:
    """Test app responds correctly with different backends."""

    @pytest.fixture
    def sqlite_env(self, monkeypatch):
        """Configure SQLite backend via environment."""
        monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
        monkeypatch.setenv("NANGO_WEBHOOK_SECRET", "test_secret")

    @pytest.fixture
    def postgres_env(self, monkeypatch):
        """Configure PostgreSQL backend via environment (if available)."""
        pg_url = os.environ.get("TEST_POSTGRES_URL")
        if not pg_url:
            pytest.skip("TEST_POSTGRES_URL not set")
        monkeypatch.setenv("DATABASE_URL", pg_url)
        monkeypatch.setenv("NANGO_WEBHOOK_SECRET", "test_secret")

    async def test_health_reports_sqlite_backend(self, sqlite_env):
        """Health endpoint reports sqlite backend (CONF-02)."""
        # Must reimport app after env change
        import importlib
        from src.adapters.driving.fastapi import app as app_module
        importlib.reload(app_module)

        async with AsyncClient(
            transport=ASGITransport(app=app_module.app),
            base_url="http://test",
        ) as client:
            response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["backend"] == "sqlite"

    @pytest.mark.skipif(
        not os.environ.get("TEST_POSTGRES_URL"),
        reason="TEST_POSTGRES_URL not set",
    )
    async def test_health_reports_postgresql_backend(self, postgres_env):
        """Health endpoint reports postgresql backend (CONF-02)."""
        import importlib
        from src.adapters.driving.fastapi import app as app_module
        importlib.reload(app_module)

        async with AsyncClient(
            transport=ASGITransport(app=app_module.app),
            base_url="http://test",
        ) as client:
            response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["backend"] == "postgresql"


class TestUnsupportedScheme:
    """Test unsupported schemes fail fast."""

    def test_mysql_scheme_raises_valueerror(self):
        """Unsupported MySQL scheme raises ValueError (fail fast)."""
        with pytest.raises(ValueError) as exc_info:
            create_repository("mysql://localhost/db")

        assert "mysql" in str(exc_info.value)
        assert "Supported schemes" in str(exc_info.value)

    def test_oracle_scheme_raises_valueerror(self):
        """Unsupported Oracle scheme raises ValueError (fail fast)."""
        with pytest.raises(ValueError) as exc_info:
            create_repository("oracle://localhost/db")

        assert "oracle" in str(exc_info.value)
