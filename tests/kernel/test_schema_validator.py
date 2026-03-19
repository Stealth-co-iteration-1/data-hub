"""Tests for SchemaValidator service.

TDD tests for schema validation using the SchemaRegistry port.
"""
import pytest
from pydantic import BaseModel, ConfigDict

from src.kernel.domain.validation import ValidationResult
from src.kernel.exceptions import SchemaNotFoundError, ValidationError
from src.kernel.validators import SchemaValidator


class MockRegistry:
    """Mock schema registry for testing."""

    def get_schema(self, schema_name: str):
        """Return test schemas."""
        if schema_name == "test_contact":

            class TestContactSchema(BaseModel):
                model_config = ConfigDict(extra="allow")

                name: str
                age: int
                email: str | None = None

            return TestContactSchema

        if schema_name == "test_strict":

            class TestStrictSchema(BaseModel):
                model_config = ConfigDict(extra="allow")

                required_field: str

            return TestStrictSchema

        return None


def test_validate_with_unknown_schema_raises_schema_not_found_error():
    """Test 1: validate() with unknown schema raises SchemaNotFoundError."""
    registry = MockRegistry()
    validator = SchemaValidator(registry)

    with pytest.raises(SchemaNotFoundError) as exc_info:
        validator.validate("unknown_schema", {})

    assert exc_info.value.schema_name == "unknown_schema"


def test_validate_with_valid_data_returns_success():
    """Test 2: validate() with valid data returns ValidationResult.is_valid=True with validated_data."""
    registry = MockRegistry()
    validator = SchemaValidator(registry)

    result = validator.validate(
        "test_contact", {"name": "Alice", "age": 30, "email": "alice@example.com"}
    )

    assert isinstance(result, ValidationResult)
    assert result.is_valid is True
    assert result.validated_data["name"] == "Alice"
    assert result.validated_data["age"] == 30
    assert result.validated_data["email"] == "alice@example.com"
    assert len(result.errors) == 0


def test_validate_with_type_mismatch_returns_failure_with_field_error():
    """Test 3: validate() with type mismatch returns ValidationResult with FieldError containing field_path."""
    registry = MockRegistry()
    validator = SchemaValidator(registry)

    result = validator.validate("test_contact", {"name": "Bob", "age": "not-an-int"})

    assert result.is_valid is False
    assert len(result.errors) > 0
    assert result.errors[0].field_path == "age"
    assert "int" in result.errors[0].message.lower() or result.errors[0].expected == "integer"
    assert result.validated_data == {}


def test_validate_with_missing_required_field_returns_failure():
    """Test 4: validate() with missing required field returns ValidationResult with FieldError."""
    registry = MockRegistry()
    validator = SchemaValidator(registry)

    result = validator.validate("test_contact", {"name": "Charlie"})  # missing age

    assert result.is_valid is False
    assert len(result.errors) > 0
    # Find the error for the age field
    age_errors = [e for e in result.errors if e.field_path == "age"]
    assert len(age_errors) > 0
    assert "required" in age_errors[0].message.lower() or age_errors[0].expected == "required field"


def test_validate_with_extra_fields_preserves_them():
    """Test 5: validate() with extra fields preserves them in validated_data (extra='allow')."""
    registry = MockRegistry()
    validator = SchemaValidator(registry)

    result = validator.validate(
        "test_contact",
        {
            "name": "Dave",
            "age": 40,
            "extra_field": "should be kept",
            "another_extra": 123,
        },
    )

    assert result.is_valid is True
    assert result.validated_data["extra_field"] == "should be kept"
    assert result.validated_data["another_extra"] == 123


def test_validate_or_raise_raises_validation_error_on_failure():
    """Test 6: validate_or_raise() raises ValidationError when validation fails."""
    registry = MockRegistry()
    validator = SchemaValidator(registry)

    with pytest.raises(ValidationError) as exc_info:
        validator.validate_or_raise("test_contact", {"name": "Eve", "age": "invalid"})

    assert exc_info.value.schema_name == "test_contact"
    assert len(exc_info.value.errors) > 0


def test_validate_or_raise_returns_validated_data_on_success():
    """Test 7: validate_or_raise() returns validated data when validation succeeds."""
    registry = MockRegistry()
    validator = SchemaValidator(registry)

    validated_data = validator.validate_or_raise(
        "test_contact", {"name": "Frank", "age": 50, "extra": "preserved"}
    )

    assert validated_data["name"] == "Frank"
    assert validated_data["age"] == 50
    assert validated_data["extra"] == "preserved"
