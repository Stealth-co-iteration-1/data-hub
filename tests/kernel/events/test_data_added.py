"""Tests for DataAddedEvent."""
import dataclasses
from datetime import datetime, timezone
from uuid import UUID

import pytest

from src.kernel.domain import RecordMetadata
from src.kernel.events import DataAddedEvent


def test_data_added_event_has_record_metadata_field():
    """Test 1: DataAddedEvent has record_metadata field of type RecordMetadata."""
    metadata = RecordMetadata(
        record_id="test_id",
        model="test_model",
        connection_id="test_connection",
        schema_name="test_schema",
    )
    correlation_id = UUID("12345678-1234-5678-1234-567812345678")

    event = DataAddedEvent(record_metadata=metadata, correlation_id=correlation_id)

    assert event.record_metadata == metadata
    assert isinstance(event.record_metadata, RecordMetadata)


def test_data_added_event_has_correlation_id_field():
    """Test 2: DataAddedEvent has correlation_id field."""
    metadata = RecordMetadata(
        record_id="test_id",
        model="test_model",
        connection_id="test_connection",
        schema_name="test_schema",
    )
    correlation_id = UUID("12345678-1234-5678-1234-567812345678")

    event = DataAddedEvent(record_metadata=metadata, correlation_id=correlation_id)

    assert event.correlation_id == correlation_id
    assert isinstance(event.correlation_id, UUID)


def test_data_added_event_has_occurred_at_with_utc_default():
    """Test 3: DataAddedEvent has occurred_at timestamp with UTC default."""
    metadata = RecordMetadata(
        record_id="test_id",
        model="test_model",
        connection_id="test_connection",
        schema_name="test_schema",
    )
    correlation_id = UUID("12345678-1234-5678-1234-567812345678")

    before = datetime.now(timezone.utc)
    event = DataAddedEvent(record_metadata=metadata, correlation_id=correlation_id)
    after = datetime.now(timezone.utc)

    assert event.occurred_at is not None
    assert isinstance(event.occurred_at, datetime)
    # Check it has timezone info
    assert event.occurred_at.tzinfo is not None
    # Check it's within a reasonable time window
    assert before <= event.occurred_at <= after


def test_data_added_event_is_immutable():
    """Test 4: DataAddedEvent is immutable (frozen=True)."""
    metadata = RecordMetadata(
        record_id="test_id",
        model="test_model",
        connection_id="test_connection",
        schema_name="test_schema",
    )
    correlation_id = UUID("12345678-1234-5678-1234-567812345678")

    event = DataAddedEvent(record_metadata=metadata, correlation_id=correlation_id)

    # Should be frozen - can't modify
    with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
        event.correlation_id = UUID("87654321-4321-8765-4321-876543218765")


def test_data_added_event_can_construct_from_record_metadata():
    """Test 5: Can construct from RecordMetadata."""
    metadata = RecordMetadata(
        record_id="rec_123",
        model="contacts",
        connection_id="nango_hubspot_456",
        schema_name="hubspot_contact",
    )
    correlation_id = UUID("12345678-1234-5678-1234-567812345678")

    event = DataAddedEvent(record_metadata=metadata, correlation_id=correlation_id)

    # Should have convenience accessors
    assert event.record_id == "rec_123"
    assert event.model == "contacts"
    assert event.connection_id == "nango_hubspot_456"
