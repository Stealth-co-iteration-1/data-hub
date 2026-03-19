"""Prometheus metrics endpoint for external scrapers.

Exposes all registered metrics in Prometheus text format.
"""

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

router = APIRouter(tags=["observability"])


@router.get("/metrics", response_class=PlainTextResponse)
async def metrics() -> PlainTextResponse:
    """Export Prometheus metrics in text format.

    Returns all registered metrics (webhooks_received, validation_failures,
    records_added, processing_latency) in Prometheus exposition format.
    """
    return PlainTextResponse(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
