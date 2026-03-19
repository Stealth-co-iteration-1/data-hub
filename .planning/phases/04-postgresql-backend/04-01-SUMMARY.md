---
phase: 04-postgresql-backend
plan: 01
subsystem: database
tags: [asyncpg, postgresql, protocol, repository, testing]

# Dependency graph
requires:
  - phase: 03-persistence-layer
    provides: DataRepository Protocol base definition
provides:
  - asyncpg driver dependency installed
  - DataRepository Protocol query() method signature
  - FakeDataRepository for unit testing
affects: [04-postgresql-backend, 05-query-capability]

# Tech tracking
tech-stack:
  added: [asyncpg>=0.31.0]
  patterns: [in-memory fake repository for testing]

key-files:
  created:
    - src/kernel/ports/fake_repository.py
    - tests/unit/test_fake_repository.py
  modified:
    - pyproject.toml
    - uv.lock
    - src/kernel/ports/repository.py

key-decisions:
  - "asyncpg>=0.31.0 chosen for Python 3.12 binary wheel compatibility"
  - "query() returns list[dict] with 100-record default limit for safety"
  - "FakeDataRepository uses in-memory dict with event_id tracking for idempotency"

patterns-established:
  - "Protocol extension: add methods to Protocol, create FakeRepository for testing, then implement in adapters"
  - "In-memory fake repositories for kernel unit testing without database dependencies"

requirements-completed: [PGRS-02]

# Metrics
duration: 2min
completed: 2026-03-19
---

# Phase 04 Plan 01: asyncpg & Protocol Extension Summary

**asyncpg dependency added and DataRepository Protocol extended with query() method for PostgreSQL support readiness**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-19T16:01:32Z
- **Completed:** 2026-03-19T16:03:21Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments
- Added asyncpg>=0.31.0 driver dependency to pyproject.toml
- Extended DataRepository Protocol with query(model, filters, limit) method
- Created FakeDataRepository implementing full Protocol for unit testing
- Added 7 new tests verifying Protocol compliance

## Task Commits

Each task was committed atomically:

1. **Task 1: Add asyncpg dependency** - `49a4b26` (chore)
2. **Task 2: Extend Protocol with query()** - `a25e4ca` (feat)
3. **Task 3: Create FakeDataRepository** - `5fc0a0d` (feat)

## Files Created/Modified
- `pyproject.toml` - Added asyncpg>=0.31.0 dependency
- `uv.lock` - Regenerated with asyncpg
- `src/kernel/ports/repository.py` - Added query() method to DataRepository Protocol
- `src/kernel/ports/fake_repository.py` - New in-memory repository for testing
- `tests/unit/test_fake_repository.py` - Protocol compliance tests

## Decisions Made
- asyncpg>=0.31.0 selected for confirmed Python 3.12 binary wheel support
- query() method uses dict[str, Any] | None filters for simple key=value matching
- Default limit of 100 records prevents unbounded queries
- FakeDataRepository tracks event_id separately for idempotency testing

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- pytest not initially available via uv run - resolved by installing via uv pip install pytest pytest-asyncio

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- asyncpg driver ready for PostgreSQL adapter implementation
- Protocol interface ready for both SQLite query() and PostgreSQL query() implementations
- FakeDataRepository available for kernel unit tests
- All 87 tests pass, no regressions

## Self-Check: PASSED

All files exist, all commits verified:
- src/kernel/ports/fake_repository.py: FOUND
- tests/unit/test_fake_repository.py: FOUND
- Commit 49a4b26: FOUND
- Commit a25e4ca: FOUND
- Commit 5fc0a0d: FOUND

---
*Phase: 04-postgresql-backend*
*Completed: 2026-03-19*
