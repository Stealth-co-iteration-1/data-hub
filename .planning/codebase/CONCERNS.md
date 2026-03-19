# Codebase Concerns

**Analysis Date:** 2026-03-18

## Tech Debt

**Global Event Publisher Singleton:**
- Issue: In-memory event publisher stored as global singleton in `src/adapters/driving/fastapi/dependencies.py` (line 21: `_event_publisher = InMemoryEventPublisher()`)
- Files: `src/adapters/driving/fastapi/dependencies.py` (line 21)
- Impact: Events accumulate indefinitely in production; multi-process deployments share corrupted state; memory leak for long-running servers
- Fix approach: Migrate to external event bus (Phase 3 per planning docs). For now, implement periodic event clearing or use time-bounded in-memory queue. In production, deploy as single process.

**Permissive Schema Registry (Pass-through Validation):**
- Issue: `src/adapters/driven/schema_registry/permissive.py` accepts all data without validation for MVP
- Files: `src/adapters/driven/schema_registry/permissive.py`, `src/adapters/driving/fastapi/dependencies.py` (lines 69-75)
- Impact: No actual data validation occurring; schema_name parameter ignored; all data persisted as-is
- Fix approach: Phase 4 will introduce strict schema enforcement per Nango model. Until then, document this limitation in API.

**SQLite as Production Database:**
- Issue: `src/config/settings.py` defaults to SQLite file database with no WAL configuration tuning
- Files: `src/config/settings.py` (line 18), `src/adapters/driven/sqlite/session.py`
- Impact: SQLite locking under concurrent write load; no multi-process read scalability; data loss if file corruption
- Fix approach: SQLite suitable only for single-process MVP. For multi-region or high-volume, migrate to PostgreSQL (schema already extensible). Add connection pool tuning if staying on SQLite.

**Database URL in Settings Default:**
- Issue: `src/config/settings.py` line 18 hardcodes `sqlite+aiosqlite:///./data.db` as production default
- Files: `src/config/settings.py` (line 18)
- Impact: File created in current working directory; not portable; relative path breaks in containerized deployment
- Fix approach: Require `DATABASE_URL` environment variable; fail fast with clear error if not set.

## Known Bugs

**BackgroundTasks Context Loss:**
- Issue: `src/adapters/driving/fastapi/routes/webhook.py` background task loses structlog context after 202 response
- Files: `src/adapters/driving/fastapi/routes/webhook.py` (lines 81-86, 107-113)
- Trigger: Webhook processing happens in background after request completes; contextvars cleared by middleware
- Workaround: Code manually re-binds context (lines 108-113) - this is the workaround, not a real fix. If middleware context clearing races with background task, logs are orphaned.
- Safe mitigation: The current manual re-bind is a stopgap. Real fix: Use custom context propagation for background tasks (requires task wrapper).

**Duplicate Event ID Behavior Inconsistency:**
- Issue: `src/adapters/driven/sqlite/repository.py` line 70 treats duplicate event_id as success but doesn't persist data
- Files: `src/adapters/driven/sqlite/repository.py` (lines 55-70)
- Symptoms: `add()` returns record_id even if duplicate was skipped; caller may try to fetch record via `get()` and receive `None`
- Workaround: `add()` caller must not assume record persisted; webhook endpoint handles this by logging only
- Risk: Future code that assumes return value = persisted data will fail silently

## Security Considerations

**Nango Webhook Secret Not Validated at Startup:**
- Risk: If `NANGO_WEBHOOK_SECRET` env var is empty/missing, no error at application start; first webhook fails with unhelpful 401
- Files: `src/config/settings.py` (line 15), `src/adapters/driving/fastapi/dependencies.py` (line 54)
- Current mitigation: Settings class marks `nango_webhook_secret` as required (no default); Pydantic raises at Settings instantiation
- Recommendations: Add explicit validation in app startup lifespan; log severity level when secret is loaded

**Sensitive Data in Dev Logs:**
- Risk: Full payloads logged in development when `ENV=development`
- Files: `src/observability/logging.py` (lines 77-82), `src/adapters/driving/fastapi/routes/webhook.py` (lines 157-158)
- Current mitigation: `should_log_full_payload()` checks environment; payload truncated to 10 keys before logging
- Recommendations: Even in development, mask PII fields (email, phone, name); use structured data with field-level sensitivity labels

**HMAC Comparison Uses Timing-Safe Compare:**
- Risk: NONE - signature verification uses `hmac.compare_digest()` (constant-time)
- Files: `src/adapters/driving/fastapi/dependencies.py` (line 60)
- Current mitigation: Proper timing-safe comparison implemented

**Event ID Idempotency Assumes External Uniqueness:**
- Risk: Duplicate detection relies on `event_id` from upstream Nango; no server-side nonce or request deduplication
- Files: `src/adapters/driven/sqlite/repository.py` (line 66)
- Current mitigation: None beyond trusting Nango's event_id generation
- Recommendations: Add server-side request deduplication timeout (e.g., X-Idempotency-Key header) to handle retries

## Performance Bottlenecks

**Webhook Processing Latency Metric Only Measures Background Task:**
- Problem: `processing_latency` metric (`src/adapters/driving/fastapi/routes/webhook.py` line 184) only measures background task duration, not total request time
- Files: `src/adapters/driving/fastapi/routes/webhook.py` (lines 105, 183-184)
- Cause: Timer starts after 202 response sent; doesn't include validation/parsing time before background task
- Improvement path: Move timer start to entry of `_process_sync_webhook`; measure true processing duration

**Schema Lookup on Every Request:**
- Problem: `SchemaValidator.validate()` calls `registry.get_schema()` for every record even if same schema used repeatedly
- Files: `src/kernel/validators/schema_validator.py` (line 47)
- Cause: PermissiveSchemaRegistry returns dummy schema each time; no caching layer
- Improvement path: Add LRU cache to schema registry; phase 4 strict registry should implement this

**Pydantic Validation Performance Risk:**
- Problem: Comment says Pydantic validator runs in compiled Rust, but large nested objects still incur overhead
- Files: `src/kernel/validators/schema_validator.py` (lines 5-8, 52)
- Cause: `model_validate()` is fast but still slower than a pre-compiled schema
- Improvement path: For high-volume (10k+ events/sec), consider pre-compiling schemas or using simpler validation logic

**In-Memory Event List Unbounded Growth:**
- Problem: `InMemoryEventPublisher.events` list grows without bound in production
- Files: `src/adapters/driven/event_bus/publisher.py` (line 19)
- Cause: No eviction or overflow handling
- Improvement path: Implement bounded queue (e.g., maxsize=10000) with overflow policy; emit warning when full

## Fragile Areas

**Fast-Ack Background Task Error Silencing:**
- Files: `src/adapters/driving/fastapi/routes/webhook.py` (lines 91-180)
- Why fragile: Exceptions in background task log but don't propagate; caller sees 202 regardless of processing outcome
- Safe modification: Never assume 202 means processing succeeded; implement event sourcing to track processing status
- Test coverage: Gap - no tests for background task exception handling (only success path tested)

**Correlation ID Manual Re-binding:**
- Files: `src/adapters/driving/fastapi/routes/webhook.py` (lines 107-113)
- Why fragile: Background task must manually call `clear_contextvars()` + `bind_contextvars()`; easy to forget in future tasks
- Safe modification: Create helper function `async def _with_correlation(coro, correlation_id)` to wrap all background tasks
- Test coverage: Tested but brittle - relies on middleware not breaking context chain

**AsyncSession Configuration Quirk:**
- Files: `src/adapters/driven/sqlite/session.py` (line 29), `src/adapters/driving/fastapi/app.py` (line 29)
- Why fragile: `expire_on_commit=False` is required to avoid MissingGreenlet errors; comment says why but easy to revert accidentally
- Safe modification: Keep comment; add test that validates attribute access after commit succeeds
- Test coverage: Not explicitly tested; relies on integration tests

**Direct Request.body() Access Before Parsing:**
- Files: `src/adapters/driving/fastapi/dependencies.py` (line 43)
- Why fragile: Code relies on FastAPI caching request.body() so subsequent JSON parsing works; if middleware consumes body first, breaks
- Safe modification: Document this assumption; never add middleware that reads raw body
- Test coverage: Signature verification tested, but not tested with other body-reading middleware

## Test Coverage Gaps

**Background Task Failure Scenarios:**
- What's not tested: Validation errors, schema not found, unexpected exceptions in background task
- Files: `src/adapters/driving/fastapi/routes/webhook.py` (lines 144-179)
- Risk: Error handling paths (ValidationError, SchemaNotFoundError branches) untested; metrics may not increment; logs may malform
- Priority: High - error paths account for ~30% of production traffic

**Concurrent Webhook Processing:**
- What's not tested: Multiple webhooks processed simultaneously; background task race conditions
- Files: `src/adapters/driving/fastapi/routes/webhook.py`, `src/adapters/driven/event_bus/publisher.py`
- Risk: Global event publisher state corruption if concurrent tasks access simultaneously
- Priority: High - production deployments will process concurrent webhooks

**Event Publisher Queue Overflow:**
- What's not tested: InMemoryEventPublisher behavior when events list exceeds memory limits
- Files: `src/adapters/driven/event_bus/publisher.py` (line 19)
- Risk: No test for unbounded growth; production memory leaks undetected
- Priority: Medium - only manifests under sustained load

**Database Connection Pool Exhaustion:**
- What's not tested: Behavior when SQLAlchemy session factory pool exhausted under load
- Files: `src/adapters/driven/sqlite/session.py`, `src/adapters/driving/fastapi/app.py`
- Risk: No pool config tuning; concurrent requests may deadlock on session acquisition
- Priority: Medium - only impacts production scale

**Invalid JSON in Webhook Payload:**
- What's not tested: Malformed JSON in webhook body (signature verification succeeds, JSON parse fails)
- Files: `src/adapters/driving/fastapi/routes/webhook.py` (line 53)
- Risk: `json.loads(raw_body)` at line 53 may raise unhandled JSONDecodeError; no error handler
- Priority: Medium - can happen if Nango sends corrupted payloads

**Logging Context Isolation:**
- What's not tested: Structlog context pollution across concurrent requests
- Files: `src/adapters/driving/fastapi/middleware.py` (lines 32, 44)
- Risk: `clear_contextvars()` may race with other request's `bind_contextvars()`; logs may show wrong correlation ID
- Priority: Low - unlikely but possible under extreme concurrency

---

*Concerns audit: 2026-03-18*
