"""Event publisher port for domain events."""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class EventPublisher(Protocol):
    """Port interface for publishing domain events.

    Driven adapters (e.g., in-memory bus, message queue) implement this protocol.
    """

    async def publish(self, event: Any) -> None:
        """Publish a domain event.

        Args:
            event: Domain event to publish (e.g., DataAddedEvent)
        """
        ...
