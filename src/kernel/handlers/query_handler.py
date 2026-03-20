"""QueryHandler - processes QueryData queries.

Orchestrates the query workflow:
1. Enforce limit cap (MAX_QUERY_LIMIT)
2. Execute query via repository port
3. Return results (no events emitted - read-only operation)
"""
from typing import Any

from ..ports.repository import DataRepository
from ..queries.query_data import MAX_QUERY_LIMIT, QueryData


class QueryHandler:
    """Handler for QueryData queries.

    Uses dependency injection - receives repository port, not concrete implementation.
    The kernel never knows about PostgreSQL, SQLite, etc.
    """

    def __init__(self, repository: DataRepository) -> None:
        """Initialize with repository port.

        Args:
            repository: Port for data persistence
        """
        self._repository = repository

    async def handle(self, query: QueryData) -> list[dict[str, Any]]:
        """Process a QueryData query.

        Enforces limit cap unconditionally, then delegates to repository.
        Does NOT emit events - queries are read-only.

        Args:
            query: The query containing filter criteria

        Returns:
            List of matching records as plain dicts with system fields
        """
        # CRITICAL: Unconditional limit cap - QURY-03
        # Even if caller requests more, we cap at MAX_QUERY_LIMIT
        effective_limit = min(query.limit, MAX_QUERY_LIMIT)

        # Execute query via repository port
        # Note: repository.query() signature is (model, filters, limit)
        # No offset parameter - port doesn't support it yet (deferred)
        results = await self._repository.query(
            model=query.model,
            filters=query.filters,
            limit=effective_limit,
        )

        return results
