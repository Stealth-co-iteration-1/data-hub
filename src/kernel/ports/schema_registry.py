"""Schema registry port for schema lookup."""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class SchemaRegistry(Protocol):
    """Port interface for schema lookup.

    Adapters implement this to provide schema definitions.
    The kernel uses logical schema names (e.g., 'hubspot_contact')
    and the adapter resolves them to actual validators.
    """

    def get_schema(self, schema_name: str) -> Any | None:
        """Look up a schema by logical name.

        Args:
            schema_name: Logical schema name (e.g., 'hubspot_contact')

        Returns:
            A Pydantic model class or None if not found.
            The returned class must be usable for validation.
        """
        ...
