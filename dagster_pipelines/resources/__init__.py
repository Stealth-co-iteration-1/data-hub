"""Dagster resource definitions."""
from dagster_pipelines.resources.postgres import PostgresResource
from dagster_pipelines.resources.nango import NangoResource

__all__ = ["PostgresResource", "NangoResource"]
