"""Events - domain events emitted after state changes.

Events signal that something happened in the system.
Other parts of the system can react to events without
tight coupling to the command handlers.
"""
from .data_added import DataAddedEvent

__all__ = ["DataAddedEvent"]
