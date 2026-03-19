"""Unit tests for InMemoryEventPublisher adapter."""
import pytest

from src.adapters.driven.event_bus import InMemoryEventPublisher
from src.kernel.ports.event_publisher import EventPublisher


class TestInMemoryEventPublisher:
    """Tests for InMemoryEventPublisher implementation."""

    def test_implements_event_publisher_protocol(self):
        """InMemoryEventPublisher satisfies EventPublisher Protocol."""
        publisher = InMemoryEventPublisher()
        assert isinstance(publisher, EventPublisher)

    async def test_publish_stores_event(self):
        """Published event is stored in events list."""
        publisher = InMemoryEventPublisher()
        event = {"type": "DataAdded", "record_id": "123"}

        await publisher.publish(event)

        assert len(publisher.events) == 1
        assert publisher.events[0] == event

    async def test_publish_multiple_events(self):
        """Multiple events are stored in order."""
        publisher = InMemoryEventPublisher()

        await publisher.publish({"id": 1})
        await publisher.publish({"id": 2})
        await publisher.publish({"id": 3})

        assert len(publisher.events) == 3
        assert [e["id"] for e in publisher.events] == [1, 2, 3]

    def test_clear_removes_all_events(self):
        """clear() empties the events list."""
        publisher = InMemoryEventPublisher()
        publisher.events = [{"a": 1}, {"b": 2}]

        publisher.clear()

        assert publisher.events == []

    async def test_get_events_of_type_filters_correctly(self):
        """get_events_of_type() returns only matching events."""
        publisher = InMemoryEventPublisher()

        class EventA:
            pass

        class EventB:
            pass

        a1 = EventA()
        a2 = EventA()
        b1 = EventB()

        await publisher.publish(a1)
        await publisher.publish(b1)
        await publisher.publish(a2)

        type_a = publisher.get_events_of_type(EventA)
        type_b = publisher.get_events_of_type(EventB)

        assert len(type_a) == 2
        assert len(type_b) == 1
        assert a1 in type_a
        assert a2 in type_a
        assert b1 in type_b
