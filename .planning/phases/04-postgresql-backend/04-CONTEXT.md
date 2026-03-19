# Phase 4: PostgreSQL Backend - Context

**Gathered:** 2026-03-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Add PostgreSQL adapter alongside existing SQLite with automatic backend selection based on DATABASE_URL scheme. No code changes required to switch backends — just set the environment variable. Includes migration ENV override and CI hardening for both backends.

</domain>

<decisions>
## Implementation Decisions

### Backend Detection
- Scheme-based detection from DATABASE_URL — zero config beyond setting the URL
- Accept both `postgresql://` and `postgresql+asyncpg://` — internally always use asyncpg
- Accept both `sqlite://` and `sqlite+aiosqlite://` — internally always use aiosqlite
- Unrecognized scheme fails fast at startup with ValueError listing supported schemes — no silent fallback

### Migration Strategy
- `alembic/env.py` reads DATABASE_URL from environment first, falls back to alembic.ini default
- CI runs migrations against both SQLite and PostgreSQL — catches dialect differences early
- PostgreSQL in CI via Docker Compose service (postgres service in docker-compose.test.yml, GitHub Actions services: postgres)

### Repository Factory
- New module at `src/adapters/driven/repository_factory.py`
- Single function: `create_repository(database_url: str) -> DataRepository`
- Factory creates both engine + session_factory internally — encapsulates all connection setup
- Repository classes expose `engine` property for health check access (`repository.engine` for SELECT 1)
- `dependencies.py` calls factory instead of hardcoding SQLiteDataRepository

### Claude's Discretion
- asyncpg connection pool sizing (reasonable defaults vs explicit config)
- Exact error message format for unsupported schemes
- Whether to add PgBouncer detection (statement_cache_size=0 workaround)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing Code (Critical)
- `src/kernel/ports/repository.py` — DataRepository Protocol that PostgresDataRepository must implement
- `src/adapters/driven/sqlite/repository.py` — SQLiteDataRepository implementation pattern to follow
- `src/adapters/driving/fastapi/dependencies.py` — Hardcodes SQLiteDataRepository, must be updated to use factory
- `src/config/settings.py` — Settings class with database_url field already exists
- `src/adapters/driving/fastapi/routes/health.py` — Uses request.app.state.engine for health check

### Project Architecture
- `.planning/research/ARCHITECTURE.md` — Hexagonal architecture, driven adapter patterns
- `.planning/research/STACK.md` — asyncpg driver requirements, SQLAlchemy 2.0 async patterns

### Known Pitfalls (from STATE.md)
- dependencies.py hardcodes SQLiteDataRepository — factory must replace it
- alembic.ini hardcodes SQLite URL — env.py must read DATABASE_URL env var
- PostgreSQL adapter must use `sqlalchemy.dialects.postgresql.insert` (not sqlite dialect import)
- If PgBouncer used: `connect_args={"statement_cache_size": 0}` required

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `DataRepository` Protocol — PostgresDataRepository implements this, no changes needed to interface
- `SQLiteDataRepository` — Reference implementation for add/get with idempotent inserts and audit logging
- `DataRecord` and `AuditLog` models — SQLAlchemy ORM models, PostgreSQL-compatible
- `Settings` class — Already has `database_url` field, ready for scheme detection

### Established Patterns
- Async/await with SQLAlchemy 2.0 async ORM (async_sessionmaker, AsyncSession)
- Idempotent inserts via dialect-specific `insert().on_conflict_do_nothing()`
- Atomic audit log writes in same transaction as data
- Dependency injection via FastAPI request.app.state

### Integration Points
- `app.py` creates engine at startup — will call factory instead
- `dependencies.py.get_add_data_handler()` — must use factory to get repository
- Health check uses `request.app.state.engine` — factory provides engine via repository.engine property

</code_context>

<specifics>
## Specific Ideas

- PostgreSQL idempotent insert uses `sqlalchemy.dialects.postgresql.insert` — different import from SQLite
- Health check could report backend type: "backend": "postgresql" or "backend": "sqlite" (success criterion #5)
- Consider logging backend type at startup for debugging: "Starting with PostgreSQL backend" / "Starting with SQLite backend"

</specifics>

<deferred>
## Deferred Ideas

- Connection pool config via ENV vars (PGRS-08 in future requirements) — v2 feature
- PgBouncer auto-detection — nice-to-have, not critical for this phase

</deferred>

---

*Phase: 04-postgresql-backend*
*Context gathered: 2026-03-19*
