"""Nango webhook endpoint with fast-ack pattern.

Receives webhooks, verifies signature, acknowledges immediately (202),
then processes in background task.

Per CONTEXT.md decisions:
- Sync webhooks only: auth and forward types acknowledged (202) but not processed
- Fast-ack + background processing via FastAPI BackgroundTasks
- Validation failure: 202 Accepted (stops Nango retries), log failure with full context
- Unknown webhook types: 202 Accepted, ignore, log at INFO level
"""

import json
import time
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from structlog.contextvars import bind_contextvars, clear_contextvars

from src.kernel.commands.add_data import AddDataCommand
from src.kernel.domain.models import CorrelationContext
from src.kernel.exceptions import SchemaNotFoundError, ValidationError
from src.kernel.handlers.add_data_handler import AddDataHandler
from src.observability.logging import get_logger, should_log_full_payload
from src.observability.metrics import (
    processing_latency,
    records_added,
    validation_failures,
    webhooks_received,
)

from ..dependencies import get_add_data_handler, verify_nango_signature
from ..schemas import WebhookResponse

router = APIRouter(tags=["webhooks"])
logger = get_logger(__name__)


@router.post("/webhooks/nango", status_code=202, response_model=WebhookResponse)
async def nango_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    raw_body: bytes = Depends(verify_nango_signature),
    handler: AddDataHandler = Depends(get_add_data_handler),
) -> WebhookResponse:
    """Receive Nango webhook, acknowledge immediately, process in background.

    Returns 202 Accepted immediately to prevent Nango timeout (20s limit).
    Background task handles validation, persistence, and event publishing.

    Signature verification happens in dependency before this runs.
    """
    payload = json.loads(raw_body)
    webhook_type = payload.get("type", "unknown")

    # Increment webhook counter (OBSV-03)
    webhooks_received.labels(type=webhook_type).inc()

    # Get correlation ID from middleware (set in CorrelationIdMiddleware via request.state)
    correlation_id = getattr(request.state, "correlation_id", "")

    # Log webhook receipt (OBSV-01)
    logger.info(
        "webhook_received",
        webhook_type=webhook_type,
        connection_id=payload.get("connectionId"),
        model=payload.get("model"),
    )

    # Only process sync webhooks (per CONTEXT.md)
    if webhook_type != "sync":
        # Non-sync types: ack and ignore (auth, forward, unknown)
        logger.info(
            "webhook_ignored",
            webhook_type=webhook_type,
            reason="non_sync_type",
        )
        return WebhookResponse(status="accepted")

    # Fast-ack: schedule background processing, return immediately
    background_tasks.add_task(
        _process_sync_webhook,
        payload=payload,
        handler=handler,
        correlation_id=correlation_id,
    )

    return WebhookResponse(status="accepted")


async def _process_sync_webhook(
    payload: dict[str, Any],
    handler: AddDataHandler,
    correlation_id: str,
) -> None:
    """Background task: process a sync webhook after 202 is returned.

    Creates AddDataCommand from webhook payload and calls handler.
    Logs validation errors with full context (per OBSV-02).
    Records processing latency metric (OBSV-03).

    Important: Re-bind correlation_id since this runs after request completes.
    """
    # Start latency timer (OBSV-03)
    start_time = time.monotonic()

    # Re-bind correlation context for background task (OBSV-01)
    clear_contextvars()
    bind_contextvars(
        correlation_id=correlation_id,
        phase="background",
        model=payload.get("model"),
    )

    bg_logger = get_logger(__name__)

    # Build AddDataCommand from Nango sync webhook payload
    command = AddDataCommand(
        model=payload.get("model", "unknown"),
        connection_id=payload.get("connectionId", "unknown"),
        schema_name=payload.get("model", "unknown"),
        raw_data=payload,
        correlation=CorrelationContext(source="nango_webhook"),
    )

    bg_logger.info(
        "webhook_processing_started",
        connection_id=command.connection_id,
        model=command.model,
    )

    try:
        await handler.handle(command)

        # Success: increment records_added counter (OBSV-03)
        records_added.inc()

        bg_logger.info(
            "webhook_processed_ok",
            connection_id=command.connection_id,
            model=command.model,
        )

    except ValidationError as exc:
        # Validation failure: increment counter and log (OBSV-02, OBSV-03)
        validation_failures.labels(schema_name=exc.schema_name).inc()

        log_kwargs: dict[str, Any] = {
            "schema_name": exc.schema_name,
            "connection_id": command.connection_id,
            "model": command.model,
            "error_count": len(exc.errors),
            "error_fields": [e.field_path for e in exc.errors],
        }

        # Full payload only in development (per CONTEXT.md)
        if should_log_full_payload():
            log_kwargs["data_sample"] = _truncate_payload(payload)

        bg_logger.warning("validation_failure", **log_kwargs)

    except SchemaNotFoundError as exc:
        # Schema not found: count as validation failure
        validation_failures.labels(schema_name=exc.schema_name).inc()

        bg_logger.warning(
            "schema_not_found",
            schema_name=exc.schema_name,
            connection_id=command.connection_id,
            model=command.model,
        )

    except Exception:
        # Unexpected error: log exception with stack trace
        bg_logger.exception(
            "webhook_processing_error",
            connection_id=command.connection_id,
            model=command.model,
        )

    finally:
        # Always record processing latency (OBSV-03)
        elapsed = time.monotonic() - start_time
        processing_latency.observe(elapsed)


def _truncate_payload(payload: dict[str, Any], max_keys: int = 10) -> dict[str, Any]:
    """Truncate payload for safe logging in development.

    Args:
        payload: Original payload dict
        max_keys: Maximum number of keys to include

    Returns:
        Truncated payload with indication if truncated
    """
    if len(payload) <= max_keys:
        return payload

    truncated: dict[str, object] = dict(list(payload.items())[:max_keys])
    truncated["_truncated"] = True
    truncated["_original_keys"] = len(payload)
    return truncated
