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

    async def test_health_reports_sqlite_backend(self):
        """Health endpoint reports sqlite backend (CONF-02).

        Uses direct app.state manipulation to test backend reporting
        without needing to reload the app module.
        """
        from sqlalchemy.ext.asyncio import create_async_engine
        from src.adapters.driving.fastapi.app import app

        # Create engine and set app.state as the lifespan would
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        original_engine = getattr(app.state, "engine", None)
        original_backend = getattr(app.state, "backend", None)

        app.state.engine = engine
        app.state.backend = "sqlite"

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get("/health")

            assert response.status_code == 200
            data = response.json()
            assert data["backend"] == "sqlite"
        finally:
            await engine.dispose()
            if original_engine is not None:
                app.state.engine = original_engine
            if original_backend is not None:
                app.state.backend = original_backend

    @pytest.mark.skipif(
        not os.environ.get("TEST_POSTGRES_URL"),
        reason="TEST_POSTGRES_URL not set",
    )
    async def test_health_reports_postgresql_backend(self):
        """Health endpoint reports postgresql backend (CONF-02).

        Uses direct app.state manipulation to test backend reporting
        when PostgreSQL is configured.
        """
        from sqlalchemy.ext.asyncio import create_async_engine
        from src.adapters.driving.fastapi.app import app

        pg_url = os.environ["TEST_POSTGRES_URL"]
        # Normalize URL to use asyncpg driver
        if "+asyncpg" not in pg_url:
            if pg_url.startswith("postgres://"):
                pg_url = pg_url.replace("postgres://", "postgresql+asyncpg://", 1)
            else:
                pg_url = pg_url.replace("postgresql://", "postgresql+asyncpg://", 1)

        engine = create_async_engine(pg_url)
        original_engine = getattr(app.state, "engine", None)
        original_backend = getattr(app.state, "backend", None)

        app.state.engine = engine
        app.state.backend = "postgresql"

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get("/health")

            assert response.status_code == 200
            data = response.json()
            assert data["backend"] == "postgresql"
        finally:
            await engine.dispose()
            if original_engine is not None:
                app.state.engine = original_engine
            if original_backend is not None:
                app.state.backend = original_backend


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
