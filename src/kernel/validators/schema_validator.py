"""Schema validation service.

Uses the SchemaRegistry port to look up schemas and Pydantic for validation.
This is the only place in the kernel where Pydantic is imported.

IMPORTANT: Uses Pydantic's model_validate() for validation, which runs in
compiled Rust. DO NOT add custom @field_validator decorators here - they
run in Python and are 10-100x slower.
"""
from typing import Any

from pydantic import ValidationError as PydanticValidationError

from ..domain.validation import ValidationResult
from ..exceptions import FieldError, SchemaNotFoundError
from ..exceptions import ValidationError as KernelValidationError
from ..ports.schema_registry import SchemaRegistry


class SchemaValidator:
    """Validates data against schemas from the registry.

    Uses dependency injection - receives SchemaRegistry port, not concrete implementation.
    """

    def __init__(self, registry: SchemaRegistry) -> None:
        """Initialize with a schema registry.

        Args:
            registry: Port for looking up schemas by name
        """
        self._registry = registry

    def validate(self, schema_name: str, data: dict[str, Any]) -> ValidationResult:
        """Validate data against a named schema.

        Args:
            schema_name: Logical schema name (e.g., 'hubspot_contact')
            data: Raw data to validate

        Returns:
            ValidationResult with is_valid, validated_data, and errors

        Raises:
            SchemaNotFoundError: If schema_name is not in the registry
        """
        schema = self._registry.get_schema(schema_name)
        if schema is None:
            raise SchemaNotFoundError(schema_name)

        try:
            # Use Pydantic's model_validate - runs in compiled Rust
            # Extra fields are allowed by default (ConfigDict(extra='allow'))
            validated = schema.model_validate(data)

            # Convert Pydantic model to dict, preserving extra fields
            validated_dict = validated.model_dump()

            return ValidationResult.success(validated_dict)

        except PydanticValidationError as e:
            errors = self._convert_pydantic_errors(e)
            return ValidationResult.failure(errors)

    def validate_or_raise(
        self, schema_name: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Validate data and raise if invalid.

        Convenience method that raises KernelValidationError on failure.

        Args:
            schema_name: Logical schema name
            data: Raw data to validate

        Returns:
            Validated data dict on success

        Raises:
            SchemaNotFoundError: If schema not found
            ValidationError: If validation fails
        """
        result = self.validate(schema_name, data)

        if not result.is_valid:
            raise KernelValidationError(
                schema_name=schema_name,
                errors=list(result.errors),
            )

        return result.validated_data

    def _convert_pydantic_errors(
        self, pydantic_error: PydanticValidationError
    ) -> list[FieldError]:
        """Convert Pydantic validation errors to kernel FieldError format.

        Extracts field path, message, expected type, and actual value.
        """
        errors: list[FieldError] = []

        for error in pydantic_error.errors():
            # Build field path from loc tuple (e.g., ('contact', 'email') -> 'contact.email')
            loc = error.get("loc", ())
            field_path = ".".join(str(part) for part in loc) if loc else "root"

            # Get message and context
            message = error.get("msg", "Validation error")

            # Extract expected type from error type (e.g., 'string_type' -> 'string')
            error_type = error.get("type", "")
            expected = self._extract_expected_type(error_type, error.get("ctx", {}))

            # Get actual value from input if available
            actual = error.get("input")

            errors.append(
                FieldError(
                    field_path=field_path,
                    message=message,
                    expected=expected,
                    actual=actual,
                )
            )

        return errors

    def _extract_expected_type(self, error_type: str, ctx: dict[str, Any]) -> Any:
        """Extract expected type/value from Pydantic error context.

        Maps Pydantic error types to human-readable expected values.
        """
        # Map common error types to expected descriptions
        type_mapping = {
            "string_type": "string",
            "int_type": "integer",
            "float_type": "number",
            "bool_type": "boolean",
            "list_type": "array",
            "dict_type": "object",
            "missing": "required field",
            "none_not_allowed": "non-null value",
        }

        if error_type in type_mapping:
            return type_mapping[error_type]

        # Check context for more specific info
        if "expected" in ctx:
            return ctx["expected"]

        return error_type
