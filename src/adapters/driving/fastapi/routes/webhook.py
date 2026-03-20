"""Nango webhook endpoint with fast-ack pattern.

Receives webhooks, verifies signature, acknowledges immediately (202),
then fetches actual records from Nango Records API in background.

Per CONTEXT.md decisions:
- Sync webhooks only: auth and forward types acknowledged (202) but not processed
- Fast-ack + background processing via FastAPI BackgroundTasks
- Validation failure: 202 Accepted (stops Nango retries), log failure with full context
- Unknown webhook types: 202 Accepted, ignore, log at INFO level

Flow:
1. Webhook notifies sync completed
2. We acknowledge immediately (202)
3. Background task fetches records via GET /records API
4. Each record is stored individually with event_id for idempotency
"""

import hashlib
import json
import time
from typing import Any

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, Request
from structlog.contextvars import bind_contextvars, clear_contextvars

from src.adapters.driven.nango import NangoClient
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

from ..dependencies import get_add_data_handler, get_nango_client, verify_nango_signature
from ..schemas import WebhookResponse

router = APIRouter(tags=["webhooks"])
logger = get_logger(__name__)


@router.post("/webhooks/nango", status_code=202, response_model=WebhookResponse)
async def nango_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    raw_body: bytes = Depends(verify_nango_signature),
    handler: AddDataHandler = Depends(get_add_data_handler),
    nango_client: NangoClient = Depends(get_nango_client),
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
        nango_client=nango_client,
        correlation_id=correlation_id,
    )

    return WebhookResponse(status="accepted")


async def _process_sync_webhook(
    payload: dict[str, Any],
    handler: AddDataHandler,
    nango_client: NangoClient,
    correlation_id: str,
) -> None:
    """Background task: fetch and store records after sync webhook.

    1. Check if sync was successful
    2. Fetch actual records from Nango Records API
    3. Store each record individually with event_id for idempotency

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
    model = payload.get("model", "unknown")
    connection_id = payload.get("connectionId", "unknown")

    # Check if this is an error sync - don't fetch records for failed syncs
    is_error = _is_sync_error(payload)
    if is_error:
        bg_logger.warning(
            "sync_error_received",
            connection_id=connection_id,
            model=model,
            error=payload.get("error"),
        )
        # Record latency even for errors
        elapsed = time.monotonic() - start_time
        processing_latency.observe(elapsed)
        return

    bg_logger.info(
        "fetching_nango_records",
        connection_id=connection_id,
        model=model,
    )

    try:
        # Fetch actual records from Nango Records API
        records = await nango_client.fetch_all_records(
            model=model,
            connection_id=connection_id,
            provider_config_key=payload.get("providerConfigKey", "salesforce"),
        )

        bg_logger.info(
            "nango_records_received",
            connection_id=connection_id,
            model=model,
            record_count=len(records),
        )

        # Store each record individually
        stored_count = 0
        for record in records:
            # Generate event_id from record for idempotency
            # Use the record's Nango ID if available, otherwise hash the record
            record_id = record.get("id") or record.get("Id")
            if record_id:
                event_id = f"{model}:{connection_id}:{record_id}"
            else:
                event_id = _generate_nango_event_id(record)

            # Enrich record with event_id
            enriched_record = {
                **record,
                "event_id": event_id,
                "_sync_error": False,
            }

            command = AddDataCommand(
                model=model,
                connection_id=connection_id,
                schema_name=model,
                raw_data=enriched_record,
                correlation=CorrelationContext(source="nango_records"),
            )

            try:
                await handler.handle(command)
                stored_count += 1
                records_added.inc()

            except ValidationError as exc:
                validation_failures.labels(schema_name=exc.schema_name).inc()
                log_kwargs: dict[str, Any] = {
                    "schema_name": exc.schema_name,
                    "connection_id": connection_id,
                    "model": model,
                    "record_id": record_id,
                    "error_count": len(exc.errors),
                    "error_fields": [e.field_path for e in exc.errors],
                }
                if should_log_full_payload():
                    log_kwargs["data_sample"] = _truncate_payload(record)
                bg_logger.warning("record_validation_failure", **log_kwargs)

            except SchemaNotFoundError as exc:
                validation_failures.labels(schema_name=exc.schema_name).inc()
                bg_logger.warning(
                    "schema_not_found",
                    schema_name=exc.schema_name,
                    connection_id=connection_id,
                    model=model,
                )
                # Stop processing this model if schema not found
                break

        bg_logger.info(
            "records_stored",
            connection_id=connection_id,
            model=model,
            stored_count=stored_count,
            total_records=len(records),
        )

    except httpx.HTTPStatusError as exc:
        bg_logger.error(
            "nango_api_error",
            connection_id=connection_id,
            model=model,
            status_code=exc.response.status_code,
            response_text=exc.response.text[:500],
        )

    except Exception:
        bg_logger.exception(
            "webhook_processing_error",
            connection_id=connection_id,
            model=model,
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


def _generate_nango_event_id(payload: dict[str, Any]) -> str:
    """Generate a unique event_id for a Nango webhook payload.

    The event_id is a SHA-256 hash of the canonical JSON representation of the
    payload. This ensures:
    - Same payload = same event_id (idempotency for exact duplicates)
    - Different payload = different event_id (retried/fixed syncs get stored)

    A successful sync and an errored sync for the same model will have different
    payloads (different timestamps, error fields, etc.) and thus different event_ids.

    Args:
        payload: The Nango webhook payload

    Returns:
        A hex string hash suitable for use as event_id
    """
    # Use canonical JSON (sorted keys, no extra whitespace) for consistent hashing
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def _is_sync_error(payload: dict[str, Any]) -> bool:
    """Check if a Nango sync webhook indicates an error.

    Args:
        payload: The Nango webhook payload

    Returns:
        True if the sync failed (success=false or error field present)
    """
    return payload.get("success") is False or "error" in payload
