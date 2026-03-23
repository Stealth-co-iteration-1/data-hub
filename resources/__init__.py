"""Dagster resource definitions."""
from resources.postgres import PostgresResource
from resources.nango import NangoResource

__all__ = ["PostgresResource", "NangoResource"]
