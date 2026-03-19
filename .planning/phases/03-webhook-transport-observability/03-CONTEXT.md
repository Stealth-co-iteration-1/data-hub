# Phase 3: Webhook Transport & Observability - Context

**Gathered:** 2026-03-18
**Status:** Ready for planning

<domain>
## Phase Boundary

FastAPI driving adapter that receives Nango webhooks, verifies signatures, translates payloads to kernel commands, and provides observability. This phase creates the HTTP transport layer that connects external webhooks to the kernel established in Phase 1 and persistence layer from Phase 2.

</domain>

<decisions>
## Implementation Decisions

### Webhook Handling
- Handle **sync webhooks only** — auth and forward types are acknowledged (202) but not processed
- **Fast-ack + background processing** — return 202 immediately, process via FastAPI BackgroundTasks
- **Signature verification via FastAPI dependency** — reads raw request body, computes HMAC-SHA256 with env secret, compares to `X-Nango-Hmac-Sha256` header, rejects 401 on mismatch
- Nango timeout is 20 seconds — fast ack ensures we never hit it

### Logging Strategy
- **JSON structured logging** via structlog with JSON output
- Each log entry: correlation_id, timestamp, level, message, and context fields
- **Sensitive data handling:** Full payloads logged in dev only (ENV=development), strict redaction in staging/prod
- Log validation error field paths but not values in non-dev environments

### Metrics (OBSV-03)
- **Counters:** webhooks_received_total, validation_failures_total, records_added_total
- **Latency histogram:** processing_latency_seconds with p50/p95/p99 buckets

### Health Check Design
- Single `/health` endpoint
- **Internally tests DB connectivity** — but does NOT expose connection details in response
- Response format: `{"status": "ok", "version": "1.0.0"}` (200) or `{"status": "error"}` (503)

### Error Responses
- **Signature failure:** 401 Unauthorized with `{"error": "invalid_signature"}`, log full details server-side
- **Validation failure:** 202 Accepted (stop retries), log failure with full context per OBSV-02
- **Unknown webhook types:** 202 Accepted, ignore. Log at INFO level. Per Nango docs: "gracefully ignore unknown types"

### Claude's Discretion
- Exact structlog configuration and processors
- Metrics export mechanism (in-memory counters vs Prometheus client)
- FastAPI lifespan setup for DB connection pool
- Exact Pydantic models for webhook payloads

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Nango Webhooks
- `https://nango.dev/docs/implementation-guides/platform/webhooks-from-nango` — Webhook types (sync/auth/forward), payload structure, signature verification (HMAC-SHA256 via X-Nango-Hmac-Sha256), retry behavior (2 retries, 100ms exponential backoff), 20s timeout

### FastAPI Patterns
- `https://fastapi.tiangolo.com/tutorial/` — Request body handling, dependencies for signature verification, BackgroundTasks for async processing, response models, error handling with HTTPException

### Project Architecture
- `.planning/research/ARCHITECTURE.md` — Hexagonal architecture, driving adapter patterns, data flow
- `.planning/research/STACK.md` — FastAPI 0.135.1, structlog 24.0+, Pydantic 2.12.5

### Existing Kernel Code
- `src/kernel/handlers/add_data_handler.py` — Handler to call from webhook endpoint
- `src/kernel/commands/add_data.py` — AddDataCommand structure including CorrelationContext
- `src/kernel/domain/models.py` — CorrelationContext for correlation IDs

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `AddDataHandler` — kernel handler that orchestrates validation, persistence, event publishing
- `AddDataCommand` — command structure with correlation support already built in
- `CorrelationContext` — dataclass for correlation_id and timestamp
- `SQLiteDataRepository` — repository adapter from Phase 2
- `InMemoryEventPublisher` — event publisher adapter from Phase 2

### Established Patterns
- Dependency injection via constructor (handlers receive ports)
- Async/await throughout (repository, handlers)
- Correlation IDs propagated through commands and events

### Integration Points
- FastAPI endpoint creates `AddDataCommand` from webhook payload
- Endpoint calls `AddDataHandler.handle()` with injected repository and event publisher
- Adapter directory structure: `src/adapters/driving/fastapi/` (new)

</code_context>

<specifics>
## Specific Ideas

- Sync webhook `modifiedAfter` timestamp should be stored as bookmark for delta syncs (per Nango docs)
- Webhook endpoint path: `/webhook/nango` or `/webhooks/nango`
- Use FastAPI's `Request.body()` for raw bytes before JSON parsing (required for signature verification)
- Environment variable `NANGO_WEBHOOK_SECRET` for HMAC key

</specifics>

<deferred>
## Deferred Ideas

- Dead letter queue for failed webhooks — v2 requirement (RESL-02)
- Automatic retry with backoff — v2 requirement (RESL-01)
- Auth webhook handling for connection status tracking — could be Phase 4

</deferred>

---

*Phase: 03-webhook-transport-observability*
*Context gathered: 2026-03-18*
