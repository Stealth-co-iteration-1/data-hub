"""FastAPI middleware for request-scoped context.

Provides correlation ID middleware using structlog.contextvars
for automatic propagation through async request handling.
"""

from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from structlog.contextvars import bind_contextvars, clear_contextvars


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware to manage correlation IDs per request.

    For each request:
    1. Clears previous request's contextvars
    2. Extracts or generates correlation_id
    3. Binds correlation_id to structlog contextvars
    4. Adds correlation_id to response headers

    All log calls within the request automatically include correlation_id.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Process request with correlation ID context."""
        # Clear context from previous request (important for async)
        clear_contextvars()

        # Get correlation ID from header or generate new one
        correlation_id = request.headers.get(
            "x-correlation-id",
            str(uuid4()),
        )

        # Store in request.state for access by route handlers and background tasks
        request.state.correlation_id = correlation_id

        # Bind to structlog contextvars - all logs in this request get it
        bind_contextvars(
            correlation_id=correlation_id,
            path=request.url.path,
            method=request.method,
        )

        # Process request
        response = await call_next(request)

        # Echo correlation ID in response for client tracing
        response.headers["x-correlation-id"] = correlation_id

        return response
