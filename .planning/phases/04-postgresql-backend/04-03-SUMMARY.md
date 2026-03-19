---
phase: 04-postgresql-backend
plan: 03
subsystem: backend-wiring
tags: [factory, configuration, dependency-injection, migrations]

dependency_graph:
  requires:
    - 04-02-SUMMARY.md # PostgresDataRepository implementation
  provides:
    - backend-factory # URL scheme detection and repository creation
    - env-based-switching # DATABASE_URL-driven backend selection
  affects:
    - app-lifespan # Uses factory instead of direct engine creation
    - dependencies # Uses repository from app.state
    - health-endpoint # Reports backend type
    - migrations # Read DATABASE_URL from environment

tech_stack:
  patterns:
    - Factory pattern for repository creation
    - URL normalization for async drivers
    - ENV-based configuration override

key_files:
  created:
    - src/adapters/driven/repository_factory.py
    - tests/unit/test_repository_factory.py
    - tests/integration/test_backend_switching.py
  modified:
    - src/adapters/driving/fastapi/app.py
    - src/adapters/driving/fastapi/dependencies.py
    - src/adapters/driving/fastapi/routes/health.py
    - migrations/env.py
    - tests/integration/test_health.py

decisions:
  - "RepositoryBundle container for repository, engine, backend metadata"
  - "URL normalization: sqlite->sqlite+aiosqlite, postgresql->postgresql+asyncpg"
  - "Support postgres:// alias (Heroku-style URLs)"
  - "Fail fast on unsupported schemes with ValueError"

metrics:
  duration: 4 min
  tasks: 6
  files_created: 3
  files_modified: 5
  loc_added: ~350
  tests_added: 16
  completed: "2026-03-19"
---

# Phase 04 Plan 03: Factory Wiring & ENV-Based Backend Selection Summary

Repository factory with URL scheme detection enabling zero-config backend switching via DATABASE_URL.

## Completed Tasks

| Task | Name | Commit | Key Changes |
|------|------|--------|-------------|
| 1 | Create repository factory | 0e18588 | RepositoryBundle, SUPPORTED_SCHEMES, create_repository() |
| 2 | Update app.py lifespan | 5828f1a | Use factory, store repository/backend in app.state |
| 3 | Update dependencies.py | 9a1bd72 | Use request.app.state.repository |
| 4 | Update health endpoint | c07f2e8 | Add backend field to response |
| 5 | Update migrations/env.py | 7ae4578 | Add get_database_url() with ENV priority |
| 6 | Create backend switching tests | 5f8f058 | Factory and health endpoint integration tests |
| - | Fix test fixtures | 47f05de | Add backend to test fixtures |

## Implementation Details

### Repository Factory (repository_factory.py)

```python
SUPPORTED_SCHEMES = {
    "sqlite": "sqlite",
    "sqlite+aiosqlite": "sqlite",
    "postgresql": "postgresql",
    "postgresql+asyncpg": "postgresql",
    "postgres": "postgresql",  # Heroku-style alias
}

def create_repository(database_url: str, echo: bool = False) -> RepositoryBundle:
    # 1. Normalize URL (add async driver suffix)
    # 2. Create engine and session factory
    # 3. Return appropriate repository based on scheme
```

### App Lifespan Changes

Before:
```python
engine = create_async_engine(settings.database_url, ...)
app.state.engine = engine
app.state.session_factory = async_sessionmaker(engine, ...)
```

After:
```python
bundle = create_repository(settings.database_url, ...)
app.state.repository = bundle.repository
app.state.engine = bundle.engine
app.state.backend = bundle.backend
```

### Health Response

```json
{
  "status": "ok",
  "version": "1.0.0",
  "backend": "sqlite"
}
```

### Migration ENV Override

```python
def get_database_url() -> str:
    env_url = os.environ.get("DATABASE_URL")
    if env_url:
        # Normalize and return
        return normalized_url
    return config.get_main_option("sqlalchemy.url")
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test fixtures missing backend field**
- **Found during:** Task 6 verification
- **Issue:** Existing health tests set app.state.engine directly without app.state.backend
- **Fix:** Added backend field to test fixtures, excluded backend from secrets check
- **Files modified:** tests/integration/test_health.py, tests/integration/test_backend_switching.py
- **Commit:** 47f05de

## Requirements Fulfilled

- **CONF-01**: Backend-agnostic configuration (factory creates correct adapter based on URL scheme)
- **CONF-02**: ENV-based switching (DATABASE_URL determines backend without code changes)

## Verification Results

All 102 tests passing:
- 11 unit tests for repository factory
- 5 integration tests for backend switching
- All existing tests continue to pass

Factory scheme detection verified:
```
Backend: sqlite
Repository type: SQLiteDataRepository
```

## Self-Check: PASSED

- [x] src/adapters/driven/repository_factory.py exists (124 lines)
- [x] tests/unit/test_repository_factory.py exists
- [x] tests/integration/test_backend_switching.py exists
- [x] Commits verified: 0e18588, 5828f1a, 9a1bd72, c07f2e8, 7ae4578, 5f8f058, 47f05de
