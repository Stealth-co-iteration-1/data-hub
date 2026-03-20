---
phase: "05"
plan: "03"
subsystem: "HTTP query endpoint"
tags: [fastapi, query, http, security, integration-tests]
dependency_graph:
  requires: [05-01, 05-02]
  provides: [POST /query/{model} HTTP endpoint]
  affects: [src/adapters/driving/fastapi]
tech_stack:
  added: []
  patterns: [RFC 7807 Problem Details, FastAPI dependency injection, AsyncClient integration tests, has_more +1 detection]
key_files:
  created:
    - src/adapters/driving/fastapi/routes/query.py
    - tests/integration/test_query_endpoint.py
  modified:
    - src/adapters/driving/fastapi/schemas.py
    - src/adapters/driving/fastapi/dependencies.py
    - src/adapters/driving/fastapi/app.py
decisions:
  - "Test pattern uses AsyncClient + FakeDataRepository via dependency override (matches project pattern, not TestClient/asyncio.get_event_loop)"
  - "Migrated class Config to ConfigDict for Pydantic V2 compliance on new schemas"
  - "has_more detection uses +1 fetch trick; MAX_QUERY_LIMIT boundary limitation documented in code"
metrics:
  duration: "3 min"
  completed_date: "2026-03-20"
  tasks_completed: 5
  files_modified: 5
---

# Phase 05 Plan 03: HTTP Query Endpoint Summary

**One-liner:** POST /query/{model} endpoint with regex model allowlist, 256-char filter cap, Problem Details errors, and paginated envelope response.

---

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create Pydantic schemas | ca654a7 | schemas.py |
| 2 | Add get_query_handler dependency | 5f64b40 | dependencies.py |
| 3 | Create query route with security guardrails | 714dc94 | routes/query.py |
| 4 | Register query route in app | c1fdd4a | app.py |
| 5 | Add query endpoint integration tests | 4c54a60 | test_query_endpoint.py, schemas.py |

---

## What Was Built

- **QueryRequest schema**: `filters: dict[str, str] | None`, `limit: int = 100`, no offset field (deferred per CONTEXT.md)
- **QueryResponse schema**: paginated envelope with `data`, `count`, `limit`, `has_more` (no offset)
- **ProblemDetail schema**: RFC 7807 format with `type`, `title`, `status`, `detail`
- **get_query_handler dependency**: creates `QueryHandler(repository=request.app.state.repository)`
- **POST /query/{model} route**: full security stack — model name regex allowlist (`^[a-z][a-z0-9_]*$`), filter value size cap (256 chars), limit cap at MAX_QUERY_LIMIT (1000), has_more detection
- **13 integration tests**: system fields, connection_id filtering, non-connection_id filter ignore, invalid model, oversized filter, limit cap, empty results, SQL injection prevention, has_more

---

## Decisions Made

1. **Test pattern**: Used `AsyncClient` with ASGI transport and `FakeDataRepository` via `dependency_overrides[get_query_handler]`, matching the existing webhook test pattern. The plan's `TestClient` + `asyncio.get_event_loop()` template was adapted to the project's async test style.

2. **Pydantic ConfigDict**: New schemas used the V2 `ConfigDict` API from the start to avoid deprecation warnings. See Deviation section.

3. **has_more detection**: The `+1 fetch trick` is implemented at the route layer (before the handler caps). When `effective_limit < MAX_QUERY_LIMIT`, we pass `fetch_limit = effective_limit + 1` to the handler. The handler then applies `min(fetch_limit, MAX_QUERY_LIMIT)` — this works correctly for all limits below 1000. The MAX_QUERY_LIMIT boundary limitation is documented in comments as accepted behavior.

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Migrated class-based Config to ConfigDict (Pydantic V2)**

- **Found during:** Task 5 test run
- **Issue:** New schemas (QueryRequest, QueryResponse, ProblemDetail) used `class Config:` inner class, which is deprecated in Pydantic V2 and produces deprecation warnings in test output
- **Fix:** Replaced all three `class Config` blocks with `model_config = ConfigDict(json_schema_extra=...)` at class level
- **Files modified:** `src/adapters/driving/fastapi/schemas.py`
- **Commit:** 4c54a60 (included in Task 5 commit)

**2. Test implementation pattern adapted**

- **Found during:** Task 5
- **Issue:** Plan's test template used synchronous `TestClient` + `asyncio.get_event_loop().run_until_complete()` for seeding data, which doesn't match the project's async test infrastructure
- **Fix:** Rewrote tests as `async def` tests using `AsyncClient` + ASGI transport + `FakeDataRepository` via `dependency_overrides`, matching the webhook endpoint test pattern exactly
- **Files modified:** `tests/integration/test_query_endpoint.py`
- **Commit:** 4c54a60

---

## Verification

- `pytest tests/integration/test_query_endpoint.py tests/unit/test_query_handler.py` — 17 passed
- Route visible at `/query/{model}` in app routes list
- Import smoke test: `from src.adapters.driving.fastapi.routes.query import router, query_records`
- Problem Details format confirmed on 400 responses
- System fields (id, connection_id, model, created_at) present in all query results

## Self-Check: PASSED
