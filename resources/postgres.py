"""PostgreSQL resource for Dagster assets.

Uses psycopg2 (sync) for database operations.
"""

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from typing import Any, Mapping

import dagster as dg
import psycopg2
from psycopg2.extensions import connection
from psycopg2.extras import execute_values  # type: ignore[reportUnknownVariableType] - TODO: psycopg2 stubs incomplete
from pydantic import PrivateAttr


class PostgresResource(dg.ConfigurableResource["PostgresResource"]):
    """PostgreSQL database resource using psycopg2.

    Configuration uses EnvVar pattern (not os.getenv) for Dagster Cloud compatibility.

    All database operations go through this resource. Assets should never import
    psycopg2 directly — this class is the bridge to the database.
    """

    connection_uri: str
    _connection: connection | None = PrivateAttr(default=None)

    def _require_connection(self) -> connection:
        """Get connection or raise if not initialized."""
        if self._connection is None:
            raise RuntimeError(
                "PostgresResource not initialized - use within asset context"
            )
        return self._connection

    @contextmanager
    def yield_for_execution(
        self, context: dg.InitResourceContext
    ) -> Iterator["PostgresResource"]:
        """Yield database connection for asset execution."""
        del context  # unused, required by Dagster interface
        conn = psycopg2.connect(self.connection_uri)
        try:
            self._connection = conn
            yield self
        finally:
            conn.close()

    def execute(
        self,
        query: str,
        params: Sequence[Any] | Mapping[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Execute SQL query and return results as list of dicts.

        Args:
            query: SQL query string with %s placeholders
            params: Query parameters (tuple, list, or dict)

        Returns:
            List of row dicts for SELECT queries, empty list for DDL/DML
        """
        conn = self._require_connection()

        with conn.cursor() as cur:
            cur.execute(query, params)

            if cur.description is None:
                return []

            columns: list[str] = [desc[0] for desc in cur.description]

            return [dict(zip(columns, row)) for row in cur.fetchall()]

    def bulk_insert(
        self,
        query: str,
        values: Sequence[tuple[Any, ...]],
        template: str,
    ) -> int:
        """Bulk insert using psycopg2 execute_values for performance.

        Args:
            query: INSERT query with VALUES %s placeholder
            values: List of tuples to insert
            template: Value template (e.g., "(%s, %s, %s, NOW())")

        Returns:
            Number of rows inserted
        """
        if not values:
            return 0

        conn = self._require_connection()

        with conn.cursor() as cur:
            execute_values(cur, query, values, template=template)
            return len(values)

    def commit(self) -> None:
        """Commit the current transaction."""
        self._require_connection().commit()

    def rollback(self) -> None:
        """Rollback the current transaction."""
        self._require_connection().rollback()

    @contextmanager
    def transaction(self) -> Iterator[None]:
        """Context manager for explicit transaction boundaries.

        Commits on success, rolls back on exception.

        Usage:
            with postgres_db.transaction():
                postgres_db.execute("DELETE FROM ...")
                postgres_db.bulk_insert(...)
        """
        try:
            yield
            self.commit()
        except Exception:
            self.rollback()
            raise
