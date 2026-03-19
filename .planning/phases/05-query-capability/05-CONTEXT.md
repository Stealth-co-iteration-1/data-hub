# Phase 5: Query Capability - Context

**Gathered:** 2026-03-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Stored data is queryable via a parameterized SQL interface through both the kernel and an HTTP endpoint. QueryData query in kernel follows CQRS pattern. Both SQLite and PostgreSQL adapters implement query(). Injection prevention via bindparams only, unconditional result limits enforced.

</domain>

<decisions>
## Implementation Decisions

### Query Interface Design
- Simple equality filters only — `{"connection_id": "abc", "status": "active"}`
- No operators ($gt, $in, etc.) for v1 — keep it simple
- Model name as path parameter: `POST /query/{model}`
- Fixed allowlist for filterable fields: `connection_id` and model columns only — no filtering on raw JSON data fields

### HTTP Endpoint Contract
- Paginated envelope response: `{"data": [...], "count": 42, "limit": 100, "has_more": true}`
- Error responses use Problem Details RFC 7807: `{"type": "...", "title": "...", "status": 400, "detail": "..."}`
- No authentication required — internal service, same as /health and /metrics
- Include system fields in results: id, connection_id, model, created_at alongside data payload

### Security Guardrails
- Model name validated via regex allowlist: `^[a-z][a-z0-9_]*$` — prevents injection via model parameter
- Filter values capped at 256 chars max — prevents memory/query explosion
- Queries logged via structlog with correlation_id, model, filter_count — uses existing logging infra
- No rate limiting — internal service behind network boundary, defer to API gateway

### Result Behavior
- Default limit: 100 records
- Maximum limit: 1000 records — cap enforced unconditionally
- No sorting for v1 — default order by id/created_at
- Empty results return 200 with `{"data": [], "count": 0, ...}` — not an error

### Claude's Discretion
- Exact Problem Details type URIs
- Whether to include total_count (expensive COUNT query) vs just has_more
- Prometheus metrics for query endpoint (latency histogram, etc.)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Kernel Protocol
- `src/kernel/ports/repository.py` — DataRepository.query() Protocol signature already defined
- `src/kernel/ports/fake_repository.py` — FakeDataRepository.query() reference implementation
- `src/kernel/commands/add_data.py` — AddDataCommand pattern to follow for QueryData query

### Existing Adapters
- `src/adapters/driven/sqlite/repository.py` — SQLiteDataRepository to extend with query()
- `src/adapters/driven/postgres/repository.py` — PostgresDataRepository to extend with query()
- `src/adapters/driven/repository_factory.py` — Factory pattern for backend selection

### HTTP Layer
- `src/adapters/driving/fastapi/routes/webhook.py` — Route implementation pattern to follow
- `src/adapters/driving/fastapi/routes/health.py` — Simple route example
- `src/adapters/driving/fastapi/dependencies.py` — Dependency injection pattern

### Requirements
- `.planning/REQUIREMENTS.md` — QURY-01 through QURY-06 requirements for this phase

### Architecture
- `.planning/codebase/ARCHITECTURE.md` — Hexagonal architecture, CQRS pattern guidance

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `DataRepository.query()` Protocol — signature already defined: `query(model, filters, limit) -> list[dict]`
- `FakeDataRepository.query()` — working reference implementation for tests
- `CorrelationContext` — observability context for request tracing
- structlog setup — query logging follows existing pattern
- Pydantic schemas — use for request/response validation (WebhookPayload pattern)

### Established Patterns
- CQRS: AddDataCommand for writes, QueryData query for reads
- Dependency injection via FastAPI `request.app.state`
- Repository factory creates correct adapter based on DATABASE_URL
- idempotent insert pattern — query is simpler (read-only)
- BackgroundTasks for async processing — query is sync (return results immediately)

### Integration Points
- `/query/{model}` route registered in FastAPI app
- `get_query_handler()` dependency injects QueryHandler with repository
- Repository.query() called by QueryHandler
- Both SQLite and Postgres adapters implement same interface

</code_context>

<specifics>
## Specific Ideas

- QueryData query follows same pure-kernel pattern as AddDataCommand — no SQLAlchemy imports in kernel
- Problem Details errors give callers machine-readable error types
- Paginated envelope sets up for future cursor-based pagination without breaking changes
- System fields in results let callers correlate with their own data

</specifics>

<deferred>
## Deferred Ideas

- Offset-based pagination — DataRepository.query() Protocol has no offset param; requires port + adapter changes, future phase
- Cursor-based pagination — more stable for large datasets, future phase
- Multi-field sorting — adds complexity, not needed for v1
- Filtering on JSON data fields — needs JSON path validation, future phase
- Rate limiting — defer to API gateway or future phase
- Authentication — add when needed for external access

</deferred>

---

*Phase: 05-query-capability*
*Context gathered: 2026-03-19*
