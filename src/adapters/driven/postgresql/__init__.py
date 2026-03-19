"""PostgreSQL adapter for DataRepository port.

Uses asyncpg driver via SQLAlchemy for async PostgreSQL operations.
"""
from .repository import PostgresDataRepository

__all__ = ["PostgresDataRepository"]
