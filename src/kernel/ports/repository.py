"""Repository port for data persistence."""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class DataRepository(Protocol):
    """Port interface for data persistence.

    Driven adapters (e.g., PostgreSQL) implement this protocol.
    The kernel uses this abstraction without knowing the concrete implementation.
    """

    async def add(
        self,
        model: str,
        connection_id: str,
        data: dict[str, Any],
    ) -> str:
        """Persist data and return the record ID.

        Args:
            model: Model name (e.g., 'hubspot_contact')
            connection_id: Nango connection ID
            data: Validated data to persist

        Returns:
            The unique identifier of the created record
        """
        ...

    async def get(
        self,
        model: str,
        record_id: str,
    ) -> dict[str, Any] | None:
        """Retrieve a record by ID.

        Args:
            model: Model name
            record_id: Unique identifier of the record

        Returns:
            The record data or None if not found
        """
        ...

    async def query(
        self,
        model: str,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Query records with optional filters.

        Args:
            model: Model name to query
            filters: Optional filter conditions (column: value)
            limit: Maximum records to return (enforced)

        Returns:
            List of matching records as plain dicts
        """
        ...
