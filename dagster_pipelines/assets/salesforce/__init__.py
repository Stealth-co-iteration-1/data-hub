"""Salesforce asset definitions."""
from dagster_pipelines.assets.salesforce.opportunity import salesforce_opportunities
from dagster_pipelines.assets.salesforce.opportunity_history import salesforce_opportunity_history
from dagster_pipelines.assets.salesforce.task import salesforce_tasks
from dagster_pipelines.assets.salesforce.event import salesforce_events

__all__ = [
    "salesforce_opportunities",
    "salesforce_opportunity_history",
    "salesforce_tasks",
    "salesforce_events",
]
