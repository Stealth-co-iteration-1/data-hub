"""DataAddedEvent - domain event emitted after successful data addition.

Events are emitted after state changes succeed. They enable
loose coupling between features (other handlers can react to events).
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID

from ..domain.models import RecordMetadata


def _utc_now() -> datetime:
    """Return current UTC timestamp."""
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class DataAddedEvent:
    """Event emitted when data is successfully added.

    Contains metadata about the created record for downstream processing.
    Immutable to prevent modification after emission.

    Attributes:
        record_metadata: Details about the persisted record
        correlation_id: Trace ID linking to the originating command
        occurred_at: When this event was created (UTC)
    """

    record_metadata: RecordMetadata
    """Metadata about the created record"""

    correlation_id: UUID
    """Correlation ID from the originating command for tracing"""

    occurred_at: datetime = field(default_factory=_utc_now)
    """When this event occurred (UTC timestamp)"""

    @property
    def record_id(self) -> str:
        """Convenience accessor for the record ID."""
        return self.record_metadata.record_id

    @property
    def model(self) -> str:
        """Convenience accessor for the model name."""
        return self.record_metadata.model

    @property
    def connection_id(self) -> str:
        """Convenience accessor for the connection ID."""
        return self.record_metadata.connection_id
