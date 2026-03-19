"""Port interfaces for the kernel.

Ports define contracts between the kernel and external systems.
They are abstract interfaces (Protocols) with no concrete implementation.
"""

from .event_publisher import EventPublisher
from .repository import DataRepository
from .schema_registry import SchemaRegistry

__all__ = ["DataRepository", "EventPublisher", "SchemaRegistry"]
