"""Placeholder asset to verify PostgresResource works end-to-end.

Removed after Phase 11 introduces real Salesforce assets.
"""
import dagster as dg
from dagster_pipelines.resources.postgres import PostgresResource


@dg.asset
def ping_database(postgres_db: PostgresResource) -> dg.MaterializeResult:
    """Verify PostgreSQL connection by executing SELECT 1.

    Returns MaterializeResult with connection status metadata.
    """
    result = postgres_db.execute("SELECT 1 as ping")
    return dg.MaterializeResult(
        metadata={
            "ping_result": result[0]["ping"],
            "status": "connected",
        }
    )
