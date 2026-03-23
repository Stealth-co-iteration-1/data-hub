"""Salesforce asset definitions."""
from assets.salesforce.opportunity import salesforce_opportunities
from assets.salesforce.opportunity_history import salesforce_opportunity_history
from assets.salesforce.task import salesforce_tasks
from assets.salesforce.event import salesforce_events

__all__ = [
    "salesforce_opportunities",
    "salesforce_opportunity_history",
    "salesforce_tasks",
    "salesforce_events",
]
