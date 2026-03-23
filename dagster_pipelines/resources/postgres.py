"""PostgreSQL resource for Dagster assets.

Uses psycopg2 (sync) - separate from FastAPI's asyncpg.
"""
import dagster as dg
import psycopg2
from contextlib import contextmanager
from pydantic import PrivateAttr
from typing import Any


class PostgresResource(dg.ConfigurableResource):
    """PostgreSQL database resource using psycopg2.

    Configuration uses EnvVar pattern (not os.getenv) for Dagster Cloud compatibility.
    """

    connection_uri: str
    _connection: Any = PrivateAttr(default=None)

    @contextmanager
    def yield_for_execution(self, context: dg.InitResourceContext):
        """Yield database connection for asset execution."""
        conn = psycopg2.connect(self.connection_uri)
        try:
            self._connection = conn
            yield self
        finally:
            conn.close()

    def execute(self, query: str) -> list[dict]:
        """Execute SQL query and return results as list of dicts."""
        with self._connection.cursor() as cur:
            cur.execute(query)
            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]
