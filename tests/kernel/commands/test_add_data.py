"""Tests for AddDataCommand."""
import dataclasses

import pytest

from src.kernel.commands import AddDataCommand
from src.kernel.domain import CorrelationContext


def test_add_data_command_has_required_fields():
    """Test 1: AddDataCommand has required fields: model, connection_id, schema_name, raw_data."""
    # Should be able to create command with all required fields
    cmd = AddDataCommand(
        model="test_model",
        connection_id="test_connection",
        schema_name="test_schema",
        raw_data={"key": "value"},
    )

    assert cmd.model == "test_model"
    assert cmd.connection_id == "test_connection"
    assert cmd.schema_name == "test_schema"
    assert cmd.raw_data == {"key": "value"}


def test_add_data_command_has_correlation_context_with_default():
    """Test 2: AddDataCommand has optional correlation_context with default."""
    # Create without explicit correlation context
    cmd = AddDataCommand(
        model="test_model",
        connection_id="test_connection",
        schema_name="test_schema",
        raw_data={},
    )

    # Should have a default CorrelationContext
    assert isinstance(cmd.correlation, CorrelationContext)
    assert cmd.correlation.correlation_id is not None
    assert cmd.correlation.timestamp is not None


def test_add_data_command_is_dataclass():
    """Test 3: AddDataCommand is a dataclass (frozen=False to allow construction)."""
    assert dataclasses.is_dataclass(AddDataCommand)
    # frozen=False means we can modify (though we shouldn't in practice)
    cmd = AddDataCommand(
        model="test_model",
        connection_id="test_connection",
        schema_name="test_schema",
        raw_data={},
    )
    # Should not raise an error (not frozen)
    cmd.model = "new_model"  # This should work since it's not frozen


def test_add_data_command_raw_data_accepts_dict():
    """Test 4: raw_data accepts Dict[str, Any]."""
    complex_data = {
        "string": "value",
        "number": 42,
        "nested": {"key": "value"},
        "list": [1, 2, 3],
        "null": None,
    }

    cmd = AddDataCommand(
        model="test_model",
        connection_id="test_connection",
        schema_name="test_schema",
        raw_data=complex_data,
    )

    assert cmd.raw_data == complex_data


def test_add_data_command_minimal_instantiation():
    """Test 5: Can instantiate with minimal args."""
    cmd = AddDataCommand(
        model="m",
        connection_id="c",
        schema_name="n",
        raw_data={},
    )

    assert cmd.model == "m"
    assert cmd.connection_id == "c"
    assert cmd.schema_name == "n"
    assert cmd.raw_data == {}
    assert isinstance(cmd.correlation, CorrelationContext)
