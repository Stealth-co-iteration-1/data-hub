"""Health check endpoint for service monitoring.

Per CONTEXT.md decisions:
- Single /health endpoint
- Internally tests DB connectivity - but does NOT expose connection details
- Response format: {"status": "ok", "version": "1.0.0"} (200) or {"status": "error"} (503)
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from src.config.settings import settings
from src.observability.logging import get_logger

router = APIRouter(tags=["health"])
logger = get_logger(__name__)


@router.get("/health")
async def health_check(request: Request) -> JSONResponse:
    """Check service health including database connectivity.

    Returns:
        200 OK: Service and database are healthy
        503 Service Unavailable: Database connection failed

    Response body never includes sensitive information (connection strings, etc.).
    """
    try:
        # Test database connectivity with lightweight query
        async with request.app.state.engine.connect() as conn:
            await conn.execute(text("SELECT 1"))

        return JSONResponse(
            status_code=200,
            content={
                "status": "ok",
                "version": settings.version,
            },
        )

    except Exception:
        # Log the actual error server-side, but don't expose to client
        logger.exception("health_check_db_failed")

        return JSONResponse(
            status_code=503,
            content={"status": "error"},
        )
