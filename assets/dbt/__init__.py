"""dbt assets for Salesforce data transformations."""

from pathlib import Path

import dagster as dg
from dagster_dbt import DbtCliResource, DbtProject, dbt_assets

# Path to dbt project
DBT_PROJECT_DIR = Path(__file__).parent.parent.parent / "dbt_project"

dbt_project = DbtProject(
    project_dir=DBT_PROJECT_DIR,
)

# Prepare dbt project for parsing (generates manifest if needed)
dbt_project.prepare_if_dev()


@dbt_assets(manifest=dbt_project.manifest_path)
def dbt_salesforce_models(context: dg.AssetExecutionContext, dbt: DbtCliResource):
    """dbt models that transform raw Salesforce data into analytics-ready tables."""
    yield from dbt.cli(["build"], context=context).stream()


__all__ = ["dbt_salesforce_models", "dbt_project"]
