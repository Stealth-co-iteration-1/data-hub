"""Dagster definitions entry point.

All assets and resources are registered here for discovery by workspace.yaml.
"""
import dagster as dg
from dagster_pipelines.assets.ping_database import ping_database
from dagster_pipelines.resources.postgres import PostgresResource

defs = dg.Definitions(
    assets=[ping_database],
    resources={
        "postgres_db": PostgresResource(
            connection_uri=dg.EnvVar("DAGSTER_DATABASE_URL"),
        ),
    },
)
