"""Integration tests for Nango webhook endpoint (TRAN-01, TRAN-02)."""

import hashlib
import hmac
import json
import time

import pytest
from httpx import ASGITransport, AsyncClient

WEBHOOK_SECRET = "test_secret_for_webhook_tests"


def make_signature(body: bytes, secret: str) -> str:
    """Compute HMAC-SHA256 signature for webhook body."""
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


class FakeNangoClient:
    """Fake Nango client for testing."""

    async def fetch_all_records(
        self, model: str, connection_id: str, provider_config_key: str = "salesforce"
    ) -> list[dict]:
        """Return empty records for tests."""
        return []


@pytest.fixture
async def client():
    """AsyncClient with test signature dependency and handler overridden."""
    from fastapi import Header, HTTPException, Request, status

    from src.adapters.driving.fastapi.app import app
    from src.adapters.driving.fastapi.dependencies import (
        get_add_data_handler,
        get_nango_client,
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

    def fake_nango_client():
        """Fake Nango client that doesn't make real HTTP calls."""
        return FakeNangoClient()

    app.dependency_overrides[verify_nango_signature] = test_verify_signature
    app.dependency_overrides[get_add_data_handler] = fake_handler
    app.dependency_overrides[get_nango_client] = fake_nango_client

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c

    app.dependency_overrides.clear()


class TestWebhookEndpoint:
    """Tests for TRAN-01: FastAPI endpoint receives Nango webhooks."""

    async def test_webhook_accepts_valid_sync_webhook(self, client: AsyncClient):
        """Valid sync webhook returns 202 Accepted."""
        payload = {
            "type": "sync",
            "connectionId": "conn_123",
            "model": "contact",
            "responseResults": {"added": 1},
        }
        body = json.dumps(payload).encode()
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

    async def test_webhook_accepts_non_sync_type(self, client: AsyncClient):
        """Non-sync webhook types (auth, forward) return 202 but are not processed."""
        for webhook_type in ["auth", "forward", "unknown"]:
            payload = {"type": webhook_type, "connectionId": "conn_123"}
            body = json.dumps(payload).encode()
            signature = make_signature(body, WEBHOOK_SECRET)

            response = await client.post(
                "/webhooks/nango",
                content=body,
                headers={
                    "x-nango-hmac-sha256": signature,
                    "content-type": "application/json",
                },
            )

            assert response.status_code == 202, f"Failed for type: {webhook_type}"
            assert response.json() == {"status": "accepted"}


class TestFastAck:
    """Tests for TRAN-02: Webhook acknowledged within 5 seconds."""

    async def test_webhook_fast_ack_returns_before_processing(
        self, client: AsyncClient
    ):
        """Response returned quickly (fast-ack pattern).

        The 202 should be returned before background processing begins.
        We verify response time is under 100ms (well under 5s requirement).
        """
        payload = {
            "type": "sync",
            "connectionId": "conn_fast_ack",
            "model": "contact",
            "responseResults": {"added": 100},  # Large batch
        }
        body = json.dumps(payload).encode()
        signature = make_signature(body, WEBHOOK_SECRET)

        start = time.monotonic()
        response = await client.post(
            "/webhooks/nango",
            content=body,
            headers={
                "x-nango-hmac-sha256": signature,
                "content-type": "application/json",
            },
        )
        elapsed_ms = (time.monotonic() - start) * 1000

        assert response.status_code == 202
        # Fast-ack: response in under 100ms (well under 5s requirement)
        assert elapsed_ms < 100, f"Response took {elapsed_ms:.1f}ms, expected <100ms"
