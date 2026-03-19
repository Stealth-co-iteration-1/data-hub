"""Fake repository for unit testing.

Implements DataRepository Protocol with in-memory storage.
Use in kernel unit tests to avoid database dependencies.
"""
from typing import Any
from uuid import uuid4


class FakeDataRepository:
    """In-memory repository for testing.

    Stores records in a dict. Implements full DataRepository Protocol.
    """

    def __init__(self) -> None:
        self._records: dict[str, dict[str, Any]] = {}
        self._by_event_id: dict[str, str] = {}  # event_id -> record_id

    async def add(
        self,
        model: str,
        connection_id: str,
        data: dict[str, Any],
    ) -> str:
        """Add record to in-memory store with idempotency check."""
        record_id = str(uuid4())
        event_id = data.get("event_id")

        # Idempotency: skip if event_id already exists
        if event_id is not None and event_id in self._by_event_id:
            return record_id  # Return new ID but don't store

        # Store record
        self._records[record_id] = {
            "model": model,
            "connection_id": connection_id,
            "data": data,
        }

        # Track event_id for idempotency
        if event_id is not None:
            self._by_event_id[event_id] = record_id

        return record_id

    async def get(
        self,
        model: str,
        record_id: str,
    ) -> dict[str, Any] | None:
        """Retrieve record by ID if model matches."""
        record = self._records.get(record_id)
        if record is None or record["model"] != model:
            return None
        return record["data"]

    async def query(
        self,
        model: str,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Query records with optional filters.

        Simple in-memory implementation for testing.
        """
        results: list[dict[str, Any]] = []
        for record in self._records.values():
            if record["model"] != model:
                continue

            # Apply filters if provided
            if filters:
                data = record["data"]
                if not all(data.get(k) == v for k, v in filters.items()):
                    continue

            results.append(record["data"])

            if len(results) >= limit:
                break

        return results
