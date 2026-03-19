# External Integrations

**Analysis Date:** 2026-03-18

## APIs & External Services

**Nango Integration:**
- Service: Nango data synchronization platform
- What it's used for: Webhook ingestion of synchronized data from external integrations (CRM, accounting systems, etc.)
- SDK/Client: HMAC-SHA256 signature verification (built-in via stdlib hashlib)
- Auth: Webhook signature via `nango_webhook_secret` environment variable
- Endpoint: `POST /webhooks/nango` - Receives sync, auth, and forward webhook events
- Location: `src/adapters/driving/fastapi/routes/webhook.py` implements webhook handler
- Signature Verification: `src/adapters/driving/fastapi/dependencies.py:verify_nango_signature()` validates HMAC header `x-nango-hmac-sha256`
- Webhook Types Supported:
  - `sync` - Data synchronization events (processed in background)
  - `auth` - Authentication events (acknowledged but not processed)
  - `forward` - Forward sync events (acknowledged but not processed)
  - `unknown` - Unknown types (logged at INFO level, not processed)

## Data Storage

**Databases:**
- SQLite with aiosqlite async driver
  - Connection: `sqlite+aiosqlite:///./data.db` (default via `DATABASE_URL` env var)
  - Client: SQLAlchemy async ORM with async_sessionmaker
  - Configuration: `alembic.ini` defines SQLite connection and migration paths
  - Models: Two tables defined in `src/adapters/driven/sqlite/models.py`
    - `data_records` - Persisted webhook payload data with unique event_id index
    - `audit_log` - Audit trail of all data operations (added/duplicate status)
  - Async Session Management: Configured in FastAPI lifespan (`src/adapters/driving/fastapi/app.py`)
  - Migrations: Managed by Alembic (`migrations/` directory) for schema versioning

**File Storage:**
- Local filesystem only - SQLite database file (`data.db`) stored in project root
- No external blob storage (S3, GCS, etc.)

**Caching:**
- None - In-memory event publisher only (for testing phase)
- Location: `src/adapters/driven/event_bus/publisher.py:InMemoryEventPublisher` stores events in-memory list

## Authentication & Identity

**Auth Provider:**
- Custom HMAC-SHA256 webhook signature verification (no external identity provider)
- Implementation: Dependency injection pattern in `src/adapters/driving/fastapi/dependencies.py`
- Verification Process:
  1. Extract raw request body before JSON parsing
  2. Compute HMAC-SHA256 using `nango_webhook_secret` from environment
  3. Compare with `x-nango-hmac-sha256` header using constant-time comparison (prevents timing attacks)
  4. Return 401 Unauthorized if signature mismatch
- Location: `src/adapters/driving/fastapi/dependencies.py:verify_nango_signature()`

## Monitoring & Observability

**Error Tracking:**
- None (errors logged to stdout/stderr with structured logging)
- Exception details captured in logs via `structlog.exception()` calls

**Logs:**
- Structured JSON logging via structlog library
- Log Configuration: `src/observability/logging.py:configure_logging()`
- Correlation IDs: Request-scoped context variables automatically propagated through async handling
  - Set by middleware: `src/adapters/driving/fastapi/middleware.py:CorrelationIdMiddleware`
  - Re-bound in background tasks for traceability across async boundaries
  - Echo back to client via `x-correlation-id` response header
- Environment-specific output:
  - Development: Pretty-printed console output with colors
  - Staging/Production: JSON format for log aggregation systems
- Sensitive Data Handling: Full payloads logged only in development; production logs only error field paths

**Metrics:**
- Prometheus-compatible metrics via prometheus-client library
- Export Endpoint: `GET /metrics` exposes metrics in Prometheus text format
- Location: `src/observability/metrics.py` defines all metrics
- Metrics Collected:
  - `webhooks_received_total` - Counter with webhook type label (sync, auth, forward, unknown)
  - `validation_failures_total` - Counter with schema_name label
  - `records_added_total` - Counter of successfully persisted records
  - `processing_latency_seconds` - Histogram with buckets [0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
- Scraping: Compatible with Prometheus, Grafana, and Kubernetes monitoring

## CI/CD & Deployment

**Hosting:**
- Self-hosted or any ASGI-compatible platform (Docker, Kubernetes, Cloud Run, etc.)
- No cloud provider-specific integrations

**CI Pipeline:**
- None detected in codebase (no GitHub Actions, GitLab CI, Jenkins configs present)

**Deployment:**
- ASGI Application: FastAPI app at `src/adapters/driving/fastapi/app.py:app`
- Server Command: `uvicorn src.adapters.driving.fastapi.app:app --host 0.0.0.0 --port 8000`
- Multi-process: Use Gunicorn with Uvicorn workers: `gunicorn -w 4 -k uvicorn.workers.UvicornWorker src.adapters.driving.fastapi.app:app`

## Environment Configuration

**Required env vars:**
- `NANGO_WEBHOOK_SECRET` - HMAC secret for Nango webhook verification (critical, no default)

**Optional env vars:**
- `DATABASE_URL` - SQLAlchemy connection string (default: `sqlite+aiosqlite:///./data.db`)
- `ENV` - Environment name for feature toggling (default: `production`, valid values: `development`, `staging`, `production`)
- `LOG_LEVEL` - Python logging level (default: `INFO`, valid values: `DEBUG`, `INFO`, `WARNING`, `ERROR`)
- `VERSION` - Application version string (default: `1.0.0`, used in health check response)

**Secrets location:**
- Loaded from `.env` file via pydantic-settings (path: `.env`)
- `.env` file is git-ignored (not committed to repository)
- Secrets in environment variables override `.env` file values

## Webhooks & Callbacks

**Incoming Webhooks:**
- `POST /webhooks/nango` - Nango sync webhook endpoint
  - Fast-ack pattern: Returns 202 Accepted immediately, processes in background
  - Signature verification: Required header `x-nango-hmac-sha256`
  - Response: `{"status": "accepted"}` (always 202, even on validation errors)
  - Implementation: `src/adapters/driving/fastapi/routes/webhook.py:nango_webhook()`
  - Background Processing: `src/adapters/driving/fastapi/routes/webhook.py:_process_sync_webhook()`

**Outgoing Webhooks/Events:**
- None - No external webhook callbacks configured
- Internal Event Publishing: In-memory event bus for domain events
  - Location: `src/adapters/driven/event_bus/publisher.py:InMemoryEventPublisher`
  - Events Published: `DataAddedEvent` (defined in kernel domain models)
  - Future Extension: Phase 3 may add structured event logging or external event streaming

## Health & Readiness Checks

**Health Endpoint:**
- `GET /health` - Service health check including database connectivity
- Response: `{"status": "ok", "version": "1.0.0"}` (200 OK) or `{"status": "error"}` (503 Service Unavailable)
- Implementation: `src/adapters/driving/fastapi/routes/health.py`
- Database Test: Lightweight `SELECT 1` query on each health check
- Details: No sensitive information exposed (connection strings, etc. never in response)

---

*Integration audit: 2026-03-18*
