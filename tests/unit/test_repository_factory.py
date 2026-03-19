"""Unit tests for repository factory scheme detection."""
import pytest

from src.adapters.driven.repository_factory import (
    SUPPORTED_SCHEMES,
    _normalize_url,
    create_repository,
)


class TestNormalizeUrl:
    """Tests for URL normalization."""

    def test_sqlite_normalized_to_aiosqlite(self):
        """sqlite:// becomes sqlite+aiosqlite://"""
        url, backend = _normalize_url("sqlite:///./data.db")
        assert url == "sqlite+aiosqlite:///./data.db"
        assert backend == "sqlite"

    def test_sqlite_aiosqlite_unchanged(self):
        """sqlite+aiosqlite:// stays unchanged."""
        url, backend = _normalize_url("sqlite+aiosqlite:///./data.db")
        assert url == "sqlite+aiosqlite:///./data.db"
        assert backend == "sqlite"

    def test_postgresql_normalized_to_asyncpg(self):
        """postgresql:// becomes postgresql+asyncpg://"""
        url, backend = _normalize_url("postgresql://user:pass@localhost/db")
        assert url == "postgresql+asyncpg://user:pass@localhost/db"
        assert backend == "postgresql"

    def test_postgresql_asyncpg_unchanged(self):
        """postgresql+asyncpg:// stays unchanged."""
        url, backend = _normalize_url("postgresql+asyncpg://user:pass@localhost/db")
        assert url == "postgresql+asyncpg://user:pass@localhost/db"
        assert backend == "postgresql"

    def test_postgres_alias_normalized(self):
        """postgres:// (alias) becomes postgresql+asyncpg://"""
        url, backend = _normalize_url("postgres://user:pass@localhost/db")
        assert url == "postgresql+asyncpg://user:pass@localhost/db"
        assert backend == "postgresql"

    def test_unsupported_scheme_raises_valueerror(self):
        """Unsupported scheme raises ValueError with helpful message."""
        with pytest.raises(ValueError) as exc_info:
            _normalize_url("mysql://localhost/db")

        error_msg = str(exc_info.value)
        assert "mysql" in error_msg
        assert "Supported schemes" in error_msg


class TestCreateRepository:
    """Tests for repository creation."""

    def test_sqlite_creates_sqlite_repository(self):
        """SQLite URL creates SQLiteDataRepository."""
        bundle = create_repository("sqlite+aiosqlite:///:memory:")
        assert bundle.backend == "sqlite"
        assert bundle.repository is not None
        assert bundle.engine is not None

    def test_sqlite_repository_has_correct_type(self):
        """SQLite bundle contains SQLiteDataRepository instance."""
        from src.adapters.driven.sqlite.repository import SQLiteDataRepository

        bundle = create_repository("sqlite+aiosqlite:///:memory:")
        assert isinstance(bundle.repository, SQLiteDataRepository)

    def test_unsupported_scheme_fails_fast(self):
        """Unsupported scheme raises ValueError immediately."""
        with pytest.raises(ValueError) as exc_info:
            create_repository("oracle://localhost/db")

        assert "oracle" in str(exc_info.value)


class TestSupportedSchemes:
    """Tests for supported scheme constants."""

    def test_all_sqlite_schemes_map_to_sqlite(self):
        """All SQLite variants map to 'sqlite' backend."""
        assert SUPPORTED_SCHEMES["sqlite"] == "sqlite"
        assert SUPPORTED_SCHEMES["sqlite+aiosqlite"] == "sqlite"

    def test_all_postgresql_schemes_map_to_postgresql(self):
        """All PostgreSQL variants map to 'postgresql' backend."""
        assert SUPPORTED_SCHEMES["postgresql"] == "postgresql"
        assert SUPPORTED_SCHEMES["postgresql+asyncpg"] == "postgresql"
        assert SUPPORTED_SCHEMES["postgres"] == "postgresql"
        assert SUPPORTED_SCHEMES["postgres+asyncpg"] == "postgresql"
