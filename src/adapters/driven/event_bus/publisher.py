"""In-memory event publisher adapter.

Simple implementation that stores events in memory.
Suitable for Phase 2 testing and single-process deployments.
Phase 3 may augment with structured logging output.
"""
from typing import Any


class InMemoryEventPublisher:
    """In-memory implementation of EventPublisher port.

    Stores published events in a list for later inspection.
    Useful for testing and simple deployments.
    """

    def __init__(self) -> None:
        """Initialize with empty event list."""
        self.events: list[Any] = []

    async def publish(self, event: Any) -> None:
        """Store event in memory.

        Args:
            event: Domain event to publish (e.g., DataAddedEvent)
        """
        self.events.append(event)

    def clear(self) -> None:
        """Clear all stored events.

        Useful in tests between test cases.
        """
        self.events.clear()

    def get_events_of_type(self, event_type: type) -> list[Any]:
        """Get all events of a specific type.

        Args:
            event_type: Type to filter by (e.g., DataAddedEvent)

        Returns:
            List of events matching the type
        """
        return [e for e in self.events if isinstance(e, event_type)]
