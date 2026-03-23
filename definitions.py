"""Dagster definitions entry point.

All assets and resources are registered here for discovery by workspace.yaml.
"""

import dagster as dg
from dagster_dbt import DbtCliResource

from assets.dbt import dbt_project, dbt_salesforce_models
from assets.salesforce.event import salesforce_events
from assets.salesforce.opportunity import salesforce_opportunities
from assets.salesforce.opportunity_history import salesforce_opportunity_history
from assets.salesforce.task import salesforce_tasks
from resources.nango import NangoResource
from resources.postgres import PostgresResource

defs = dg.Definitions(
    assets=[
        # Raw Salesforce ingestion
        salesforce_opportunities,
        salesforce_opportunity_history,
        salesforce_tasks,
        salesforce_events,
        # dbt transformations
        dbt_salesforce_models,
    ],
    resources={
        "postgres_db": PostgresResource(
            connection_uri=dg.EnvVar("DAGSTER_DATABASE_URL"),
        ),
        "nango": NangoResource(
            secret_key=dg.EnvVar("NANGO_SECRET_KEY"),
        ),
        "dbt": DbtCliResource(
            project_dir=dbt_project,
        ),
    },
)
