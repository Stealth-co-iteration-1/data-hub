"""FastAPI dependencies for webhook processing.

Provides:
- verify_nango_signature: HMAC-SHA256 signature verification on raw request bytes
- get_add_data_handler: Dependency injection for kernel handler
"""

import hashlib
import hmac

from fastapi import Header, HTTPException, Request, status

from src.adapters.driven.event_bus.publisher import InMemoryEventPublisher
from src.adapters.driven.schema_registry.permissive import PermissiveSchemaRegistry
from src.adapters.driven.sqlite.repository import SQLiteDataRepository
from src.config.settings import settings
from src.kernel.handlers.add_data_handler import AddDataHandler


# Global event publisher instance - shared across requests
_event_publisher = InMemoryEventPublisher()


async def verify_nango_signature(
    request: Request,
    x_nango_hmac_sha256: str | None = Header(default=None),
) -> bytes:
    """Verify Nango webhook signature on raw request bytes.

    CRITICAL: Must be called before any JSON parsing.
    request.body() caches the body, so subsequent parsing still works.

    Args:
        request: FastAPI Request object
        x_nango_hmac_sha256: Signature from Nango header

    Returns:
        Raw body bytes for subsequent parsing

    Raises:
        HTTPException 401: If signature is missing or invalid
    """
    raw_body = await request.body()

    # Missing header
    if x_nango_hmac_sha256 is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "invalid_signature"},
        )

    # Compute expected signature
    expected = hmac.new(
        settings.nango_webhook_secret.encode(),
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    # Constant-time comparison to prevent timing attacks
    if not hmac.compare_digest(expected, x_nango_hmac_sha256):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "invalid_signature"},
        )

    return raw_body


def get_schema_registry() -> PermissiveSchemaRegistry:
    """Get schema registry for validation.

    For v1, returns a permissive registry that accepts all data.
    Phase 4 will introduce strict schema enforcement per Nango model.
    """
    return PermissiveSchemaRegistry()


async def get_add_data_handler(request: Request) -> AddDataHandler:
    """Dependency injection for AddDataHandler.

    Creates handler with:
    - SQLiteDataRepository from app.state.session_factory
    - InMemoryEventPublisher (shared instance)
    - PermissiveSchemaRegistry (v1 pass-through)

    Args:
        request: FastAPI request (provides app.state)

    Returns:
        Configured AddDataHandler instance
    """
    repository = SQLiteDataRepository(request.app.state.session_factory)
    schema_registry = get_schema_registry()

    return AddDataHandler(
        repository=repository,
        event_publisher=_event_publisher,
        schema_registry=schema_registry,
    )
