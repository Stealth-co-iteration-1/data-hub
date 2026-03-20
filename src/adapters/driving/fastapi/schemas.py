"""Pydantic schemas for FastAPI request/response models."""

from typing import Any

from pydantic import BaseModel, ConfigDict


class WebhookResponse(BaseModel):
    """Standard webhook response."""

    status: str


class ErrorResponse(BaseModel):
    """Error response for 4xx/5xx."""

    error: str


class QueryRequest(BaseModel):
    """Request body for query endpoint.

    Simple equality filters only - no operators for v1.
    V1: Only connection_id filter is effective (no JSON field filtering).
    Offset deferred to future phase with cursor-based pagination.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "filters": {"connection_id": "abc123"},
                "limit": 50,
            }
        }
    )

    filters: dict[str, str] | None = None
    """Optional equality filters. V1: Only {"connection_id": "..."} is effective."""

    limit: int = 100
    """Max records to return. Default 100, max 1000."""

    # NOTE: No offset field - deferred to future phase per CONTEXT.md


class QueryResponse(BaseModel):
    """Paginated envelope response for query endpoint.

    Per CONTEXT.md: {"data": [...], "count": N, "limit": N, "has_more": bool}
    Note: offset removed (deferred), has_more detection limited at MAX_QUERY_LIMIT.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "data": [
                    {
                        "id": "abc-123",
                        "connection_id": "conn1",
                        "model": "contacts",
                        "created_at": "2026-03-19T10:30:00Z",
                        "name": "Alice",
                        "email": "alice@example.com",
                    }
                ],
                "count": 1,
                "limit": 100,
                "has_more": False,
            }
        }
    )

    data: list[dict[str, Any]]
    """List of matching records with system fields (id, connection_id, model, created_at) + payload"""

    count: int
    """Number of records in this response"""

    limit: int
    """Limit used for this query"""

    has_more: bool
    """True if more records exist beyond current page.
    NOTE: At MAX_QUERY_LIMIT (1000), has_more may be False even if more records exist
    (known limitation - the +1 detection trick doesn't work at the cap boundary)."""


class ProblemDetail(BaseModel):
    """RFC 7807 Problem Details error response."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "urn:data-hub:error:invalid-model",
                "title": "Invalid Model Name",
                "status": 400,
                "detail": "Model name 'INVALID!' contains disallowed characters",
            }
        }
    )

    type: str = "about:blank"
    """URI reference identifying the problem type"""

    title: str
    """Short human-readable summary"""

    status: int
    """HTTP status code"""

    detail: str
    """Human-readable explanation specific to this occurrence"""
