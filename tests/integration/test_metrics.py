"""Integration tests for Prometheus metrics (OBSV-03)."""

import asyncio
import hashlib
import hmac
import json

import pytest
from httpx import ASGITransport, AsyncClient

WEBHOOK_SECRET = "test_secret_for_metrics_tests"


def make_signature(body: bytes, secret: str) -> str:
    """Compute HMAC-SHA256 signature for webhook body."""
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


class FakeNangoClient:
    """Fake Nango client for testing."""

    async def fetch_all_records(
        self, model: str, connection_id: str, provider_config_key: str = "salesforce"
    ) -> list[dict]:
        """Return a test record to trigger schema validation."""
        # Return a record so schema validation is attempted
        return [{"id": "test_record_1", "data": "test"}]


@pytest.fixture
async def client(monkeypatch):
    """AsyncClient with test configuration using dependency overrides."""
    import hashlib
    import hmac

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
        """Fake handler using FakeSchemaRegistry to control schema behavior."""
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


class TestWebhooksReceivedMetric:
    """Tests for webhooks_received_total counter."""

    async def test_webhooks_received_counter_increments(self, client: AsyncClient):
        """webhooks_received_total counter increases after webhook."""
        from src.observability.metrics import webhooks_received

        # Get initial count for sync type
        initial_count = webhooks_received.labels(type="sync")._value.get()

        # Send a webhook
        payload = {"type": "sync", "connectionId": "conn_123", "model": "contact"}
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

        # Check counter increased
        new_count = webhooks_received.labels(type="sync")._value.get()
        assert new_count == initial_count + 1

    async def test_webhooks_received_labels_by_type(self, client: AsyncClient):
        """webhooks_received_total counter uses type label correctly."""
        from src.observability.metrics import webhooks_received

        # Get initial counts
        sync_before = webhooks_received.labels(type="sync")._value.get()
        auth_before = webhooks_received.labels(type="auth")._value.get()

        # Send sync webhook
        sync_payload = {"type": "sync", "connectionId": "conn_1"}
        sync_body = json.dumps(sync_payload).encode()
        await client.post(
            "/webhooks/nango",
            content=sync_body,
            headers={
                "x-nango-hmac-sha256": make_signature(sync_body, WEBHOOK_SECRET),
                "content-type": "application/json",
            },
        )

        # Send auth webhook
        auth_payload = {"type": "auth", "connectionId": "conn_2"}
        auth_body = json.dumps(auth_payload).encode()
        await client.post(
            "/webhooks/nango",
            content=auth_body,
            headers={
                "x-nango-hmac-sha256": make_signature(auth_body, WEBHOOK_SECRET),
                "content-type": "application/json",
            },
        )

        # Check each type incremented separately
        sync_after = webhooks_received.labels(type="sync")._value.get()
        auth_after = webhooks_received.labels(type="auth")._value.get()

        assert sync_after == sync_before + 1
        assert auth_after == auth_before + 1


class TestProcessingLatencyMetric:
    """Tests for processing_latency_seconds histogram."""

    async def test_processing_latency_histogram_records(self, client: AsyncClient):
        """processing_latency_seconds histogram records processing time."""
        from src.observability.metrics import processing_latency

        # Get initial sum
        initial_count = processing_latency._sum.get()

        # Send a sync webhook (will be processed in background)
        payload = {"type": "sync", "connectionId": "conn_latency", "model": "contact"}
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

        # Wait for background task to complete
        await asyncio.sleep(0.2)

        # Check histogram was updated (sum should have increased)
        new_count = processing_latency._sum.get()
        assert new_count > initial_count, "Histogram sum should have increased"


class TestValidationFailuresMetric:
    """Tests for validation_failures_total counter."""

    async def test_validation_failures_counter_increments_on_schema_not_found(
        self, client: AsyncClient
    ):
        """validation_failures_total counter increases on schema not found error."""
        from src.observability.metrics import validation_failures

        # Use a model name that doesn't have a schema registered
        # FakeSchemaRegistry raises SchemaNotFoundError for unknown schemas
        schema_name = "nonexistent_schema_xyz"

        # Get initial count (create label if needed)
        initial_count = validation_failures.labels(schema_name=schema_name)._value.get()

        # Send webhook with unknown schema
        payload = {
            "type": "sync",
            "connectionId": "conn_validation",
            "model": schema_name,
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

        # Wait for background task
        await asyncio.sleep(0.2)

        # Check counter increased
        new_count = validation_failures.labels(schema_name=schema_name)._value.get()
        assert new_count == initial_count + 1
