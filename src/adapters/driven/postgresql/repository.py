"""PostgreSQL implementation of DataRepository port.

Implements the kernel's DataRepository Protocol using SQLAlchemy async ORM with asyncpg.
Uses dialect-specific insert for idempotent operations.
The kernel never imports this module directly.
"""
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from src.adapters.driven.sqlite.models import AuditLog, DataRecord


class PostgresDataRepository:
    """PostgreSQL adapter implementing DataRepository port.

    Uses SQLAlchemy async ORM with asyncpg driver for persistence.
    Kernel uses this via dependency injection, never imports directly.
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        engine: AsyncEngine,
    ) -> None:
        """Initialize with session factory and engine.

        Args:
            session_factory: Factory that creates AsyncSession instances
            engine: AsyncEngine for health checks and direct access
        """
        self._session_factory = session_factory
        self._engine = engine

    @property
    def engine(self) -> AsyncEngine:
        """Expose engine for health check access."""
        return self._engine

    async def add(
        self,
        model: str,
        connection_id: str,
        data: dict[str, Any],
    ) -> str:
        """Persist data and return record ID.

        Also writes audit log entry in same transaction.
        Audit status is 'added' for new records, 'duplicate' for skipped duplicates.

        Args:
            model: Target model name (e.g., 'hubspot_contact')
            connection_id: Nango connection ID
            data: Data payload to persist

        Returns:
            Record ID (may not exist in DB if duplicate event_id was skipped)
        """
        record_id = str(uuid4())
        event_id = data.get("event_id")

        async with self._session_factory() as session:
            async with session.begin():
                if event_id is not None:
                    # Idempotent insert - skip if event_id already exists
                    # CRITICAL: Use postgresql dialect insert, NOT sqlite
                    stmt = (
                        pg_insert(DataRecord)
                        .values(
                            id=record_id,
                            event_id=event_id,
                            model_name=model,
                            connection_id=connection_id,
                            data=data,
                        )
                        .on_conflict_do_nothing(index_elements=["event_id"])
                    )
                    result = await session.execute(stmt)
                    # rowcount > 0 means inserted, 0 means duplicate skipped
                    status = "added" if result.rowcount > 0 else "duplicate"
                else:
                    # Normal insert - no idempotency check
                    record = DataRecord(
                        id=record_id,
                        event_id=None,
                        model_name=model,
                        connection_id=connection_id,
                        data=data,
                    )
                    session.add(record)
                    status = "added"

                # Always write audit entry - atomic with data
                audit = AuditLog(
                    record_id=record_id,
                    model_name=model,
                    connection_id=connection_id,
                    status=status,
                )
                session.add(audit)
                # session.begin() auto-commits both DataRecord and AuditLog atomically

        return record_id

    async def get(
        self,
        model: str,
        record_id: str,
    ) -> dict[str, Any] | None:
        """Retrieve a record by ID.

        Args:
            model: Target model name (must match)
            record_id: Record ID to retrieve

        Returns:
            Data dict or None if not found or model doesn't match
        """
        async with self._session_factory() as session:
            stmt = select(DataRecord).where(
                DataRecord.id == record_id,
                DataRecord.model_name == model,
            )
            result = await session.execute(stmt)
            record = result.scalar_one_or_none()

            if record is None:
                return None

            # Return plain dict - never leak ORM objects to kernel
            return record.data

    async def query(
        self,
        model: str,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Query records with optional filters.

        Args:
            model: Model name to query
            filters: Optional filter conditions (column: value)
            limit: Maximum records to return (enforced)

        Returns:
            List of matching records as plain dicts
        """
        async with self._session_factory() as session:
            stmt = select(DataRecord).where(DataRecord.model_name == model)

            # Apply filters on JSON data column
            if filters:
                for key, value in filters.items():
                    # PostgreSQL JSONB extraction: data->>'key' = value
                    stmt = stmt.where(DataRecord.data[key].astext == str(value))

            stmt = stmt.limit(limit)

            result = await session.execute(stmt)
            records = result.scalars().all()

            # Return plain dicts - never leak ORM objects
            return [record.data for record in records]
