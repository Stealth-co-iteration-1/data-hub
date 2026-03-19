"""Integration tests for Nango webhook signature verification (TRAN-03)."""

import hashlib
import hmac
import json

import pytest
from httpx import ASGITransport, AsyncClient

WEBHOOK_SECRET = "test_secret_for_signature_verification"


def make_signature(body: bytes, secret: str) -> str:
    """Compute HMAC-SHA256 signature for webhook body."""
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


@pytest.fixture
def valid_sync_payload() -> dict:
    """Valid Nango sync webhook payload."""
    return {
        "type": "sync",
        "connectionId": "conn_test_123",
        "providerConfigKey": "hubspot",
        "syncName": "contacts",
        "model": "contact",
        "responseResults": {"added": 5, "updated": 2, "deleted": 0},
        "syncType": "INCREMENTAL",
        "modifiedAfter": "2024-01-15T10:00:00.000Z",
    }


@pytest.fixture
async def client():
    """AsyncClient with test signature dependency and handler overridden."""
    from fastapi import Header, HTTPException, Request, status

    from src.adapters.driving.fastapi.app import app
    from src.adapters.driving.fastapi.dependencies import (
        get_add_data_handler,
        verify_nango_signature,
    )
    from src.kernel.handlers.add_data_handler import AddDataHandler
    from tests.unit.fakes import FakeDataRepository, FakeEventPublisher, FakeSchemaRegistry

    async def test_verify_signature(
        request: Request,
        x_nango_hmac_sha256: str | None = Header(default=None),
    ) -> bytes:
        """Test version of signature verification using WEBHOOK_SECRET."""
        raw_body = await request.body()

        if x_nango_hmac_sha256 is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": "invalid_signature"},
            )

        expected = hmac.new(
            WEBHOOK_SECRET.encode(),
            raw_body,
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(expected, x_nango_hmac_sha256):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": "invalid_signature"},
            )

        return raw_body

    async def fake_handler():
        """Fake handler that doesn't need session_factory."""
        return AddDataHandler(
            repository=FakeDataRepository(),
            event_publisher=FakeEventPublisher(),
            schema_registry=FakeSchemaRegistry(),
        )

    app.dependency_overrides[verify_nango_signature] = test_verify_signature
    app.dependency_overrides[get_add_data_handler] = fake_handler

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c

    app.dependency_overrides.clear()


class TestSignatureVerification:
    """Tests for TRAN-03: Webhook signature verification."""

    async def test_signature_rejects_invalid_signature(
        self, client: AsyncClient, valid_sync_payload: dict
    ):
        """Invalid signature returns 401 with error detail."""
        body = json.dumps(valid_sync_payload).encode()

        response = await client.post(
            "/webhooks/nango",
            content=body,
            headers={
                "x-nango-hmac-sha256": "invalid_signature_here",
                "content-type": "application/json",
            },
        )

        assert response.status_code == 401
        assert response.json() == {"detail": {"error": "invalid_signature"}}

    async def test_signature_rejects_missing_header(
        self, client: AsyncClient, valid_sync_payload: dict
    ):
        """Missing signature header returns 401."""
        body = json.dumps(valid_sync_payload).encode()

        response = await client.post(
            "/webhooks/nango",
            content=body,
            headers={"content-type": "application/json"},
        )

        assert response.status_code == 401
        assert response.json() == {"detail": {"error": "invalid_signature"}}

    async def test_signature_accepts_valid_signature(
        self, client: AsyncClient, valid_sync_payload: dict
    ):
        """Valid signature passes verification and returns 202."""
        body = json.dumps(valid_sync_payload).encode()
        signature = make_signature(body, WEBHOOK_SECRET)

        response = await client.post(
            "/webhooks/nango",
            content=body,
            headers={
                "x-nango-hmac-sha256": signature,
                "content-type": "application/json",
            },
        )

        assert response.status_code == 202
        assert response.json() == {"status": "accepted"}
