---
status: complete
phase: 03-webhook-transport-observability
source: [03-01-SUMMARY.md, 03-02-SUMMARY.md, 03-03-SUMMARY.md]
started: 2026-03-19T00:00:00Z
updated: 2026-03-19T00:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Cold Start Smoke Test
expected: Kill any running server. Run `uv run alembic upgrade head`. Start server with `NANGO_WEBHOOK_SECRET=test123 uv run uvicorn src.adapters.driving.fastapi.app:app --port 8000`. Server boots without errors.
result: pass

### 2. Health Check Returns 200
expected: Run `curl http://localhost:8000/health` — returns `{"status":"ok","version":"1.0.0"}` with HTTP 200.
result: pass

### 3. Metrics Endpoint Works
expected: Run `curl http://localhost:8000/metrics` — returns Prometheus text format with `webhooks_received_total`, `processing_latency_seconds` metrics.
result: pass

### 4. Webhook Rejects Missing Signature
expected: Run `curl -X POST http://localhost:8000/webhooks/nango -H "Content-Type: application/json" -d '{"type":"sync"}'` — returns HTTP 401 with `{"detail":{"error":"invalid_signature"}}`.
result: pass

### 5. Webhook Accepts Valid Signature
expected: Generate valid HMAC-SHA256 signature and POST to /webhooks/nango — returns HTTP 202 with `{"status":"accepted"}`.
result: pass

### 6. Correlation ID in Response
expected: Any request to /webhooks/nango or /health includes `x-correlation-id` header in response.
result: pass

## Summary

total: 6
passed: 6
issues: 0
pending: 0
skipped: 0

## Gaps

[none yet]
