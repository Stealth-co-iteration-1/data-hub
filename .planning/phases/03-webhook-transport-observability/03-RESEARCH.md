# Phase 3: Webhook Transport & Observability - Research

**Researched:** 2026-03-18
**Domain:** FastAPI webhook ingestion, HMAC signature verification, structlog structured logging, Prometheus-style metrics
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Sync webhooks only** — auth and forward types are acknowledged (202) but not processed
- **Fast-ack + background processing** — return 202 immediately, process via FastAPI BackgroundTasks
- **Signature verification via FastAPI dependency** — reads raw request body, computes HMAC-SHA256 with env secret, compares to `X-Nango-Hmac-Sha256` header, rejects 401 on mismatch
- Nango timeout is 20 seconds — fast ack ensures we never hit it
- **JSON structured logging** via structlog with JSON output
- Each log entry: correlation_id, timestamp, level, message, and context fields
- **Sensitive data handling:** Full payloads logged in dev only (ENV=development), strict redaction in staging/prod
- Log validation error field paths but not values in non-dev environments
- **Counters:** webhooks_received_total, validation_failures_total, records_added_total
- **Latency histogram:** processing_latency_seconds with p50/p95/p99 buckets
- Single `/health` endpoint — internally tests DB connectivity, does NOT expose connection details
- Response format: `{"status": "ok", "version": "1.0.0"}` (200) or `{"status": "error"}` (503)
- **Signature failure:** 401 Unauthorized with `{"error": "invalid_signature"}`
- **Validation failure:** 202 Accepted (stop retries), log failure with full context
- **Unknown webhook types:** 202 Accepted, ignore, log at INFO level

### Claude's Discretion
- Exact structlog configuration and processors
- Metrics export mechanism (in-memory counters vs Prometheus client)
- FastAPI lifespan setup for DB connection pool
- Exact Pydantic models for webhook payloads

### Deferred Ideas (OUT OF SCOPE)
- Dead letter queue for failed webhooks — v2 requirement (RESL-02)
- Automatic retry with backoff — v2 requirement (RESL-01)
- Auth webhook handling for connection status tracking — could be Phase 4
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TRAN-01 | FastAPI endpoint receives Nango webhooks | FastAPI 0.135.1 driving adapter pattern; `Request.body()` for raw bytes; `BackgroundTasks` for async processing |
| TRAN-02 | Webhook acknowledged within 5 seconds (fast ack pattern) | 202 returned immediately before handler runs; BackgroundTasks execute after response sent |
| TRAN-03 | Webhook signature verified on raw bytes before processing | HMAC-SHA256 on `await request.body()`, header `X-Nango-Hmac-Sha256`, FastAPI dependency pattern |
| TRAN-04 | Health check endpoint returns service and database status | Single `/health` GET; runs a lightweight DB query; returns 200 or 503 |
| OBSV-01 | Structured logging with correlation IDs for request tracing | structlog 25.5.0 with `contextvars` module; middleware binds correlation_id per request |
| OBSV-02 | Validation failures logged with full context (source, schema, data sample) | `ValidationError` from kernel carries `schema_name` + `errors[].field_path`; adapter logs these |
| OBSV-03 | Data quality metrics tracked: validation failure rate, processing latency | `prometheus-client` 0.24.1: `Counter` + `Histogram`; `/metrics` endpoint or in-memory |
</phase_requirements>

---

## Summary

Phase 3 builds the driving adapter layer in the hexagonal architecture: a FastAPI application that receives Nango webhook POSTs, verifies their cryptographic signature on the raw request bytes, dispatches processing to background tasks, and provides full observability via structured logging and metrics. The kernel (`AddDataHandler`) and persistence layer (`SQLiteDataRepository`) are already complete from Phases 1 and 2 — this phase wires them to HTTP.

The primary technical challenge is signature verification order: HMAC must be computed against the raw request body bytes **before** any JSON parsing. FastAPI's `await request.body()` returns these raw bytes and caches them so subsequent parsing works normally. This must be implemented as a FastAPI dependency (not inline route logic) to stay consistent with the hexagonal adapter pattern.

Observability uses structlog's `contextvars` module for zero-overhead request-scoped correlation IDs. Every log entry within a request automatically carries `correlation_id` without explicit passing. Metrics use `prometheus-client`'s Counter and Histogram types, which are the standard choice for Python service metrics with p50/p95/p99 latency support.

**Primary recommendation:** Build in three plans: (1) FastAPI app scaffold + webhook endpoint + signature dependency, (2) structlog configuration + correlation ID middleware + OBSV-01/OBSV-02 logging, (3) metrics + health check + integration tests.

---

## Standard Stack

### Core (additions to existing project)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| fastapi[standard] | 0.135.1 | HTTP framework and routing | Already planned; native async, dependency injection, BackgroundTasks built-in |
| uvicorn | 0.42.0 | ASGI server | Standard server for FastAPI in development and production |
| structlog | 25.5.0 | Structured JSON logging | Production-ready, `contextvars` support for async request-scoped context |
| prometheus-client | 0.24.1 | Metrics counters and histograms | Official Prometheus Python client; Counter, Histogram, WSGI/ASGI handlers |
| httpx | 0.28.1 | Async HTTP client for tests | `ASGITransport` + `AsyncClient` for testing FastAPI endpoints without running a server |

### Already Installed (from Phases 1 & 2)
| Library | Version | Purpose |
|---------|---------|---------|
| pydantic | 2.12.5 | Request/response schema validation |
| sqlalchemy[asyncio] | 2.0.48 | DB session for health check |
| aiosqlite | 0.22.1 | SQLite async driver |
| pytest | 9.0.2 | Test runner |
| pytest-asyncio | 1.3.0 | Async test support |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| prometheus-client | In-memory dict counters | Simpler, no `/metrics` endpoint, not Prometheus-compatible — acceptable for v1 if no scraping infra yet |
| structlog | standard `logging` | No contextvars, no JSON processors, harder to bind per-request state |
| BackgroundTasks | asyncio.create_task() | create_task requires running event loop; BackgroundTasks is FastAPI-native and handles cleanup |

**Installation (additions only):**
```bash
uv add "fastapi[standard]>=0.135.1" "uvicorn>=0.42.0" "structlog>=25.5.0" "prometheus-client>=0.24.1"
uv add --dev "httpx>=0.28.1"
```

**Version verification (confirmed March 2026):**
- fastapi 0.135.1 — confirmed via [PyPI](https://pypi.org/project/fastapi/)
- structlog 25.5.0 — confirmed via [structlog.org](https://www.structlog.org/)
- prometheus-client 0.24.1 — confirmed via [PyPI](https://pypi.org/project/prometheus-client/) (published 2026-01-14)
- uvicorn 0.42.0 — confirmed via [PyPI](https://pypi.org/project/uvicorn/) (released 2026-03-16)
- httpx 0.28.1 — confirmed via [PyPI](https://pypi.org/project/httpx/)

---

## Architecture Patterns

### Recommended Project Structure (additions only)

```
src/
├── adapters/
│   ├── driven/                        # Already exists (Phase 2)
│   │   ├── event_bus/publisher.py
│   │   └── sqlite/
│   └── driving/                       # NEW in Phase 3
│       └── fastapi/
│           ├── __init__.py
│           ├── app.py                 # FastAPI app + lifespan
│           ├── routes/
│           │   ├── __init__.py
│           │   ├── webhook.py         # POST /webhooks/nango
│           │   └── health.py         # GET /health
│           ├── dependencies.py        # verify_signature, get_handler deps
│           ├── schemas.py             # Pydantic DTOs for Nango payload
│           └── middleware.py          # Correlation ID middleware
├── config/
│   ├── __init__.py
│   └── settings.py                   # Pydantic Settings (env vars)
└── observability/
    ├── __init__.py
    ├── logging.py                    # structlog configuration
    └── metrics.py                    # Counter/Histogram definitions
```

### Pattern 1: Raw-Bytes Signature Verification Dependency

**What:** FastAPI dependency that reads the raw request body bytes, computes HMAC-SHA256, and compares with `X-Nango-Hmac-Sha256` header before any route logic runs.

**When to use:** Always on the `/webhooks/nango` POST route. Must run before JSON parsing.

**Critical rule:** `await request.body()` caches the body — subsequent parsing with `await request.json()` or Pydantic body injection still works after calling `body()` first.

```python
# Source: FastAPI docs + Nango webhook docs
import hashlib
import hmac
import os

from fastapi import Depends, Header, HTTPException, Request, status

async def verify_nango_signature(
    request: Request,
    x_nango_hmac_sha256: str | None = Header(default=None),
) -> bytes:
    """FastAPI dependency: verify Nango webhook signature on raw bytes.

    Returns the raw body bytes so route handlers can parse JSON.
    Raises 401 if signature is missing or invalid.
    """
    raw_body = await request.body()  # Caches body; JSON parsing still works

    secret = os.environ["NANGO_WEBHOOK_SECRET"]
    expected = hmac.new(
        secret.encode(),
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    if not x_nango_hmac_sha256 or not hmac.compare_digest(
        expected, x_nango_hmac_sha256
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "invalid_signature"},
        )

    return raw_body
```

### Pattern 2: Fast-Ack + BackgroundTasks

**What:** Route handler returns 202 immediately, then processes the webhook payload in a BackgroundTask that runs after the response is sent.

**When to use:** Every sync webhook. Nango's 20-second timeout makes this mandatory.

**Key constraint:** BackgroundTasks run in the same process and event loop — they are NOT isolated. If the server shuts down mid-processing, the task is lost. This is acceptable for v1 (v2 will add dead letter queue).

```python
# Source: FastAPI BackgroundTasks docs
from fastapi import APIRouter, BackgroundTasks, Depends
from .dependencies import verify_nango_signature
from .schemas import NangoSyncWebhook

router = APIRouter()

@router.post("/webhooks/nango", status_code=202)
async def nango_webhook(
    background_tasks: BackgroundTasks,
    raw_body: bytes = Depends(verify_nango_signature),
    handler: AddDataHandler = Depends(get_add_data_handler),
) -> dict:
    """Receive Nango webhook, ack immediately, process in background."""
    import json
    payload = json.loads(raw_body)
    webhook_type = payload.get("type", "unknown")

    if webhook_type != "sync":
        # Unknown/unsupported types: ack and ignore (per Nango docs)
        logger.info("webhook_type_ignored", webhook_type=webhook_type)
        return {"status": "accepted"}

    background_tasks.add_task(process_sync_webhook, payload, handler)
    return {"status": "accepted"}
```

### Pattern 3: structlog with contextvars for Correlation IDs

**What:** Middleware clears and binds `correlation_id` per request using `structlog.contextvars`. All log calls within that request automatically include it.

**When to use:** Add middleware to the FastAPI app during app initialization.

```python
# Source: structlog.contextvars docs (structlog 25.5.0)
import structlog
from structlog.contextvars import bind_contextvars, clear_contextvars

# Configuration (call once at app startup)
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,   # MUST be first
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

# Middleware
@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    clear_contextvars()
    correlation_id = request.headers.get("x-correlation-id", str(uuid4()))
    bind_contextvars(correlation_id=correlation_id, path=request.url.path)
    response = await call_next(request)
    response.headers["x-correlation-id"] = correlation_id
    return response
```

### Pattern 4: FastAPI Lifespan for DB Connection Pool

**What:** `asynccontextmanager` lifespan creates the SQLAlchemy engine (and session factory) once at startup, disposes on shutdown. Stored in `app.state` for injection.

**When to use:** Replaces deprecated `@app.on_event("startup")` pattern — lifespan is the current standard.

```python
# Source: FastAPI lifespan events docs
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    engine = create_async_engine(settings.database_url)
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)
    yield
    # Shutdown
    await engine.dispose()

app = FastAPI(lifespan=lifespan)
```

### Pattern 5: Nango Sync Webhook Payload Structure

**What:** Nango sends different payload shapes for `sync`, `auth`, and `forward` webhook types. Only `sync` type is processed.

**Nango sync success payload fields:**
```json
{
  "type": "sync",
  "connectionId": "conn_123",
  "providerConfigKey": "hubspot",
  "syncName": "contacts",
  "model": "contact",
  "responseResults": {"added": 5, "updated": 2, "deleted": 0},
  "syncType": "INCREMENTAL",
  "modifiedAfter": "2024-01-15T10:00:00.000Z",
  "queryTimeMs": 450
}
```

**Note:** The `modifiedAfter` timestamp should be stored as a bookmark per connection for delta sync. Individual records are retrieved via the Nango SDK, not directly in the webhook payload.

**Note:** The webhook payload does NOT contain the actual data records. It is a notification that records are ready to fetch via the Nango SDK. For this v1 implementation, the handler creates an `AddDataCommand` from the webhook metadata itself (connectionId, model, etc.) — not fetching from Nango.

### Pattern 6: Metrics with prometheus-client

**What:** Define counters and histograms at module level (singleton per process). Expose via `/metrics` endpoint or access programmatically.

```python
# Source: prometheus/client_python docs
from prometheus_client import Counter, Histogram, REGISTRY
from prometheus_client.exposition import generate_latest

webhooks_received = Counter(
    "webhooks_received_total",
    "Total webhooks received",
    ["type"],  # label: sync, auth, forward, unknown
)
validation_failures = Counter(
    "validation_failures_total",
    "Total validation failures",
    ["schema_name"],
)
records_added = Counter(
    "records_added_total",
    "Total records added successfully",
)
processing_latency = Histogram(
    "processing_latency_seconds",
    "Webhook processing latency",
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],  # p50/p95/p99 visibility
)
```

### Anti-Patterns to Avoid

- **Parsing JSON before signature check:** Always call `request.body()` first, signature check, then parse. Never inject a Pydantic body model directly — it parses before your dependency can check.
- **Putting business logic in the route:** The route handler should only: (a) verify signature via dependency, (b) parse webhook type, (c) enqueue background task, (d) return 202. All processing goes in the background task function.
- **Calling `request.body()` after consuming stream:** FastAPI caches the body after first `request.body()` call — this is safe to call multiple times.
- **Using `@app.on_event("startup")`:** Deprecated since FastAPI 0.93. Use lifespan context manager instead.
- **Global mutable state for correlation IDs:** Use `structlog.contextvars`, not thread-locals or global variables — thread-locals break with async.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HMAC constant-time comparison | Custom string comparison | `hmac.compare_digest()` | Timing attack prevention; custom comparison leaks information |
| JSON structured logs | Custom JSON formatter | structlog + `JSONRenderer()` | Processor chain, stdlib integration, contextvars — 1000+ edge cases |
| Request-scoped context | Thread-local storage | `structlog.contextvars` | Thread-locals break under async; contextvars is async-safe |
| Metrics p50/p95/p99 | Custom percentile computation | `prometheus_client.Histogram` | Prometheus histogram handles bucket aggregation correctly |
| ASGI middleware | Custom ASGI app wrapper | `BaseHTTPMiddleware` + `add_middleware()` | Starlette handles exception propagation, content encoding, etc. |

**Key insight:** The raw-bytes signature pattern looks simple but has multiple failure modes (body encoding, header parsing, timing attacks). Use `hmac.compare_digest()` and `hashlib.sha256` from stdlib — they handle all edge cases.

---

## Common Pitfalls

### Pitfall 1: Signature Verification on Parsed Body
**What goes wrong:** Computing HMAC on `json.dumps(await request.json())` instead of `await request.body()`. The signatures will never match because JSON serialization changes whitespace and key ordering.
**Why it happens:** Intuitive to work with dicts; raw bytes feel low-level.
**How to avoid:** Always `await request.body()` first, then compute HMAC, then parse.
**Warning signs:** Tests pass with hardcoded payloads but fail with real Nango webhooks.

### Pitfall 2: BackgroundTask Loses structlog Context
**What goes wrong:** Background task function runs after the request completes. The structlog `contextvars` context is cleared at the start of the next request — the background task may have lost its correlation_id.
**Why it happens:** `contextvars` are copied into background tasks at the time `add_task()` is called — this is actually safe in Python's contextvars module (tasks inherit a copy of the context). However, explicit re-binding in the task function is safer and clearer.
**How to avoid:** Pass `correlation_id` as an explicit argument to the background task function and re-bind at the start.
**Warning signs:** Background task logs appear with wrong or missing correlation_id.

### Pitfall 3: FastAPI Dependency Injection with `request.body()` and Body Models
**What goes wrong:** If you declare `payload: NangoWebhookPayload` as a Pydantic body parameter alongside `raw_body: bytes = Depends(verify_signature)`, FastAPI will parse the body as JSON before your dependency runs.
**Why it happens:** FastAPI resolves body parameters before calling dependencies that read the body.
**How to avoid:** Use `raw_body: bytes = Depends(verify_signature)` and parse JSON manually inside the route or background task. Do NOT use Pydantic body injection on the webhook endpoint.
**Warning signs:** `await request.body()` returns empty bytes inside the dependency.

### Pitfall 4: pytest-asyncio with Lifespan Events
**What goes wrong:** `AsyncClient(transport=ASGITransport(app=app))` does not trigger FastAPI's lifespan events. The DB engine is never initialized, causing `AttributeError` on `app.state`.
**Why it happens:** ASGITransport doesn't call lifespan by default in httpx.
**How to avoid:** Use `async with AsyncClient(app=app, base_url="http://test") as client:` — the context manager form triggers lifespan. Alternatively, use `asgi-lifespan` library with `LifespanManager`.
**Warning signs:** `AttributeError: 'State' object has no attribute 'engine'` in tests.

### Pitfall 5: prometheus-client Registry Collision in Tests
**What goes wrong:** Defining Prometheus metrics at module level causes `ValueError: Duplicated timeseries` when tests import the metrics module multiple times.
**Why it happens:** The default registry is a process-level singleton; re-importing redefines the same metrics.
**How to avoid:** Use a custom registry in tests, or check `if not hasattr(REGISTRY, '_names_to_collectors')`. Better: use `CollectorRegistry(auto_describe=True)` for test isolation.
**Warning signs:** `ValueError: Duplicated timeseries in CollectorRegistry` in test output.

### Pitfall 6: Nango Webhook Data vs. Notification
**What goes wrong:** Treating the Nango sync webhook payload as containing the actual data records. The payload only contains counts (`responseResults.added`, etc.) and connection metadata.
**Why it happens:** Unclear documentation; tempting to process inline.
**How to avoid:** For v1, create `AddDataCommand` from the webhook metadata itself (use `connectionId` as `source_id`, `model` as `table`, webhook payload as `raw_data`). Actual record fetching via Nango SDK is a Phase 4 concern.
**Warning signs:** Trying to iterate over records in the webhook JSON.

---

## Code Examples

### Full Webhook Route with Signature Dependency

```python
# src/adapters/driving/fastapi/routes/webhook.py
import hashlib
import hmac
import json
import time
from uuid import uuid4

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request, status

from src.kernel.handlers.add_data_handler import AddDataHandler
from src.kernel.commands.add_data import AddDataCommand
from src.kernel.domain.models import CorrelationContext
from src.kernel.exceptions import ValidationError, SchemaNotFoundError
from src.observability.metrics import (
    webhooks_received, validation_failures, records_added, processing_latency
)
from .dependencies import get_add_data_handler, verify_nango_signature

logger = structlog.get_logger()
router = APIRouter()


@router.post("/webhooks/nango", status_code=202)
async def nango_webhook(
    background_tasks: BackgroundTasks,
    raw_body: bytes = Depends(verify_nango_signature),
    handler: AddDataHandler = Depends(get_add_data_handler),
) -> dict:
    payload = json.loads(raw_body)
    webhook_type = payload.get("type", "unknown")
    webhooks_received.labels(type=webhook_type).inc()

    if webhook_type != "sync":
        logger.info("webhook_ignored", webhook_type=webhook_type)
        return {"status": "accepted"}

    background_tasks.add_task(
        _process_sync_webhook,
        payload=payload,
        handler=handler,
        correlation_id=str(uuid4()),
    )
    return {"status": "accepted"}


async def _process_sync_webhook(
    payload: dict,
    handler: AddDataHandler,
    correlation_id: str,
) -> None:
    """Background task: process a sync webhook after 202 is returned."""
    from structlog.contextvars import bind_contextvars, clear_contextvars
    clear_contextvars()
    bind_contextvars(correlation_id=correlation_id, phase="background")

    start = time.monotonic()
    command = AddDataCommand(
        table=payload.get("model", "unknown"),
        source_id=payload.get("connectionId", "unknown"),
        schema_name=payload.get("model", "unknown"),
        raw_data=payload,
        correlation=CorrelationContext(source="nango_webhook"),
    )

    try:
        await handler.handle(command)
        records_added.inc()
        logger.info("webhook_processed_ok", model=command.table)
    except ValidationError as exc:
        validation_failures.labels(schema_name=exc.schema_name).inc()
        logger.warning(
            "validation_failure",
            schema_name=exc.schema_name,
            source_id=command.source_id,
            error_fields=[e.field_path for e in exc.errors],
            error_count=len(exc.errors),
        )
    except Exception:
        logger.exception("webhook_processing_error")
    finally:
        processing_latency.observe(time.monotonic() - start)
```

### Health Check Endpoint

```python
# src/adapters/driving/fastapi/routes/health.py
import structlog
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from src.config.settings import settings

logger = structlog.get_logger()
router = APIRouter()


@router.get("/health")
async def health_check(request: Request) -> JSONResponse:
    """Health check with DB connectivity test."""
    try:
        async with request.app.state.engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return JSONResponse(
            status_code=200,
            content={"status": "ok", "version": settings.version},
        )
    except Exception:
        logger.exception("health_check_db_failed")
        return JSONResponse(status_code=503, content={"status": "error"})
```

### Pydantic Settings

```python
# src/config/settings.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    nango_webhook_secret: str
    database_url: str = "sqlite+aiosqlite:///./data.db"
    env: str = "production"
    version: str = "1.0.0"
    log_level: str = "INFO"

    class Config:
        env_file = ".env"

settings = Settings()
```

**Note:** `pydantic-settings` is included with `fastapi[standard]`. No separate install needed.

### Integration Test Pattern

```python
# tests/integration/test_webhook.py
import hashlib
import hmac
import json
import pytest
from httpx import ASGITransport, AsyncClient

from src.adapters.driving.fastapi.app import app

WEBHOOK_SECRET = "test_secret"

def make_signature(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


@pytest.fixture
async def client(monkeypatch):
    monkeypatch.setenv("NANGO_WEBHOOK_SECRET", WEBHOOK_SECRET)
    async with AsyncClient(app=app, base_url="http://test") as c:
        yield c


async def test_webhook_accepts_valid_signature(client):
    payload = {"type": "sync", "connectionId": "conn_1", "model": "contact"}
    body = json.dumps(payload).encode()
    sig = make_signature(body, WEBHOOK_SECRET)

    response = await client.post(
        "/webhooks/nango",
        content=body,
        headers={"x-nango-hmac-sha256": sig, "content-type": "application/json"},
    )
    assert response.status_code == 202


async def test_webhook_rejects_invalid_signature(client):
    body = b'{"type": "sync"}'
    response = await client.post(
        "/webhooks/nango",
        content=body,
        headers={"x-nango-hmac-sha256": "bad_sig"},
    )
    assert response.status_code == 401
    assert response.json() == {"detail": {"error": "invalid_signature"}}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `@app.on_event("startup")` | `@asynccontextmanager async def lifespan(app)` | FastAPI 0.93 | `on_event` deprecated; lifespan pairs startup/shutdown cleanly |
| Thread-local storage for request context | `structlog.contextvars` | Python 3.7+ | Thread-locals silently break in async; contextvars are async-safe |
| `TestClient` for all tests | `AsyncClient(app=app)` via httpx | FastAPI 0.87 | TestClient blocks; AsyncClient works in async test functions |
| `structlog` version 24.x | structlog 25.5.0 | Oct 2025 | Version number tracks year; API is stable |

**Deprecated/outdated:**
- `@app.on_event("startup")` / `@app.on_event("shutdown")`: Use `lifespan=` parameter instead.
- `structlog.dev.ConsoleRenderer` in production: Use `JSONRenderer` in non-dev environments.
- `hmac.new(key, msg, digestmod).hexdigest()` as string comparison with `==`: Use `hmac.compare_digest()` always.

---

## Open Questions

1. **Schema registry for webhook payloads**
   - What we know: `AddDataHandler.handle()` calls `validate_or_raise(command.schema_name, ...)`, which looks up the schema by name from `SchemaRegistry`.
   - What's unclear: For v1, the `schema_name` comes from the Nango webhook `model` field. There must be registered schemas for each model name. The `FakeSchemaRegistry` in tests uses `contact` and `product` schemas.
   - Recommendation: Phase 3 should include a `FileSchemaRegistry` or `HardcodedSchemaRegistry` adapter that pre-registers known Nango models. Alternatively, treat validation failure gracefully (202 + log) and add real schemas in Phase 4. The CONTEXT.md decision to return 202 on validation failure (not 500) makes this safe to defer.

2. **prometheus-client vs. in-memory counters**
   - What we know: User decision is "Claude's discretion." OBSV-03 says metrics are "tracked and queryable."
   - What's unclear: Whether a `/metrics` Prometheus endpoint is needed, or just queryable via internal state.
   - Recommendation: Use `prometheus-client` with a `/metrics` endpoint. This is the standard and costs nothing extra. It makes the metrics queryable without running a Prometheus server — you can `curl /metrics` directly.

3. **`httpx` vs. `requests` for test AsyncClient**
   - What we know: `httpx` is the standard; tests use `ASGITransport`. The project currently has no `httpx` installed.
   - What's unclear: None — `httpx` is the clear choice.
   - Recommendation: `uv add --dev httpx>=0.28.1`.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 + pytest-asyncio 1.3.0 |
| Config file | `pyproject.toml` (`asyncio_mode = "auto"`) |
| Quick run command | `uv run pytest tests/integration/test_webhook.py -x -q` |
| Full suite command | `uv run pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TRAN-01 | POST /webhooks/nango returns 202 for valid sync webhook | integration | `uv run pytest tests/integration/test_webhook.py::test_webhook_accepts_valid_signature -x` | ❌ Wave 0 |
| TRAN-02 | Response returned before background task completes | integration | `uv run pytest tests/integration/test_webhook.py::test_webhook_fast_ack -x` | ❌ Wave 0 |
| TRAN-03 | Invalid signature → 401; missing header → 401 | integration | `uv run pytest tests/integration/test_webhook.py::test_webhook_rejects_invalid_signature -x` | ❌ Wave 0 |
| TRAN-04 | GET /health returns 200 with DB up, 503 with DB down | integration | `uv run pytest tests/integration/test_health.py -x` | ❌ Wave 0 |
| OBSV-01 | correlation_id appears in all log entries for a request | unit | `uv run pytest tests/unit/test_logging.py::test_correlation_id_in_logs -x` | ❌ Wave 0 |
| OBSV-02 | ValidationError logs schema_name, field_paths, source_id | unit | `uv run pytest tests/unit/test_logging.py::test_validation_failure_logging -x` | ❌ Wave 0 |
| OBSV-03 | webhooks_received_total increments; histogram records latency | unit | `uv run pytest tests/unit/test_metrics.py -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/unit/ -q`
- **Per wave merge:** `uv run pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/integration/test_webhook.py` — covers TRAN-01, TRAN-02, TRAN-03
- [ ] `tests/integration/test_health.py` — covers TRAN-04
- [ ] `tests/unit/test_logging.py` — covers OBSV-01, OBSV-02
- [ ] `tests/unit/test_metrics.py` — covers OBSV-03
- [ ] Install new dependencies: `uv add "fastapi[standard]>=0.135.1" "uvicorn>=0.42.0" "structlog>=25.5.0" "prometheus-client>=0.24.1" && uv add --dev "httpx>=0.28.1"`

---

## Sources

### Primary (HIGH confidence)

- [Nango Webhook Docs](https://nango.dev/docs/implementation-guides/platform/webhooks-from-nango) — payload structure, signature header `X-Nango-Hmac-Sha256`, retry behavior (2 retries, 100ms exponential), 20s timeout, `modifiedAfter` bookmark
- [FastAPI BackgroundTasks docs](https://fastapi.tiangolo.com/tutorial/background-tasks/) — add_task pattern, runs after response sent, not for heavy computation
- [FastAPI Lifespan Events docs](https://fastapi.tiangolo.com/advanced/events/) — `@asynccontextmanager`, `lifespan=` param, `app.state` storage
- [FastAPI Async Tests docs](https://fastapi.tiangolo.com/advanced/async-tests/) — `ASGITransport`, `AsyncClient`, lifespan trigger via context manager
- [FastAPI Middleware docs](https://fastapi.tiangolo.com/advanced/middleware/) — `BaseHTTPMiddleware`, `add_middleware()`, `request.state`
- [structlog contextvars docs](https://www.structlog.org/en/stable/contextvars.html) — `bind_contextvars`, `clear_contextvars`, `merge_contextvars` processor
- [structlog stdlib integration docs](https://www.structlog.org/en/stable/standard-library.html) — production JSON configuration, processor chain
- [prometheus-client PyPI](https://pypi.org/project/prometheus-client/) — version 0.24.1, Counter, Histogram, generate_latest

### Secondary (MEDIUM confidence)

- [Svix FastAPI webhook guide](https://www.svix.com/guides/receiving/receive-webhooks-with-python-fastapi/) — raw body pattern, `await request.body()`, `status.HTTP_401_UNAUTHORIZED`
- [WebSearch: prometheus-client 0.24.1](https://libraries.io/pypi/prometheus-client) — confirmed published 2026-01-14
- [WebSearch: uvicorn 0.42.0](https://pypi.org/project/uvicorn/) — confirmed released 2026-03-16

### Tertiary (LOW confidence — flag for validation)

- WebSearch findings on BackgroundTask contextvars inheritance — verify behavior empirically in tests; Python contextvars spec says tasks copy context at creation time, but confirm with `structlog.contextvars` behavior.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — versions confirmed via PyPI and official docs
- Architecture: HIGH — patterns from official FastAPI and structlog docs
- Nango payload structure: HIGH — from official Nango implementation guide
- Pitfalls: MEDIUM — signature verification pitfalls from multiple webhook provider guides; BackgroundTask contextvars from Python spec
- Metrics design: HIGH — prometheus-client is the standard, API is stable

**Research date:** 2026-03-18
**Valid until:** 2026-04-18 (stable libraries; FastAPI and structlog rarely make breaking changes in patch versions)
