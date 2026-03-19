"""SQLite adapter package.

Exports the SQLiteDataRepository and session factory for use in application composition.
"""

__all__ = ["SQLiteDataRepository", "create_session_factory"]


def __getattr__(name: str) -> object:
    if name == "SQLiteDataRepository":
        from src.adapters.driven.sqlite.repository import SQLiteDataRepository
        return SQLiteDataRepository
    if name == "create_session_factory":
        from src.adapters.driven.sqlite.session import create_session_factory
        return create_session_factory
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
