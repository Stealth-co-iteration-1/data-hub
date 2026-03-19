"""Permissive schema registry for v1 webhook processing.

Returns a permissive (allow-all) schema for any model name.
Phase 4 will introduce proper schema validation with field enforcement.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict


class _PermissiveModel(BaseModel):
    """Pydantic model that accepts any fields without strict validation.

    Used as a pass-through for v1 where schema enforcement is not yet implemented.
    All fields are preserved via extra="allow".
    """

    model_config = ConfigDict(extra="allow")


class PermissiveSchemaRegistry:
    """Schema registry that returns a permissive schema for any model name.

    For v1, all webhook data is accepted regardless of schema.
    Phase 4 will replace this with strict schema enforcement.
    """

    def get_schema(self, schema_name: str) -> type[BaseModel] | None:
        """Return a permissive schema for any model name.

        Args:
            schema_name: The schema to look up (ignored in v1)

        Returns:
            A permissive Pydantic model that accepts any data
        """
        # Return the permissive model class regardless of schema name
        # This allows all webhook data through for v1
        _: Any = schema_name  # Explicitly unused in v1
        return _PermissiveModel
