"""Integration tests for Prometheus metrics endpoint."""

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def client():
    """AsyncClient for testing metrics endpoint."""
    from src.adapters.driving.fastapi.app import app

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c


class TestMetricsEndpoint:
    """Tests for GET /metrics endpoint."""

    async def test_metrics_returns_200(self, client: AsyncClient):
        """Metrics endpoint returns 200 OK."""
        response = await client.get("/metrics")
        assert response.status_code == 200

    async def test_metrics_returns_prometheus_format(self, client: AsyncClient):
        """Metrics endpoint returns Prometheus text format."""
        response = await client.get("/metrics")

        # Check content type
        assert "text/plain" in response.headers.get("content-type", "")

        # Check for expected metric names in response
        content = response.text
        assert "webhooks_received_total" in content
        assert "validation_failures_total" in content
        assert "records_added_total" in content
        assert "processing_latency_seconds" in content

    async def test_metrics_includes_histogram_buckets(self, client: AsyncClient):
        """Processing latency histogram includes bucket definitions."""
        response = await client.get("/metrics")
        content = response.text

        # Histograms have _bucket, _count, _sum suffixes
        assert "processing_latency_seconds_bucket" in content
        assert "processing_latency_seconds_count" in content
        assert "processing_latency_seconds_sum" in content
