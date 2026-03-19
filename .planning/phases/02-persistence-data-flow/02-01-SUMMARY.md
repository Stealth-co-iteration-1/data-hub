---
phase: 02-persistence-data-flow
plan: 01
subsystem: database
tags: [sqlalchemy, aiosqlite, sqlite, orm, hexagonal-architecture, idempotency]

# Dependency graph
requires:
  - phase: 01-foundation-kernel
    provides: DataRepository Protocol in src/kernel/ports/repository.py

provides:
  - SQLiteDataRepository implementing DataRepository Protocol via SQLAlchemy 2.0 async ORM
  - Async session factory with expire_on_commit=False for safe async access
  - DataRecord ORM model with unique event_id constraint for idempotency
  - Integration test suite (5 tests) covering PERS-01, PERS-04, VERF-01
  - Kernel isolation test ensuring no adapter imports in src/kernel/

affects: [03-webhook-transport-observability, composition-root]

# Tech tracking
tech-stack:
  added:
    - sqlalchemy[asyncio]>=2.0.48 (async ORM + greenlet)
    - aiosqlite>=0.20 (SQLite async driver, thread-per-connection model)
  patterns:
    - SQLAlchemy 2.0 Mapped/mapped_column style ORM models
    - sqlite_insert().on_conflict_do_nothing() for atomic idempotent inserts
    - async_sessionmaker with expire_on_commit=False (prevents MissingGreenlet)
    - Adapter returns plain dict, never ORM objects (kernel boundary enforcement)
    - In-memory SQLite per test for isolation in integration tests

key-files:
  created:
    - src/adapters/driven/sqlite/models.py (DataRecord ORM model with event_id unique constraint)
    - src/adapters/driven/sqlite/session.py (create_engine + create_session_factory)
    - src/adapters/driven/sqlite/repository.py (SQLiteDataRepository implementing DataRepository)
    - src/adapters/__init__.py
    - src/adapters/driven/__init__.py
    - src/adapters/driven/sqlite/__init__.py (lazy exports of SQLiteDataRepository, create_session_factory)
    - tests/integration/__init__.py
    - tests/integration/conftest.py (in-memory SQLite fixtures per test)
    - tests/integration/test_sqlite_repository.py (5 integration tests)
  modified:
    - pyproject.toml (added sqlalchemy[asyncio]>=2.0.48 and aiosqlite>=0.20)
    - tests/test_kernel_ports.py (added test_kernel_has_no_adapter_imports)

key-decisions:
  - "event_id extracted from data.get('event_id') in adapter, not as separate port parameter - keeps DataRepository port stable"
  - "ON CONFLICT DO NOTHING via sqlite_insert() for idempotency - session.add() raises IntegrityError, cannot use for conflict handling"
  - "expire_on_commit=False in async_sessionmaker - prevents MissingGreenlet errors after session close"
  - "Plain dict returned from get(), never ORM DataRecord - enforces kernel/adapter boundary"
  - "Lazy imports in sqlite/__init__.py to avoid circular import during task 2 before repository existed"

patterns-established:
  - "Pattern: Adapter returns plain dict from ORM - never leak ORM types to kernel"
  - "Pattern: sqlite_insert().on_conflict_do_nothing(index_elements=['event_id']) for idempotent inserts"
  - "Pattern: In-memory SQLite (sqlite+aiosqlite:///:memory:) for integration test isolation"
  - "Pattern: async with session.begin() for auto-commit/rollback transaction management"

requirements-completed: [PERS-01, PERS-02, PERS-04]

# Metrics
duration: 8min
completed: 2026-03-18
---

# Phase 2 Plan 01: SQLite Repository Adapter Summary

**SQLAlchemy 2.0 async SQLiteDataRepository with ON CONFLICT DO NOTHING idempotency, 46 tests passing, kernel isolated from adapters**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-03-18T22:34:27Z
- **Completed:** 2026-03-18T22:42:00Z
- **Tasks:** 6
- **Files modified:** 10

## Accomplishments
- SQLiteDataRepository implements DataRepository Protocol with full async support (PERS-01, PERS-02)
- Idempotent inserts via sqlite_insert().on_conflict_do_nothing() on event_id unique constraint (PERS-04)
- Integration test suite: 5 tests covering roundtrip persistence, None returns, table isolation, idempotency, and event_id-free inserts
- Kernel isolation enforced by AST-scanning import boundary test - no adapter imports in src/kernel/ (PERS-02)
- Full test suite: 46 passed (40 existing + 5 integration + 1 new kernel isolation)

## Task Commits

Each task was committed atomically:

1. **Task 1: Install SQLAlchemy async dependencies** - `e06aeb6` (chore)
2. **Task 2: Create SQLAlchemy ORM models** - `202f529` (feat)
3. **Task 3: Create async session factory** - `6137b93` (feat)
4. **Task 4: Create integration test fixtures and stubs (RED)** - `5643c85` (test)
5. **Task 5: Implement SQLiteDataRepository (GREEN)** - `5372ca8` (feat)
6. **Task 6: Verify kernel isolation** - `f9e380a` (test)

## Files Created/Modified
- `pyproject.toml` - Added sqlalchemy[asyncio]>=2.0.48 and aiosqlite>=0.20 to runtime dependencies
- `src/adapters/__init__.py` - Empty package init
- `src/adapters/driven/__init__.py` - Empty package init
- `src/adapters/driven/sqlite/__init__.py` - Lazy exports for SQLiteDataRepository and create_session_factory
- `src/adapters/driven/sqlite/models.py` - DataRecord ORM model with event_id unique constraint, JSON data column
- `src/adapters/driven/sqlite/session.py` - create_engine + create_session_factory with expire_on_commit=False
- `src/adapters/driven/sqlite/repository.py` - SQLiteDataRepository with add() and get() implementing DataRepository
- `tests/integration/__init__.py` - Empty package init
- `tests/integration/conftest.py` - Async engine + session_factory + repository fixtures using in-memory SQLite
- `tests/integration/test_sqlite_repository.py` - 5 integration tests for repository contract
- `tests/test_kernel_ports.py` - Extended with test_kernel_has_no_adapter_imports (AST scan)

## Decisions Made
- event_id extracted from data.get("event_id") inside the adapter, not surfaced as a port parameter. Keeps DataRepository Protocol stable; adapter owns idempotency key extraction.
- sqlite_insert().on_conflict_do_nothing() chosen over session.add() for idempotent path. session.add() raises IntegrityError on duplicate unique constraint - cannot be used for silent skip semantics.
- expire_on_commit=False in async_sessionmaker. Default True causes MissingGreenlet when accessing ORM attributes after session close in async context.
- Lazy imports via __getattr__ in sqlite/__init__.py to avoid circular import during Task 2 when repository module didn't exist yet.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Circular import prevented ORM model test during Task 2**
- **Found during:** Task 2 (Create SQLAlchemy ORM models)
- **Issue:** sqlite/__init__.py eagerly imported SQLiteDataRepository which didn't exist yet, causing ModuleNotFoundError when testing models in isolation
- **Fix:** Changed sqlite/__init__.py to use Python __getattr__ lazy imports so repository is only imported on first access
- **Files modified:** src/adapters/driven/sqlite/__init__.py
- **Verification:** `from src.adapters.driven.sqlite.models import Base, DataRecord` succeeded after fix
- **Committed in:** 202f529 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking - circular import during package init)
**Impact on plan:** Necessary for task ordering. No scope creep. Final __init__.py exports are correct.

## Issues Encountered
- uv sync removed dev dependencies (pytest, pytest-asyncio, etc.) when adding runtime deps. Required `uv sync --dev` to restore. No code changes needed.

## User Setup Required
None - no external service configuration required. All tests use in-memory SQLite.

## Next Phase Readiness
- SQLiteDataRepository ready for wiring into composition root
- Session factory accepts any SQLite URL - easy to switch to file-backed DB for production
- DataRecord table schema in-memory only for tests; needs Alembic migration for file-backed DB (planned in future plan)
- All 46 tests pass, full integration verified

---
*Phase: 02-persistence-data-flow*
*Completed: 2026-03-18*
