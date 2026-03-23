"""Dagster definitions entry point.

All assets and resources are registered here for discovery by workspace.yaml.
"""
import dagster as dg
from dagster_pipelines.assets.salesforce.opportunity import salesforce_opportunities
from dagster_pipelines.assets.salesforce.opportunity_history import salesforce_opportunity_history
from dagster_pipelines.assets.salesforce.task import salesforce_tasks
from dagster_pipelines.assets.salesforce.event import salesforce_events
from dagster_pipelines.resources.postgres import PostgresResource
from dagster_pipelines.resources.nango import NangoResource

defs = dg.Definitions(
    assets=[
        salesforce_opportunities,
        salesforce_opportunity_history,
        salesforce_tasks,
        salesforce_events,
    ],
    resources={
        "postgres_db": PostgresResource(
            connection_uri=dg.EnvVar("DAGSTER_DATABASE_URL"),
        ),
        "nango": NangoResource(
            secret_key=dg.EnvVar("NANGO_SECRET_KEY"),
        ),
    },
)
