---
phase: 03-webhook-transport-observability
plan: 02
subsystem: observability
tags: [structlog, correlation-id, structured-logging, json-logging, middleware, fastapi, contextvars]

requires:
  - phase: 03-01
    provides: FastAPI app with webhook endpoint, lifespan, dependency injection pattern

provides:
  - structlog configured with JSON output (production) and console renderer (development)
  - CorrelationIdMiddleware binding correlation_id to every request via contextvars
  - Webhook route with full OBSV-01/OBSV-02 structured logging (validation failure context)
  - Integration tests verifying x-correlation-id header propagation

affects:
  - 03-03 (metrics plan will add prometheus counters alongside these log calls)

tech-stack:
  added: []
  patterns:
    - structlog contextvars for request-scoped correlation IDs (async-safe)
    - CorrelationIdMiddleware clears and re-binds context per request
    - Background tasks re-bind correlation_id explicitly (prevent context loss)
    - Environment-aware logging: JSONRenderer in prod, ConsoleRenderer in dev
    - dict[str, Any] for JSON payload types throughout webhook route

key-files:
  created:
    - src/observability/__init__.py
    - src/observability/logging.py
    - src/adapters/driving/fastapi/middleware.py
    - tests/integration/test_logging.py
  modified:
    - src/adapters/driving/fastapi/app.py
    - src/adapters/driving/fastapi/routes/webhook.py

key-decisions:
  - "structlog contextvars used over thread-locals — thread-locals break under async, contextvars are async-safe"
  - "Background tasks explicitly re-bind correlation_id via clear_contextvars() + bind_contextvars() — prevents context inheritance issues"
  - "should_log_full_payload() gates data_sample logging to development env only — protects sensitive data in production"
  - "dict[str, Any] for JSON payload type annotations — correct for heterogeneous JSON values"

patterns-established:
  - "Observability pattern: get_logger(__name__) at module level, bind_contextvars in middleware"
  - "Background task logging: always clear and re-bind context at task start"

requirements-completed: [OBSV-01, OBSV-02]

duration: 8min
completed: 2026-03-18
---

# Phase 03 Plan 02: Structured Logging with Correlation IDs Summary

**structlog JSON logging with per-request correlation IDs via contextvars middleware, validation failure context logging (OBSV-01, OBSV-02)**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-18T23:48:00Z
- **Completed:** 2026-03-18T23:56:00Z
- **Tasks:** 5
- **Files modified:** 6

## Accomplishments

- structlog configured with JSON output in production and colorful console renderer in development, using contextvars for zero-overhead request-scoped state
- CorrelationIdMiddleware extracts or generates UUID correlation ID per request, binds to structlog contextvars, echoes in response headers
- Webhook route logs all events (receipt, ignored, background processing, success, validation failure, schema error) with structured fields per OBSV-01/OBSV-02
- 4 new integration tests verify x-correlation-id header presence and propagation, 69 total tests passing

## Task Commits

Each task was committed atomically:

1. **Task 1: Create structlog configuration module** - `1074088` (feat)
2. **Task 2: Create correlation ID middleware** - `4a774fb` (feat)
3. **Task 3: Update FastAPI app to configure logging and add middleware** - `e7a2b61` (feat)
4. **Task 4: Update webhook route with structured logging** - `333d978` (feat)
5. **Task 5: Create integration tests for correlation ID and validation logging** - `212ed6e` (test)

## Files Created/Modified

- `src/observability/__init__.py` - Module exports configure_logging and get_logger
- `src/observability/logging.py` - structlog configuration with JSON/console renderers, should_log_full_payload()
- `src/adapters/driving/fastapi/middleware.py` - CorrelationIdMiddleware using BaseHTTPMiddleware
- `src/adapters/driving/fastapi/app.py` - Added configure_logging() in lifespan, configure_middleware() adds CorrelationIdMiddleware
- `src/adapters/driving/fastapi/routes/webhook.py` - Full structured logging: webhook_received, webhook_ignored, validation_failure, schema_not_found, webhook_processing_error
- `tests/integration/test_logging.py` - 4 integration tests for OBSV-01 and OBSV-02

## Decisions Made

- **structlog contextvars over thread-locals:** Thread-locals silently break under async; contextvars are the async-safe standard per Python 3.7+
- **Background task re-binds context explicitly:** Passing correlation_id as argument and calling clear_contextvars() + bind_contextvars() at task start prevents context inheritance issues and makes the intent clear
- **dict[str, Any] for JSON payload:** Proper type annotation for heterogeneous JSON-parsed dictionaries; required for correct pyright/pylance analysis

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed incomplete type annotations on dict parameters**
- **Found during:** Task 4 (webhook route implementation)
- **Issue:** IDE diagnostics reported `dict` without type arguments causing type errors throughout the file; `log_kwargs` dict had narrow inferred value types preventing `dict[str, Any]` assignment
- **Fix:** Added `from typing import Any` import; typed `payload` as `dict[str, Any]`, `log_kwargs` as `dict[str, Any]`, `_truncate_payload` parameters and return as `dict[str, Any]`
- **Files modified:** src/adapters/driving/fastapi/routes/webhook.py
- **Verification:** All IDE diagnostics resolved; import test passes; 69 tests green
- **Committed in:** `333d978` (Task 4 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - type annotation bug)
**Impact on plan:** Fix required for type correctness; no scope creep, no behavioral change.

## Issues Encountered

None beyond the type annotation fix documented above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Logging infrastructure complete; Plan 03-03 can add prometheus metrics counters alongside these log calls
- get_logger() available from src.observability for any new modules
- All 69 tests passing; no regressions from correlation ID middleware addition

---
*Phase: 03-webhook-transport-observability*
*Completed: 2026-03-18*

## Self-Check: PASSED
