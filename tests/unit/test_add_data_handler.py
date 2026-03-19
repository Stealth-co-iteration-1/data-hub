"""Unit tests for AddDataHandler."""
import pytest

from src.kernel.commands import AddDataCommand
from src.kernel.domain import CorrelationContext
from src.kernel.events import DataAddedEvent
from src.kernel.exceptions import SchemaNotFoundError, ValidationError
from src.kernel.handlers import AddDataHandler

from .fakes import FakeDataRepository, FakeEventPublisher, FakeSchemaRegistry


class TestAddDataHandler:
    """Tests for AddDataHandler."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.repository = FakeDataRepository()
        self.event_publisher = FakeEventPublisher()
        self.schema_registry = FakeSchemaRegistry()

        self.handler = AddDataHandler(
            repository=self.repository,
            event_publisher=self.event_publisher,
            schema_registry=self.schema_registry,
        )

    @pytest.mark.asyncio
    async def test_handle_validates_and_persists_data(self) -> None:
        """Handler should validate data and persist it."""
        command = AddDataCommand(
            model="contacts",
            connection_id="integration_123",
            schema_name="contact",
            raw_data={"name": "Alice", "email": "alice@example.com"},
        )

        event = await self.handler.handle(command)

        # Should have persisted
        assert len(self.repository.add_calls) == 1
        model, connection_id, data = self.repository.add_calls[0]
        assert model == "contacts"
        assert connection_id == "integration_123"
        assert data["name"] == "Alice"

    @pytest.mark.asyncio
    async def test_handle_publishes_event(self) -> None:
        """Handler should publish DataAddedEvent."""
        command = AddDataCommand(
            model="contacts",
            connection_id="integration_123",
            schema_name="contact",
            raw_data={"name": "Bob", "email": "bob@example.com"},
        )

        await self.handler.handle(command)

        assert len(self.event_publisher.published_events) == 1
        event = self.event_publisher.published_events[0]
        assert isinstance(event, DataAddedEvent)
        assert event.model == "contacts"
        assert event.connection_id == "integration_123"

    @pytest.mark.asyncio
    async def test_handle_returns_event_with_metadata(self) -> None:
        """Handler should return event with correct metadata."""
        command = AddDataCommand(
            model="products",
            connection_id="shop_456",
            schema_name="product",
            raw_data={"sku": "ABC", "price": 99.99, "quantity": 10},
        )

        event = await self.handler.handle(command)

        assert event.model == "products"
        assert event.connection_id == "shop_456"
        assert event.record_metadata.schema_name == "product"
        assert event.record_id is not None  # Should have generated ID

    @pytest.mark.asyncio
    async def test_handle_preserves_correlation_id(self) -> None:
        """Handler should preserve correlation ID from command to event."""
        correlation = CorrelationContext()
        command = AddDataCommand(
            model="contacts",
            connection_id="test",
            schema_name="contact",
            raw_data={"name": "Charlie", "email": "charlie@example.com"},
            correlation=correlation,
        )

        event = await self.handler.handle(command)

        assert event.correlation_id == correlation.correlation_id

    @pytest.mark.asyncio
    async def test_handle_raises_on_invalid_data(self) -> None:
        """Handler should raise ValidationError for invalid data."""
        command = AddDataCommand(
            model="contacts",
            connection_id="test",
            schema_name="contact",
            raw_data={"name": "Diana"},  # missing email
        )

        with pytest.raises(ValidationError) as exc_info:
            await self.handler.handle(command)

        assert exc_info.value.schema_name == "contact"

    @pytest.mark.asyncio
    async def test_handle_raises_on_unknown_schema(self) -> None:
        """Handler should raise SchemaNotFoundError for unknown schema."""
        command = AddDataCommand(
            model="widgets",
            connection_id="test",
            schema_name="nonexistent_schema",
            raw_data={"foo": "bar"},
        )

        with pytest.raises(SchemaNotFoundError) as exc_info:
            await self.handler.handle(command)

        assert exc_info.value.schema_name == "nonexistent_schema"

    @pytest.mark.asyncio
    async def test_handle_does_not_persist_on_validation_failure(self) -> None:
        """Handler should not persist data if validation fails."""
        command = AddDataCommand(
            model="contacts",
            connection_id="test",
            schema_name="contact",
            raw_data={"invalid": "data"},  # missing required fields
        )

        with pytest.raises(ValidationError):
            await self.handler.handle(command)

        # Should not have persisted anything
        assert len(self.repository.add_calls) == 0

    @pytest.mark.asyncio
    async def test_handle_does_not_publish_on_validation_failure(self) -> None:
        """Handler should not publish event if validation fails."""
        command = AddDataCommand(
            model="contacts",
            connection_id="test",
            schema_name="contact",
            raw_data={"invalid": "data"},
        )

        with pytest.raises(ValidationError):
            await self.handler.handle(command)

        # Should not have published anything
        assert len(self.event_publisher.published_events) == 0

    @pytest.mark.asyncio
    async def test_handle_preserves_extra_fields(self) -> None:
        """Handler should preserve extra fields in persisted data."""
        command = AddDataCommand(
            model="contacts",
            connection_id="test",
            schema_name="contact",
            raw_data={
                "name": "Eve",
                "email": "eve@example.com",
                "custom_field": "should_be_preserved",
            },
        )

        await self.handler.handle(command)

        _, _, data = self.repository.add_calls[0]
        assert data["custom_field"] == "should_be_preserved"
