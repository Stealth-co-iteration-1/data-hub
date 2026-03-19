"""SQLite implementation of DataRepository port.

Implements the kernel's DataRepository Protocol using SQLAlchemy async ORM.
The kernel never imports this module directly.
"""
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .models import AuditLog, DataRecord


class SQLiteDataRepository:
    """SQLite adapter implementing DataRepository port.

    Uses SQLAlchemy async ORM for persistence.
    Kernel uses this via dependency injection, never imports directly.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Initialize with session factory.

        Args:
            session_factory: Factory that creates AsyncSession instances
        """
        self._session_factory = session_factory

    async def add(
        self,
        model: str,
        connection_id: str,
        data: dict[str, Any],
    ) -> str:
        """Persist data and return record ID.

        Also writes audit log entry in same transaction (PERS-03).
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
                    stmt = (
                        sqlite_insert(DataRecord)
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

                # Always write audit entry - PERS-03
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
