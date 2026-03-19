"""Repository factory for backend selection based on DATABASE_URL scheme.

Creates the appropriate DataRepository implementation based on URL scheme.
Encapsulates engine and session factory creation.
"""
from urllib.parse import urlparse

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from src.kernel.ports.repository import DataRepository


class RepositoryBundle:
    """Container for repository, engine, and backend info.

    Provides all components needed by the application:
    - repository: DataRepository implementation
    - engine: AsyncEngine for health checks and cleanup
    - backend: String identifier ("sqlite" or "postgresql")
    """

    def __init__(
        self,
        repository: DataRepository,
        engine: AsyncEngine,
        backend: str,
    ) -> None:
        self.repository = repository
        self.engine = engine
        self.backend = backend


SUPPORTED_SCHEMES = {
    "sqlite": "sqlite",
    "sqlite+aiosqlite": "sqlite",
    "postgresql": "postgresql",
    "postgresql+asyncpg": "postgresql",
    "postgres": "postgresql",  # Common alias
    "postgres+asyncpg": "postgresql",
}


def _normalize_url(database_url: str) -> tuple[str, str]:
    """Normalize database URL and determine backend type.

    Args:
        database_url: Original database URL

    Returns:
        Tuple of (normalized_url, backend_type)

    Raises:
        ValueError: If scheme is not supported
    """
    parsed = urlparse(database_url)
    scheme = parsed.scheme.lower()

    if scheme not in SUPPORTED_SCHEMES:
        supported = ", ".join(sorted(set(SUPPORTED_SCHEMES.keys())))
        raise ValueError(
            f"Unsupported database scheme '{scheme}'. "
            f"Supported schemes: {supported}"
        )

    backend = SUPPORTED_SCHEMES[scheme]

    # Normalize URL to use the async driver
    if backend == "sqlite" and not scheme.endswith("+aiosqlite"):
        # sqlite:// -> sqlite+aiosqlite://
        normalized = database_url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    elif backend == "postgresql" and "+asyncpg" not in scheme:
        # postgresql:// -> postgresql+asyncpg://
        # postgres:// -> postgresql+asyncpg://
        if scheme.startswith("postgres"):
            if "+" not in scheme:
                if scheme == "postgres":
                    normalized = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
                else:
                    normalized = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
            else:
                normalized = database_url
        else:
            normalized = database_url
    else:
        normalized = database_url

    return normalized, backend


def create_repository(database_url: str, echo: bool = False) -> RepositoryBundle:
    """Create repository, engine, and session factory for the given database URL.

    Factory function that:
    1. Detects backend from URL scheme
    2. Normalizes URL to use async driver
    3. Creates engine and session factory
    4. Returns appropriate repository implementation

    Args:
        database_url: Database connection URL (e.g., "postgresql://...", "sqlite://...")
        echo: If True, log SQL statements (for development)

    Returns:
        RepositoryBundle with repository, engine, and backend type

    Raises:
        ValueError: If database URL scheme is not supported
    """
    normalized_url, backend = _normalize_url(database_url)

    engine = create_async_engine(normalized_url, echo=echo)
    session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
        engine,
        expire_on_commit=False,
    )

    if backend == "sqlite":
        from src.adapters.driven.sqlite.repository import SQLiteDataRepository
        repository = SQLiteDataRepository(session_factory)
    else:  # postgresql
        from src.adapters.driven.postgresql.repository import PostgresDataRepository
        repository = PostgresDataRepository(session_factory, engine)

    return RepositoryBundle(repository, engine, backend)
