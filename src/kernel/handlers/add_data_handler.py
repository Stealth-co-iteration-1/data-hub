"""AddDataHandler - processes AddDataCommand.

Orchestrates the complete data addition workflow:
1. Validate data against schema
2. Persist validated data via repository
3. Emit DataAddedEvent via event publisher
"""
from ..commands.add_data import AddDataCommand
from ..domain.models import RecordMetadata
from ..events.data_added import DataAddedEvent
from ..ports.event_publisher import EventPublisher
from ..ports.repository import DataRepository
from ..ports.schema_registry import SchemaRegistry
from ..validators.schema_validator import SchemaValidator


class AddDataHandler:
    """Handler for AddDataCommand.

    Uses dependency injection - receives ports, not concrete implementations.
    The kernel never knows about PostgreSQL, FastAPI, etc.
    """

    def __init__(
        self,
        repository: DataRepository,
        event_publisher: EventPublisher,
        schema_registry: SchemaRegistry,
    ) -> None:
        """Initialize with port implementations.

        Args:
            repository: Port for data persistence
            event_publisher: Port for publishing domain events
            schema_registry: Port for looking up schemas
        """
        self._repository = repository
        self._event_publisher = event_publisher
        self._validator = SchemaValidator(schema_registry)

    async def handle(self, command: AddDataCommand) -> DataAddedEvent:
        """Process an AddDataCommand.

        Validates data, persists it, and emits an event.

        Args:
            command: The command containing data to add

        Returns:
            DataAddedEvent with record metadata

        Raises:
            SchemaNotFoundError: If schema_name is not in the registry
            ValidationError: If data fails validation
        """
        # Step 1: Validate data against schema
        # Raises ValidationError or SchemaNotFoundError on failure
        validated_data = self._validator.validate_or_raise(
            command.schema_name,
            command.raw_data,
        )

        # Step 2: Persist validated data via repository
        record_id = await self._repository.add(
            model=command.model,
            connection_id=command.connection_id,
            data=validated_data,
        )

        # Step 3: Create record metadata
        metadata = RecordMetadata(
            record_id=record_id,
            model=command.model,
            connection_id=command.connection_id,
            schema_name=command.schema_name,
        )

        # Step 4: Create and publish event
        event = DataAddedEvent(
            record_metadata=metadata,
            correlation_id=command.correlation.correlation_id,
        )

        await self._event_publisher.publish(event)

        return event
