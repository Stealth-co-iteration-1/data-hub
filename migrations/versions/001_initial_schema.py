"""Initial schema: data_records and audit_log tables.

Revision ID: 001
Revises:
Create Date: 2026-03-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create data_records and audit_log tables."""
    # Data records table
    op.create_table("data_records",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("event_id", sa.String(), unique=True, nullable=True, index=True),
        sa.Column("table_name", sa.String(), nullable=False, index=True),
        sa.Column("source_id", sa.String(), nullable=False, index=True),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # Audit log table
    op.create_table("audit_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("record_id", sa.String(), nullable=False, index=True),
        sa.Column("table_name", sa.String(), nullable=False, index=True),
        sa.Column("source_id", sa.String(), nullable=False, index=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    """Drop data_records and audit_log tables."""
    op.drop_table("audit_log")
    op.drop_table("data_records")
