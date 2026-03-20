---
phase: 05-query-capability
plan: 01
subsystem: api
tags: [cqrs, kernel, query, dataclass, hexagonal]

# Dependency graph
requires:
  - phase: 04-postgresql-backend
    provides: DataRepository.query() port declared in repository.py
provides:
  - QueryData dataclass (CQRS read intent)
  - QueryHandler (limit-enforced read orchestrator)
  - kernel exports for QueryData, QueryHandler, DEFAULT_QUERY_LIMIT, MAX_QUERY_LIMIT
affects: [05-02, 05-03, any phase that builds query endpoints or needs kernel query API]

# Tech tracking
tech-stack:
  added: []
  patterns: [CQRS query/handler pattern, unconditional limit cap via min(), TDD RED/GREEN for handler]

key-files:
  created:
    - src/kernel/queries/query_data.py
    - src/kernel/queries/__init__.py
    - src/kernel/handlers/query_handler.py
    - tests/kernel/queries/__init__.py
    - tests/kernel/queries/test_query_data.py
    - tests/unit/test_query_handler.py
  modified:
    - src/kernel/handlers/__init__.py
    - src/kernel/__init__.py
    - tests/unit/fakes.py

key-decisions:
  - "QueryData has no offset field - pagination deferred, port signature doesn't include it"
  - "MAX_QUERY_LIMIT=1000 enforced via min() in handler - unconditional cap regardless of caller request"
  - "FakeDataRepository.query() returns system fields (id, connection_id, model, created_at) plus data fields"

patterns-established:
  - "Query pattern: @dataclass with model (required), filters (optional), limit (capped), correlation (default)"
  - "Handler pattern: single dependency (repository port only), effective_limit = min(query.limit, MAX_QUERY_LIMIT)"
  - "No events emitted from query handlers - queries are read-only"

requirements-completed: [QURY-01, QURY-02, QURY-03]

# Metrics
duration: 2min
completed: 2026-03-19
---

# Phase 5 Plan 01: Query Capability - Kernel Layer Summary

**Pure-kernel CQRS query layer with QueryData dataclass and QueryHandler enforcing unconditional 1000-record limit cap via repository port**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-19T18:22:10Z
- **Completed:** 2026-03-19T18:24:00Z
- **Tasks:** 4 completed
- **Files modified:** 9

## Accomplishments
- QueryData @dataclass with model (required), filters, limit, correlation fields - zero external imports
- DEFAULT_QUERY_LIMIT=100 and MAX_QUERY_LIMIT=1000 constants
- QueryHandler with unconditional limit cap via `min(query.limit, MAX_QUERY_LIMIT)`
- FakeDataRepository extended with query() method and query_calls tracking
- 13 new tests: 9 QueryData + 4 QueryHandler, all passing
- Full kernel exports: QueryData, QueryHandler, DEFAULT_QUERY_LIMIT, MAX_QUERY_LIMIT

## Task Commits

Each task was committed atomically:

1. **Task 1: Create QueryData query dataclass** - `5e57910` (feat)
2. **Task 2: Create QueryHandler with limit enforcement** - `3acd1bc` (test - RED), `633c23e` (feat - GREEN)
3. **Task 3: Export QueryData and QueryHandler from kernel** - `3c72fb2` (feat)
4. **Task 4: Add kernel unit tests for QueryData and QueryHandler** - `ab68cba` (test)

_Note: Task 2 was TDD - two commits (RED test then GREEN implementation)_

## Files Created/Modified
- `src/kernel/queries/query_data.py` - QueryData @dataclass with limit constants
- `src/kernel/queries/__init__.py` - Exports QueryData, DEFAULT_QUERY_LIMIT, MAX_QUERY_LIMIT
- `src/kernel/handlers/query_handler.py` - QueryHandler enforcing limit cap via repository port
- `src/kernel/handlers/__init__.py` - Updated to export QueryHandler alongside AddDataHandler
- `src/kernel/__init__.py` - Updated to export all query-related names
- `tests/kernel/queries/__init__.py` - Empty init for test package
- `tests/kernel/queries/test_query_data.py` - 9 tests for QueryData
- `tests/unit/test_query_handler.py` - 4 tests for QueryHandler
- `tests/unit/fakes.py` - FakeDataRepository extended with query() and query_calls

## Decisions Made
- QueryData has no offset field - pagination deferred to future phase, port signature does not include offset
- Limit cap is unconditional: `min(query.limit, MAX_QUERY_LIMIT)` always applies, even if caller sends 5000
- FakeDataRepository.query() returns dicts with system fields (id, connection_id, model, created_at) plus data

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Kernel query layer complete - QueryData + QueryHandler ready for adapter and API layers
- FakeDataRepository now implements full DataRepository protocol including query()
- Phase 05-02 can add SQLite adapter query implementation
- Phase 05-03 can add FastAPI query endpoint wiring

## Self-Check: PASSED

All 8 implementation files found on disk. All 5 commits (5e57910, 3acd1bc, 633c23e, 3c72fb2, ab68cba) present in git log. 13 tests passing.

---
*Phase: 05-query-capability*
*Completed: 2026-03-19*
