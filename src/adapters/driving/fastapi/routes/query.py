"""Query endpoint for retrieving stored records.

POST /query/{model} with structured filter parameters.
Implements injection prevention via model name allowlist and filter value size limits.
"""
import re
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from src.kernel.domain.models import CorrelationContext
from src.kernel.handlers.query_handler import QueryHandler
from src.kernel.queries.query_data import DEFAULT_QUERY_LIMIT, MAX_QUERY_LIMIT, QueryData
from src.observability.logging import get_logger

from ..dependencies import get_query_handler
from ..schemas import ProblemDetail, QueryRequest, QueryResponse

router = APIRouter(tags=["query"])
logger = get_logger(__name__)

# Security guardrails per CONTEXT.md
MODEL_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
MAX_FILTER_VALUE_LENGTH = 256


def _validate_model_name(model: str) -> ProblemDetail | None:
    """Validate model name against allowlist pattern.

    Returns ProblemDetail if invalid, None if valid.
    """
    if not MODEL_NAME_PATTERN.match(model):
        return ProblemDetail(
            type="urn:data-hub:error:invalid-model",
            title="Invalid Model Name",
            status=400,
            detail=f"Model name '{model}' must start with lowercase letter and contain only a-z, 0-9, underscore",
        )
    return None


def _validate_filter_values(filters: dict[str, str] | None) -> ProblemDetail | None:
    """Validate filter values are within size limits.

    Returns ProblemDetail if invalid, None if valid.
    """
    if filters is None:
        return None
    for key, value in filters.items():
        if len(value) > MAX_FILTER_VALUE_LENGTH:
            return ProblemDetail(
                type="urn:data-hub:error:filter-value-too-long",
                title="Filter Value Too Long",
                status=400,
                detail=f"Filter value for '{key}' exceeds {MAX_FILTER_VALUE_LENGTH} character limit",
            )
    return None


@router.post(
    "/query/{model}",
    response_model=QueryResponse,
    responses={
        400: {"model": ProblemDetail, "description": "Invalid request"},
    },
)
async def query_records(
    model: str,
    request: Request,
    body: QueryRequest,
    handler: QueryHandler = Depends(get_query_handler),
) -> QueryResponse | JSONResponse:
    """Query records for a model with optional filters.

    Security guardrails:
    - Model name validated via regex allowlist (no injection via path param)
    - Filter values capped at 256 chars
    - Limit capped at MAX_QUERY_LIMIT unconditionally
    - Only connection_id filter is effective (no JSON field filtering in v1)

    Args:
        model: Model name (path parameter) - must match ^[a-z][a-z0-9_]*$
        request: FastAPI request (for correlation ID)
        body: QueryRequest with filters, limit (no offset - deferred)
        handler: QueryHandler dependency

    Returns:
        QueryResponse with paginated envelope or ProblemDetail error
    """
    # Validate model name against allowlist
    if error := _validate_model_name(model):
        logger.warning(
            "query_invalid_model",
            model=model,
            error_type=error.type,
        )
        return JSONResponse(
            status_code=error.status,
            content=error.model_dump(),
        )

    # Validate filter values
    if error := _validate_filter_values(body.filters):
        logger.warning(
            "query_filter_value_too_long",
            model=model,
            error_type=error.type,
        )
        return JSONResponse(
            status_code=error.status,
            content=error.model_dump(),
        )

    # Get correlation ID from middleware
    correlation_id = getattr(request.state, "correlation_id", "")

    # Compute effective limit (capped at MAX_QUERY_LIMIT)
    effective_limit = min(body.limit, MAX_QUERY_LIMIT)

    # For has_more detection, we request one extra record
    # KNOWN LIMITATION: At MAX_QUERY_LIMIT boundary, this doesn't work because
    # QueryHandler also caps at MAX_QUERY_LIMIT. When limit=1000, we pass 1001,
    # handler caps to 1000, and we can't detect if there are more records.
    # Documented as accepted behavior per checker feedback.
    fetch_limit = effective_limit + 1 if effective_limit < MAX_QUERY_LIMIT else effective_limit

    query = QueryData(
        model=model,
        filters=body.filters,
        limit=fetch_limit,
        correlation=CorrelationContext(source="http_query"),
    )

    logger.info(
        "query_started",
        model=model,
        filter_count=len(body.filters) if body.filters else 0,
        limit=effective_limit,
    )

    # Execute query via handler
    results = await handler.handle(query)

    # Determine has_more by checking if we got more than requested
    # Note: at MAX_QUERY_LIMIT, has_more will be False even if more records exist
    has_more = len(results) > effective_limit
    if has_more:
        results = results[:effective_limit]  # Trim extra record

    logger.info(
        "query_completed",
        model=model,
        count=len(results),
        has_more=has_more,
    )

    return QueryResponse(
        data=results,
        count=len(results),
        limit=effective_limit,
        has_more=has_more,
    )
