"""Kernel module - pure business logic with zero external dependencies.

This module contains:
- Commands: State-changing operations (AddDataCommand)
- Queries: Read-only operations (QueryData)
- Events: Domain events (DataAddedEvent)
- Handlers: Command/query handlers (AddDataHandler, QueryHandler)
- Ports: Abstract interfaces for adapters
- Exceptions: Domain-specific errors

The kernel has NO imports from infrastructure libraries
(SQLAlchemy, FastAPI, asyncpg, etc.)
"""
from .commands import AddDataCommand
from .domain import CorrelationContext, RecordMetadata, ValidationResult
from .events import DataAddedEvent
from .exceptions import (
    FieldError,
    KernelError,
    SchemaNotFoundError,
    ValidationError,
)
from .handlers import AddDataHandler, QueryHandler
from .ports import DataRepository, EventPublisher, SchemaRegistry
from .queries import DEFAULT_QUERY_LIMIT, MAX_QUERY_LIMIT, QueryData
from .validators import SchemaValidator

__all__ = [
    # Commands
    "AddDataCommand",
    # Queries
    "QueryData",
    "DEFAULT_QUERY_LIMIT",
    "MAX_QUERY_LIMIT",
    # Events
    "DataAddedEvent",
    # Handlers
    "AddDataHandler",
    "QueryHandler",
    # Domain
    "CorrelationContext",
    "RecordMetadata",
    "ValidationResult",
    # Ports
    "DataRepository",
    "EventPublisher",
    "SchemaRegistry",
    # Validators
    "SchemaValidator",
    # Exceptions
    "FieldError",
    "KernelError",
    "SchemaNotFoundError",
    "ValidationError",
]
