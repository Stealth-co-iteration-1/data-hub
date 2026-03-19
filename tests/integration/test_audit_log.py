"""Integration tests for audit trail functionality (PERS-03)."""
import pytest
from sqlalchemy import select

from src.adapters.driven.sqlite.models import AuditLog


class TestAuditLog:
    """Tests for audit log creation on data operations."""

    async def test_add_creates_audit_entry(self, repository, session_factory):
        """Adding data creates an audit log entry with status 'added'."""
        data = {"name": "Alice"}

        record_id = await repository.add(
            model="contacts",
            connection_id="nango_123",
            data=data,
        )

        # Query audit log directly
        async with session_factory() as session:
            stmt = select(AuditLog).where(AuditLog.record_id == record_id)
            result = await session.execute(stmt)
            audit = result.scalar_one()

            assert audit.status == "added"
            assert audit.model_name == "contacts"
            assert audit.connection_id == "nango_123"

    async def test_duplicate_event_id_creates_audit_entry(self, repository, session_factory):
        """Duplicate event_id creates audit entry with status 'duplicate'."""
        data = {"event_id": "evt_xyz789", "name": "Bob"}

        # First add - status "added"
        id1 = await repository.add(model="contacts", connection_id="src", data=data)

        # Second add with same event_id - status "duplicate"
        id2 = await repository.add(model="contacts", connection_id="src", data=data)

        async with session_factory() as session:
            stmt = select(AuditLog).order_by(AuditLog.id)
            result = await session.execute(stmt)
            audits = result.scalars().all()

            assert len(audits) == 2
            assert audits[0].status == "added"
            assert audits[0].record_id == id1
            assert audits[1].status == "duplicate"
            assert audits[1].record_id == id2

    async def test_audit_entry_has_all_required_fields(self, repository, session_factory):
        """Audit entry contains timestamp, connection_id, model_name, status (PERS-03)."""
        data = {"name": "Charlie"}

        record_id = await repository.add(
            model="products",
            connection_id="integration_abc",
            data=data,
        )

        async with session_factory() as session:
            stmt = select(AuditLog).where(AuditLog.record_id == record_id)
            result = await session.execute(stmt)
            audit = result.scalar_one()

            # All required fields present
            assert audit.occurred_at is not None
            assert audit.connection_id == "integration_abc"
            assert audit.model_name == "products"
            assert audit.status == "added"
            assert audit.record_id == record_id
