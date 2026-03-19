"""AddDataCommand - state-changing operation for data ingestion.

This command represents the user's intention to add validated data.
It contains all information needed for schema validation and persistence.
"""
from dataclasses import dataclass, field
from typing import Any

from ..domain.models import CorrelationContext


@dataclass
class AddDataCommand:
    """Command to add validated data.

    The kernel validates data against the schema before persistence.
    Extra fields beyond the schema are allowed and preserved.

    Attributes:
        model: Model name (e.g., 'hubspot_contact')
        connection_id: Nango connection ID
        schema_name: Logical schema name for validation (e.g., 'hubspot_contact')
        raw_data: Data to validate and persist (JSON-serializable dict)
        correlation: Observability context for tracing
    """

    model: str
    """Model name for persistence (e.g., 'hubspot_contact')"""

    connection_id: str
    """Nango connection ID"""

    schema_name: str
    """Logical schema name used for validation lookup"""

    raw_data: dict[str, Any]
    """Raw data payload to validate and persist (extra fields allowed)"""

    correlation: CorrelationContext = field(default_factory=CorrelationContext)
    """Observability context with correlation ID and timestamp"""
