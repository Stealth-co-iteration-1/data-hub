"""Domain models and value objects.

Pure Python dataclasses with no external dependencies.
These represent core domain concepts used across commands and events.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


def _utc_now() -> datetime:
    """Return current UTC timestamp."""
    return datetime.now(timezone.utc)


def _new_uuid() -> UUID:
    """Generate a new UUID v4."""
    return uuid4()


@dataclass(frozen=True)
class RecordMetadata:
    """Metadata for a persisted data record.

    Immutable value object containing record identification and audit info.
    """

    record_id: str
    """Unique identifier assigned by the repository"""

    model: str
    """Model name (e.g., 'hubspot_contact')"""

    connection_id: str
    """Nango connection ID"""

    schema_name: str
    """Schema used for validation"""

    created_at: datetime = field(default_factory=_utc_now)
    """When the record was created (UTC)"""


@dataclass(frozen=True)
class CorrelationContext:
    """Observability context for request tracing.

    Passed through the system to enable distributed tracing.
    """

    correlation_id: UUID = field(default_factory=_new_uuid)
    """Unique identifier for tracing a request across systems"""

    timestamp: datetime = field(default_factory=_utc_now)
    """When the operation was initiated (UTC)"""

    source: str | None = None
    """Optional source system identifier"""
