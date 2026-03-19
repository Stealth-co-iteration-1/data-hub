"""Unit tests for SchemaValidator."""
import pytest
from pydantic import BaseModel, ConfigDict

from src.kernel.exceptions import SchemaNotFoundError, ValidationError
from src.kernel.validators import SchemaValidator

from .fakes import FakeSchemaRegistry


class TestSchemaValidator:
    """Tests for SchemaValidator."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.registry = FakeSchemaRegistry()
        self.validator = SchemaValidator(self.registry)

    def test_validate_with_valid_data_returns_success(self) -> None:
        """Valid data should return ValidationResult.is_valid=True."""
        result = self.validator.validate(
            "contact",
            {"name": "Alice", "email": "alice@example.com"},
        )

        assert result.is_valid is True
        assert result.validated_data["name"] == "Alice"
        assert result.validated_data["email"] == "alice@example.com"
        assert len(result.errors) == 0

    def test_validate_preserves_extra_fields(self) -> None:
        """Extra fields should be preserved in validated data."""
        result = self.validator.validate(
            "contact",
            {"name": "Bob", "email": "bob@example.com", "phone": "555-1234"},
        )

        assert result.is_valid is True
        assert result.validated_data["phone"] == "555-1234"

    def test_validate_with_type_mismatch_returns_error(self) -> None:
        """Type mismatch should return ValidationResult with errors."""
        # product.price expects float, sending string
        result = self.validator.validate(
            "product",
            {"sku": "ABC123", "price": "not-a-number", "quantity": 10},
        )

        assert result.is_valid is False
        assert len(result.errors) > 0
        # Error should mention the price field
        field_paths = [e.field_path for e in result.errors]
        assert "price" in field_paths

    def test_validate_with_missing_required_field_returns_error(self) -> None:
        """Missing required field should return ValidationResult with errors."""
        result = self.validator.validate(
            "contact",
            {"name": "Charlie"},  # missing email
        )

        assert result.is_valid is False
        assert len(result.errors) > 0
        field_paths = [e.field_path for e in result.errors]
        assert "email" in field_paths

    def test_validate_with_unknown_schema_raises_error(self) -> None:
        """Unknown schema should raise SchemaNotFoundError."""
        with pytest.raises(SchemaNotFoundError) as exc_info:
            self.validator.validate("nonexistent", {"foo": "bar"})

        assert exc_info.value.schema_name == "nonexistent"

    def test_validate_or_raise_returns_data_on_success(self) -> None:
        """validate_or_raise should return validated data on success."""
        data = self.validator.validate_or_raise(
            "contact",
            {"name": "Diana", "email": "diana@example.com"},
        )

        assert data["name"] == "Diana"
        assert data["email"] == "diana@example.com"

    def test_validate_or_raise_raises_on_failure(self) -> None:
        """validate_or_raise should raise ValidationError on failure."""
        with pytest.raises(ValidationError) as exc_info:
            self.validator.validate_or_raise(
                "contact",
                {"name": "Eve"},  # missing email
            )

        error = exc_info.value
        assert error.schema_name == "contact"
        assert len(error.errors) > 0

    def test_error_includes_expected_and_actual(self) -> None:
        """FieldError should include expected type and actual value."""
        result = self.validator.validate(
            "product",
            {"sku": "XYZ", "price": "invalid", "quantity": 5},
        )

        assert result.is_valid is False
        price_error = next(e for e in result.errors if e.field_path == "price")
        assert price_error.actual == "invalid"
        # expected should indicate numeric type
        assert price_error.expected is not None
