"""Salesforce asset definitions."""
from assets.salesforce.account import salesforce_accounts
from assets.salesforce.contact import salesforce_contacts
from assets.salesforce.event import salesforce_events
from assets.salesforce.opportunity import salesforce_opportunities
from assets.salesforce.opportunity_history import salesforce_opportunity_history
from assets.salesforce.task import salesforce_tasks
from assets.salesforce.user import salesforce_users

__all__ = [
    "salesforce_accounts",
    "salesforce_contacts",
    "salesforce_events",
    "salesforce_opportunities",
    "salesforce_opportunity_history",
    "salesforce_tasks",
    "salesforce_users",
]
