"""QueryData - read operation for querying stored records.

This query represents the user's intention to retrieve filtered data.
Queries are read-only operations - they do not modify state.
"""
from dataclasses import dataclass, field
from typing import Any

from ..domain.models import CorrelationContext

# Unconditional limit cap - QURY-03
DEFAULT_QUERY_LIMIT = 100
MAX_QUERY_LIMIT = 1000


@dataclass
class QueryData:
    """Query to retrieve filtered records.

    Queries are CQRS reads - they return data but do not emit events.
    The limit is capped unconditionally at MAX_QUERY_LIMIT.

    NOTE: Offset-based pagination is deferred. The port signature does not
    include offset parameter - future phase will add cursor-based pagination.

    Attributes:
        model: Model name to query (e.g., 'hubspot_contact')
        filters: Optional equality filter conditions (connection_id only for v1)
        limit: Max records to return (capped at MAX_QUERY_LIMIT)
        correlation: Observability context for tracing
    """

    model: str
    """Model name to query (e.g., 'hubspot_contact')"""

    filters: dict[str, Any] | None = None
    """Optional equality filters. V1: connection_id only (no JSON field filtering)."""

    limit: int = DEFAULT_QUERY_LIMIT
    """Max records to return (capped at MAX_QUERY_LIMIT)"""

    correlation: CorrelationContext = field(default_factory=CorrelationContext)
    """Observability context with correlation ID and timestamp"""
