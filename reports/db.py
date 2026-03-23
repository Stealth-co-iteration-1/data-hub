"""Database connection helpers for Streamlit reports.

This is a standalone module for the Streamlit app, separate from
the Dagster PostgresResource. Direct psycopg2 usage is allowed here
since this is not a Dagster asset.
"""

import os
from contextlib import contextmanager
from typing import Any, Generator

import pandas as pd
import psycopg2
from dotenv import load_dotenv
from psycopg2.extensions import connection


def _get_database_url() -> str:
    """Load DATABASE_URL from environment, reading .env if needed."""
    # Load .env from project root (one level up from reports/)
    dotenv_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    load_dotenv(dotenv_path)

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL environment variable is not set. "
            "Please set it in .env or as an environment variable."
        )
    return database_url


@contextmanager
def get_connection() -> Generator[connection, None, None]:
    """Context manager for database connections.

    Usage:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM table")
                rows = cur.fetchall()
    """
    conn = psycopg2.connect(_get_database_url())
    try:
        yield conn
    finally:
        conn.close()


def query_to_df(
    sql: str, params: tuple[Any, ...] | dict[str, Any] | None = None
) -> pd.DataFrame:
    """Execute a SQL query and return results as a pandas DataFrame.

    Args:
        sql: SQL query string
        params: Query parameters (tuple for %s placeholders, dict for %(name)s)

    Returns:
        pandas DataFrame with query results
    """
    with get_connection() as conn:
        return pd.read_sql_query(sql, conn, params=params)
