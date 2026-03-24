"""Salesforce OpportunityHistory asset with full refresh."""
import json
import os
from typing import Any

import dagster as dg

from resources.nango import NangoResource
from resources.postgres import PostgresResource


# Table DDL - executed on first materialization
CREATE_TABLE_SQL = """
CREATE SCHEMA IF NOT EXISTS public_raw;

CREATE TABLE IF NOT EXISTS public_raw.salesforce_opportunity_history (
    salesforce_id TEXT NOT NULL,
    connection_id TEXT NOT NULL,
    data JSONB NOT NULL,
    synced_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (salesforce_id, connection_id)
);
"""


@dg.asset(group_name="salesforce_raw")
def salesforce_opportunity_history(
    nango: NangoResource,
    postgres_db: PostgresResource,
) -> dg.MaterializeResult[Any]:
    """Fetch OpportunityHistory records from Nango and persist to PostgreSQL.

    Full refresh strategy: DELETE existing records for connection_id,
    then INSERT all records from Nango.
    """
    connection_id = os.environ["NANGO_CONNECTION_ID"]

    postgres_db.execute(CREATE_TABLE_SQL)

    # Fetch from Nango
    records = nango.get_records(model="OpportunityHistory", connection_id=connection_id)

    # Full refresh: DELETE + INSERT in transaction
    with postgres_db.transaction():
        postgres_db.execute(
            "DELETE FROM public_raw.salesforce_opportunity_history WHERE connection_id = %s",
            (connection_id,),
        )

        if records:
            values = [
                (record["id"], connection_id, json.dumps(record)) for record in records
            ]

            postgres_db.bulk_insert(
                """INSERT INTO public_raw.salesforce_opportunity_history
                       (salesforce_id, connection_id, data, synced_at) VALUES %s""",
                values,
                "(%s, %s, %s, NOW())",
            )

    return dg.MaterializeResult(
        metadata={
            "dagster/row_count": len(records),
            "connection_id": connection_id,
        }
    )
