"""Validation result types.

Value objects representing the outcome of schema validation.
"""
from dataclasses import dataclass, field
from typing import Any

from ..exceptions import FieldError


@dataclass(frozen=True)
class ValidationResult:
    """Result of validating data against a schema.

    Either contains validated data (success) or errors (failure).
    Extra fields not in the schema are preserved in validated_data.
    """

    is_valid: bool
    """Whether validation succeeded"""

    validated_data: dict[str, Any] = field(default_factory=dict)
    """The validated data (may include extra fields). Empty on failure."""

    errors: tuple[FieldError, ...] = field(default_factory=tuple)
    """Validation errors. Empty on success."""

    @classmethod
    def success(cls, data: dict[str, Any]) -> "ValidationResult":
        """Create a successful validation result."""
        return cls(is_valid=True, validated_data=data, errors=())

    @classmethod
    def failure(cls, errors: list[FieldError]) -> "ValidationResult":
        """Create a failed validation result."""
        return cls(is_valid=False, validated_data={}, errors=tuple(errors))
