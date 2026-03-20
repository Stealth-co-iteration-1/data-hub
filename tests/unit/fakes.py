"""Fake implementations of ports for unit testing.

These fakes implement the kernel port protocols without any
infrastructure dependencies. They store data in memory and
record calls for verification.
"""
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict


class FakeDataRepository:
    """In-memory implementation of DataRepository for testing."""

    def __init__(self) -> None:
        self.records: dict[str, dict[str, Any]] = {}
        self.add_calls: list[tuple[str, str, dict[str, Any]]] = []
        self.query_calls: list[tuple[str, dict[str, Any] | None, int]] = []

    async def add(
        self,
        model: str,
        connection_id: str,
        data: dict[str, Any],
    ) -> str:
        """Store data in memory and return a generated ID."""
        record_id = str(uuid4())
        self.records[record_id] = {
            "model": model,
            "connection_id": connection_id,
            "data": data,
        }
        self.add_calls.append((model, connection_id, data))
        return record_id

    async def get(
        self,
        model: str,
        record_id: str,
    ) -> dict[str, Any] | None:
        """Retrieve a record by ID."""
        record = self.records.get(record_id)
        if record and record["model"] == model:
            return record["data"]
        return None

    async def query(
        self,
        model: str,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Query records with optional filters.

        V1: filters supports connection_id only (no JSON field filtering).
        Returns dicts with system fields (id, connection_id, model, created_at) + data.
        """
        self.query_calls.append((model, filters, limit))
        results = []
        for record_id, record in self.records.items():
            if record["model"] != model:
                continue
            # V1: Only filter on connection_id (a real column, not JSON field)
            if filters:
                if "connection_id" in filters:
                    if record.get("connection_id") != filters["connection_id"]:
                        continue
            # Return with system fields per CONTEXT.md decision
            results.append({
                "id": record_id,
                "connection_id": record.get("connection_id", ""),
                "model": record["model"],
                "created_at": record.get("created_at", ""),
                **record["data"],
            })
            if len(results) >= limit:
                break
        return results


class FakeEventPublisher:
    """In-memory implementation of EventPublisher for testing."""

    def __init__(self) -> None:
        self.published_events: list[Any] = []

    async def publish(self, event: Any) -> None:
        """Record the event for later verification."""
        self.published_events.append(event)


class FakeSchemaRegistry:
    """In-memory implementation of SchemaRegistry for testing.

    Pre-populated with test schemas.
    """

    def __init__(self) -> None:
        self.schemas: dict[str, type[BaseModel]] = {}
        # Register default test schemas
        self._register_test_schemas()

    def _register_test_schemas(self) -> None:
        """Register schemas used in tests."""
        # Simple contact schema
        class ContactSchema(BaseModel):
            model_config = ConfigDict(extra="allow")
            name: str
            email: str

        # Schema with more types
        class ProductSchema(BaseModel):
            model_config = ConfigDict(extra="allow")
            sku: str
            price: float
            quantity: int

        self.schemas["contact"] = ContactSchema
        self.schemas["product"] = ProductSchema

    def register(self, name: str, schema: type[BaseModel]) -> None:
        """Register a schema for testing."""
        self.schemas[name] = schema

    def get_schema(self, schema_name: str) -> type[BaseModel] | None:
        """Look up a schema by name."""
        return self.schemas.get(schema_name)
