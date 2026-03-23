"""Dagster definitions entry point.

All assets and resources are registered here for discovery by workspace.yaml.
"""
import dagster as dg
from assets.salesforce.opportunity import salesforce_opportunities
from assets.salesforce.opportunity_history import salesforce_opportunity_history
from assets.salesforce.task import salesforce_tasks
from assets.salesforce.event import salesforce_events
from resources.postgres import PostgresResource
from resources.nango import NangoResource

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
