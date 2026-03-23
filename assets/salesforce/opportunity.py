"""Salesforce Opportunity asset with full refresh."""
import os
import json
import dagster as dg
from psycopg2.extras import execute_values

from resources.nango import NangoResource
from resources.postgres import PostgresResource


# Table DDL - executed on first materialization
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS salesforce_opportunities (
    salesforce_id TEXT NOT NULL,
    connection_id TEXT NOT NULL,
    data JSONB NOT NULL,
    synced_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (salesforce_id, connection_id)
);
"""


@dg.asset
def salesforce_opportunities(
    nango: NangoResource,
    postgres_db: PostgresResource,
) -> dg.MaterializeResult:
    """Fetch Opportunity records from Nango and persist to PostgreSQL.

    Full refresh strategy: DELETE existing records for connection_id,
    then INSERT all records from Nango.
    """
    connection_id = os.environ["NANGO_CONNECTION_ID"]
    conn = postgres_db._connection

    # Ensure table exists
    with conn.cursor() as cur:
        cur.execute(CREATE_TABLE_SQL)

    # Fetch from Nango
    records = nango.get_records(model="Opportunity", connection_id=connection_id)

    # Full refresh: DELETE + INSERT in transaction
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM salesforce_opportunities WHERE connection_id = %s",
            (connection_id,),
        )

        if records:
            values = [
                (record["id"], connection_id, json.dumps(record))
                for record in records
            ]
            execute_values(
                cur,
                """INSERT INTO salesforce_opportunities
                   (salesforce_id, connection_id, data, synced_at) VALUES %s""",
                values,
                template="(%s, %s, %s, NOW())",
            )

    conn.commit()

    return dg.MaterializeResult(
        metadata={
            "dagster/row_count": len(records),
            "connection_id": connection_id,
        }
    )
