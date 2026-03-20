"""SQLAlchemy ORM models for PostgreSQL adapter.

These models live ONLY in the adapter layer. The kernel never imports them.
ORM types are mapped to plain dicts before returning to kernel.

NOTE: These models are identical to sqlite/models.py because SQLAlchemy ORM
models are dialect-agnostic. However, each adapter maintains its own copy
to preserve hexagonal architecture independence — adapters should not
import from each other.
"""
from datetime import datetime, timezone
from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


class DataRecord(Base):
    """Persisted data record.

    Maps to kernel's repository.add() / repository.get() contract.
    """
    __tablename__ = "data_records"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    event_id: Mapped[str | None] = mapped_column(String, unique=True, nullable=True, index=True)
    model_name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    connection_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    data: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


class AuditLog(Base):
    """Audit trail for data operations.

    Captures: timestamp, connection_id, model_name, status.
    Written in same transaction as DataRecord for atomicity.
    """
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    record_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    model_name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    connection_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String, nullable=False)  # "added" | "duplicate"
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
