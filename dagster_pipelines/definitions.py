"""Dagster definitions entry point.

All assets and resources are registered here for discovery by workspace.yaml.
"""
import dagster as dg
from dagster_pipelines.assets.salesforce.opportunity import salesforce_opportunities
from dagster_pipelines.resources.postgres import PostgresResource
from dagster_pipelines.resources.nango import NangoResource

defs = dg.Definitions(
    assets=[salesforce_opportunities],
    resources={
        "postgres_db": PostgresResource(
            connection_uri=dg.EnvVar("DAGSTER_DATABASE_URL"),
        ),
        "nango": NangoResource(
            secret_key=dg.EnvVar("NANGO_SECRET_KEY"),
        ),
    },
)
