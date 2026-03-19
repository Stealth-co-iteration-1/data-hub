"""Rename columns to align with Nango terminology.

- table_name -> model_name (matches Nango's 'model' field)
- source_id -> connection_id (matches Nango's 'connectionId' field)

Revision ID: 002
Revises: 001
Create Date: 2026-03-19

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rename columns in data_records and audit_log tables."""
    # SQLite requires batch mode for ALTER COLUMN operations
    with op.batch_alter_table("data_records") as batch_op:
        batch_op.alter_column("table_name", new_column_name="model_name")
        batch_op.alter_column("source_id", new_column_name="connection_id")

    with op.batch_alter_table("audit_log") as batch_op:
        batch_op.alter_column("table_name", new_column_name="model_name")
        batch_op.alter_column("source_id", new_column_name="connection_id")


def downgrade() -> None:
    """Revert column renames."""
    with op.batch_alter_table("data_records") as batch_op:
        batch_op.alter_column("model_name", new_column_name="table_name")
        batch_op.alter_column("connection_id", new_column_name="source_id")

    with op.batch_alter_table("audit_log") as batch_op:
        batch_op.alter_column("model_name", new_column_name="table_name")
        batch_op.alter_column("connection_id", new_column_name="source_id")
