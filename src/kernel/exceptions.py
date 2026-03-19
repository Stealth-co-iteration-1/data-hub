"""Domain-specific exceptions for the kernel.

These exceptions represent business rule violations and domain errors.
They contain structured data for debugging and error reporting.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FieldError:
    """Detailed error information for a single field."""

    field_path: str
    """Path to the field (e.g., 'contact.email', 'items[0].price')"""

    message: str
    """Human-readable error message"""

    expected: Any = None
    """Expected value or type (optional)"""

    actual: Any = None
    """Actual value received (optional)"""


class KernelError(Exception):
    """Base exception for all kernel errors."""

    pass


@dataclass
class ValidationError(KernelError):
    """Raised when data fails schema validation.

    Contains structured error information for each invalid field.
    Downstream systems can process these programmatically.
    """

    schema_name: str
    """The schema that was used for validation"""

    errors: list[FieldError] = field(default_factory=list)
    """List of field-level validation errors"""

    def __str__(self) -> str:
        error_count = len(self.errors)
        if error_count == 0:
            return f"Validation failed for schema '{self.schema_name}'"
        field_names = ", ".join(e.field_path for e in self.errors[:3])
        suffix = f" and {error_count - 3} more" if error_count > 3 else ""
        return f"Validation failed for schema '{self.schema_name}': {field_names}{suffix}"


class SchemaNotFoundError(KernelError):
    """Raised when a schema cannot be found in the registry."""

    def __init__(self, schema_name: str) -> None:
        self.schema_name = schema_name
        super().__init__(f"Schema not found: '{schema_name}'")
