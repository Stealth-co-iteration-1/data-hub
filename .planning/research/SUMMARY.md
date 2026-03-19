# Project Research Summary

**Project:** data-hub v2.0
**Domain:** Hexagonal Python service — PostgreSQL adapter, configurable storage backends, SQL query capability
**Researched:** 2026-03-19
**Confidence:** HIGH

## Executive Summary

Data-hub v2.0 is a production hardening milestone on top of a fully validated v1.0 hexagonal service. The existing stack (FastAPI, SQLAlchemy 2.0 async, aiosqlite, Alembic, Pydantic, structlog) is locked and working. The v2.0 work adds exactly three capabilities: a PostgreSQL async adapter (asyncpg), ENV-based storage backend selection, and a `QueryData` kernel command with a parameterized SQL read port and corresponding HTTP endpoint. The single new dependency is `asyncpg>=0.31.0`. Nothing in this milestone changes the kernel architecture — it only extends the protocol, adds a parallel adapter, adds a factory at the composition root, and wires a new route.

The recommended approach is strictly additive: extend `DataRepository` Protocol with a `query()` method, create `PostgresDataRepository` in `adapters/driven/postgres/` mirroring the SQLite structure, add a factory function in `adapters/driven/factory.py` that selects the correct repository from the `DATABASE_URL` scheme, and expose `GET /query` via a new route module. Backend switching requires no new ENV variable — `DATABASE_URL` already drives `create_async_engine()` in `app.py`. The configurable backend is purely a composition-root concern: `dependencies.py` must replace its hardcoded `SQLiteDataRepository` instantiation with a call to the factory.

The primary risks are operational rather than architectural. Three issues can cause silent production failures: Alembic's hardcoded `alembic.ini` URL must be overridden by `DATABASE_URL` in `migrations/env.py` or migrations will silently target SQLite in production; the hardcoded `SQLiteDataRepository` in `dependencies.py` must be replaced by the factory or the PostgreSQL adapter is never invoked regardless of `DATABASE_URL`; and the query endpoint must enforce an unconditional `LIMIT` or a single request can exhaust worker memory. SQL injection via identifier interpolation in `text()` queries is also a hard requirement to address, not a deferred security concern.

---

## Key Findings

### Recommended Stack

The existing stack requires only one addition: `asyncpg>=0.31.0`. SQLAlchemy 2.0.48 already ships the `postgresql+asyncpg` dialect built-in — no SQLAlchemy upgrade needed. `create_async_engine`, `async_sessionmaker`, and `AsyncSession` behave identically for PostgreSQL as they do for SQLite; only the URL scheme changes. The `pydantic-settings` config already has `database_url`, and `migrations/env.py` already uses `async_engine_from_config` — the correct async Alembic pattern. All supporting infrastructure is in place.

**Core technologies:**
- `asyncpg>=0.31.0`: PostgreSQL async driver — SQLAlchemy's primary asyncio dialect for PostgreSQL; ships binary wheels for Python 3.12/3.13; faster than psycopg3 in async-only workloads; 0.31.0 is the latest stable release (November 2025)
- `sqlalchemy[asyncio]` 2.0.48 (existing): already supports `postgresql+asyncpg` dialect natively; `create_async_engine` and `text()` with named params work identically for both dialects
- `alembic` 1.18.4 (existing): `env.py` async pattern already correct; only needs `DATABASE_URL` ENV override in `migrations/env.py`
- `pydantic-settings` (existing): `database_url` field already present; backend selection requires no new settings field

**What NOT to use:**
- `exec_driver_sql()` for parameterized queries — bypasses SQLAlchemy dialect layer; asyncpg rejects `:name` syntax at driver level, raising `PostgresSyntaxError`; use `session.execute(text("... :param ..."), {"param": value})` instead
- `psycopg2` — synchronous; incompatible with SQLAlchemy asyncio extension
- String formatting inside `text()` queries — SQL injection vulnerability; always use named bind parameters

### Expected Features

All v2.0 features are P1 — the milestone is not complete without them. Pagination, automated migration on startup, and pool tuning are explicitly P2. Nothing in this milestone is architecturally novel; all features are extensions of existing patterns.

**Must have (table stakes for v2.0):**
- `DataRepository.query()` port extension — Protocol must declare the method before any adapter or handler can use it; unblocks all other work
- PostgreSQL adapter (`PostgresDataRepository`) — production deployments require a server-grade DB; must use `sqlalchemy.dialects.postgresql.insert` for idempotent inserts
- Idempotent inserts on PostgreSQL (`ON CONFLICT DO NOTHING`) — duplicate webhooks are a production reality; SQLite adapter already has this; PostgreSQL adapter must match
- ENV-based backend factory — twelve-factor standard; factory reads `DATABASE_URL` scheme and returns the correct repository class
- `QueryData` command + handler (pure kernel, zero SQLAlchemy imports) — SQL and params travel as plain Python types through the kernel boundary
- Both adapters implement `query()` — SQLite adapter must also implement it for local development and unit test parity
- `GET /query` HTTP endpoint with Pydantic-validated request — stored data that cannot be read back is useless; must enforce result cap unconditionally

**Should have (after P1 stable):**
- Connection pool parameters as ENV vars (`pool_size`, `max_overflow`, `pool_recycle`, `pool_pre_ping`) — safe defaults exist; tune per deployment
- Automated Alembic migration on startup — known v1.0 tech debt; can now target PostgreSQL in CI
- Query result pagination (`limit`/`offset`) — add when result sets grow large in production

**Defer (v3+):**
- Event consumers — explicitly out of scope per PROJECT.md
- Schema drift detection — deferred to v3.0
- Real-time streaming — batch/webhook model is sufficient

### Architecture Approach

The hexagonal boundary is already established and must not be violated. All v2.0 changes are extensions or additions at the adapter and composition-root layers. The kernel stays clean: `src/kernel/` must have zero imports from `sqlalchemy`, `asyncpg`, or any external dependency. `QueryDataCommand` carries `sql: str` and `params: dict` as plain Python — the kernel never knows which database is running. The factory at `adapters/driven/factory.py` is the sole location that imports both concrete adapters; it is called per request (cheap — no I/O, just class instantiation with the already-created `session_factory` from `app.state`).

**Major components:**
1. `kernel/ports/repository.py` (EXTEND) — add `query(sql, params) -> list[dict]` to the `DataRepository` Protocol; this is the critical-path blocker for all other work
2. `kernel/commands/query_data.py` + `kernel/handlers/query_data_handler.py` (NEW) — pure Python command/handler; handler calls `repository.query()`; no ORM types cross the kernel boundary
3. `adapters/driven/postgres/repository.py` (NEW) — `PostgresDataRepository` implementing full protocol; uses `sqlalchemy.dialects.postgresql.insert` for upserts; uses `session.execute(text(sql), params)` for queries
4. `adapters/driven/factory.py` (NEW) — `create_repository(database_url, session_factory)` selects adapter by URL scheme; lazy imports inside function body prevent circular deps
5. `adapters/driving/fastapi/dependencies.py` (MODIFY) — replace hardcoded `SQLiteDataRepository` with factory call; add `get_query_handler` dependency
6. `adapters/driving/fastapi/routes/query.py` (NEW) — `GET /query` endpoint; Pydantic-validated request; structured filter params only (never raw SQL from HTTP callers); unconditional LIMIT enforcement
7. `tests/unit/fakes.py` (MODIFY) — add `query()` to `FakeDataRepository` so `QueryDataHandler` can be unit-tested without a real database

**No changes needed:** `app.py`, `config/settings.py`, `migrations/env.py` (except ENV override for DATABASE_URL), ORM models in `sqlite/models.py` (dialect-agnostic)

### Critical Pitfalls

1. **Alembic `alembic.ini` hardcodes SQLite URL** — update `migrations/env.py` to read `os.environ.get("DATABASE_URL")` before Alembic uses the config URL; without this, `alembic upgrade head` silently migrates the local SQLite file in any PostgreSQL environment, exits 0, and the first production request fails with a missing-table error

2. **`dependencies.py` hardcodes `SQLiteDataRepository`** — after adding the factory, replace the direct instantiation; without this the PostgreSQL adapter exists but is never invoked regardless of `DATABASE_URL`; the service starts, responds to requests, and appears healthy while always using SQLite

3. **SQL injection via identifier interpolation in `text()` queries** — values are safe with named bind parameters; SQL identifiers (column names, table names, ORDER BY fields) cannot be parameterized and must be validated against an explicit allowlist; injection test cases are acceptance criteria, not a deferred item; never accept raw SQL strings from HTTP callers

4. **Dialect-specific `ON CONFLICT` — wrong import in PostgreSQL adapter** — the PostgreSQL adapter must use `from sqlalchemy.dialects.postgresql import insert as pg_insert`; copying the SQLite adapter's `sqlite_insert` raises `CompileError` at execution time (not import time); verify with an idempotency integration test against a real PostgreSQL connection (not SQLite or in-memory)

5. **Unbound query result size — DoS via expensive query** — enforce an unconditional `LIMIT` in the query adapter regardless of client input; make the default and maximum ENV-configurable (`DEFAULT_QUERY_LIMIT=100`, `MAX_QUERY_LIMIT=1000`); a single unbounded query on a populated `data_records` table can exhaust worker memory or starve the connection pool

---

## Implications for Roadmap

The dependency chain drives a clear build order. The Protocol extension is the critical-path blocker — nothing else can be implemented until `query()` is declared on `DataRepository`. After that, the PostgreSQL adapter and the kernel command can proceed in parallel before converging at the factory, dependency wiring, and route layers. Migration CI hardening is a deployment prerequisite that can proceed in parallel with query work once the adapter exists.

### Phase 1: Protocol Extension and Foundation

**Rationale:** The `DataRepository` Protocol is the seam everything depends on. Extending it with `query()` and adding `asyncpg` to `pyproject.toml` are the only prerequisites for all downstream work. Also includes updating `FakeDataRepository` to keep unit tests compilable immediately.

**Delivers:** Extended `DataRepository` Protocol with `query()` method; updated `FakeDataRepository` in `tests/unit/fakes.py`; `asyncpg>=0.31.0` added to `pyproject.toml` and installed

**Addresses:** `DataRepository.query()` read port (P1 table stakes)

**Avoids:** Blocked parallel development in subsequent phases; kernel purity violations from carrying SQL types before the port boundary is defined

### Phase 2: PostgreSQL Adapter and Backend Factory

**Rationale:** The PostgreSQL adapter and backend factory are the core value of v2.0. Once the Protocol is extended, this phase can proceed in parallel with kernel command work. The factory is the last step because it depends on both adapters being complete.

**Delivers:** `PostgresDataRepository` implementing full protocol (add, get, query) with idempotent inserts; `SQLiteDataRepository` extended with `query()`; `adapters/driven/factory.py` factory function; `dependencies.py` updated to use factory; connection pool parameters (`pool_pre_ping`, `pool_recycle`, `pool_size`, `max_overflow`) as ENV-configurable settings; `/health` endpoint reports active backend (`storage_backend` field)

**Uses:** `asyncpg>=0.31.0`, `sqlalchemy.dialects.postgresql.insert`, `session.execute(text(...), params)` pattern

**Implements:** `PostgresDataRepository`, `BackendFactory` components

**Avoids:** Hardcoded repository bypass (Pitfall 5 from PITFALLS.md); dialect-specific ON CONFLICT error (Pitfall 1); connection pool misconfiguration (Pitfall 4); singleton repository created at module import time (Architecture Anti-Pattern 3)

### Phase 3: QueryData Kernel Command and Query Endpoint

**Rationale:** The query feature depends on both adapters implementing `query()` (Phase 2) and the Protocol declaring it (Phase 1). Kernel command and HTTP route are built together so injection prevention and result cap enforcement are never separated from the feature.

**Delivers:** `QueryDataCommand` + `QueryDataHandler` (pure kernel, zero external imports); `GET /query` FastAPI route with Pydantic-validated structured parameters; unconditional LIMIT enforcement (`DEFAULT_QUERY_LIMIT`, `MAX_QUERY_LIMIT` ENV-configurable); allowlist validation for filter identifiers; structured error responses (400 for invalid input, not 500)

**Uses:** `text()` with named bind parameters; `result.mappings()` for plain dict results; `[dict(row) for row in result]` pattern

**Implements:** `QueryDataHandler`, `routes/query.py` components

**Avoids:** SQL injection via identifier interpolation (Pitfall 3); unbound query result size DoS (Pitfall 7); ORM leakage into kernel (Architecture Anti-Pattern 2); free-form SQL strings accepted from HTTP callers (Anti-Feature in FEATURES.md)

### Phase 4: Migration Compatibility and CI Hardening

**Rationale:** Alembic migration correctness against PostgreSQL is a deployment prerequisite. The `alembic.ini` hardcoded URL is a silent production failure mode — the command exits 0 while migrating the wrong database. This phase closes that gap and validates the entire migration history against both dialects.

**Delivers:** `migrations/env.py` updated to read `DATABASE_URL` from environment first; CI job running `alembic upgrade head` + `alembic downgrade base` against `postgres:16-alpine` Docker service; confirmation all three existing migrations are PostgreSQL-compatible; `alembic.ini` confirmed to contain no production credentials

**Avoids:** Alembic URL bypass (Pitfall 2); `batch_alter_table` migration incompatibility with future migrations (Pitfall 6); credentials committed to repository (Security section in PITFALLS.md)

### Phase Ordering Rationale

- Phase 1 must be serial and first because the Protocol is the dependency contract for all other phases; no adapter can implement `query()` until it is declared and no handler can call it
- Phases 2 and 3 can partially overlap — `PostgresDataRepository` and `QueryDataCommand` can be developed in parallel after Phase 1; the factory (end of Phase 2) must complete before the route (Phase 3) can be fully wired end-to-end
- Phase 4 runs in parallel with Phase 3 if team capacity allows, or sequentially after — it validates the complete adapter against a real PostgreSQL container and is a gate before any production deployment
- The ARCHITECTURE.md build order (Steps 1–9) maps directly to this phase structure and confirms the dependency chain

### Research Flags

All phases have well-documented patterns — no phase requires `/gsd:research-phase` during planning:

- **Phase 1 (Protocol Extension):** Standard Python Protocol extension; zero ambiguity; pattern established in v1.0 codebase
- **Phase 2 (PostgreSQL Adapter + Factory):** SQLAlchemy 2.0 async PostgreSQL dialect is extensively documented; all patterns verified against official docs and direct codebase inspection; dialect-specific insert pattern is explicit in STACK.md
- **Phase 3 (QueryData Command + Endpoint):** Hexagonal command/handler pattern already demonstrated by `AddData`; `text()` parameterization pattern verified against SQLAlchemy issue #6452; PITFALLS.md has injection-specific guidance
- **Phase 4 (Migration CI):** Alembic async pattern and ENV override are well-documented; Docker Compose CI for PostgreSQL is standard; existing `env.py` already uses the correct async pattern

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | asyncpg 0.31.0 confirmed on PyPI with Python 3.12/3.13 wheels; SQLAlchemy 2.0.48 verified in lock file; all other dependencies already installed and validated in v1.0; `exec_driver_sql` vs `execute(text())` difference verified against SQLAlchemy issue #6452 |
| Features | HIGH | Feature set derived directly from PROJECT.md milestone scope; dependency graph verified against existing codebase file structure; all P1 features are extensions of established patterns, not new patterns |
| Architecture | HIGH | Existing codebase inspected directly (`repository.py`, `dependencies.py`, `app.py`, `settings.py`, `migrations/env.py`); all component boundaries verified against running v1.0 code; build order confirmed by tracing actual import dependencies |
| Pitfalls | HIGH | All critical items verified against official SQLAlchemy docs, asyncpg docs, and Alembic docs with multiple authoritative sources per pitfall; warning signs and recovery strategies are concrete and actionable |

**Overall confidence:** HIGH

### Gaps to Address

- **Connection pool tuning values:** The research recommends `pool_size=5`, `max_overflow=10` as a starting point with ENV-configurability. Actual optimal values depend on Uvicorn worker count and PostgreSQL `max_connections` in the deployment environment. Validate after first load test with real infrastructure; target 20 concurrent requests without `QueuePool limit reached` errors.

- **PgBouncer in deployment stack:** If the production PostgreSQL deployment uses PgBouncer in transaction mode, `connect_args={"statement_cache_size": 0}` must be added to `create_async_engine()`. This is not known at research time. Add a `DB_STATEMENT_CACHE_SIZE` ENV var defaulting to the asyncpg default so it can be set to 0 without a code change if PgBouncer is confirmed in the deployment stack.

- **`JSONB` vs `JSON` column type:** The existing `sa.JSON` column maps to PostgreSQL `JSON` (not `JSONB`). JSONB enables indexing and faster operators on the `data` column. Explicitly deferred to a future milestone; not a blocker for v2.0 but flag for the team if query performance on `data` column becomes a concern.

---

## Sources

### Primary (HIGH confidence)
- SQLAlchemy 2.0 Async I/O documentation — `create_async_engine`, `async_sessionmaker`, `postgresql+asyncpg` URL format, `session.execute(text(), params)` pattern
- SQLAlchemy 2.0 PostgreSQL dialect documentation — `from sqlalchemy.dialects.postgresql import insert`, `on_conflict_do_nothing()`
- asyncpg PyPI + GitHub releases — version 0.31.0 confirmed (November 24, 2025), Python 3.12/3.13 binary wheels verified
- SQLAlchemy issue #6452 — `exec_driver_sql` vs `execute(text())` for asyncpg named parameters; `execute(text(...), dict)` is the correct and safe pattern
- SQLAlchemy discussion #7192 — asyncpg parameter rewriting handled by dialect layer when using `session.execute`; named params work correctly
- Alembic async migration documentation — `async_engine_from_config`, `connection.run_sync(do_run_migrations)` pattern
- Alembic batch migrations documentation — `op.batch_alter_table()` for cross-dialect compatibility
- Alembic ENV override discussion #1043 — `os.environ.get("DATABASE_URL")` pattern in `env.py`
- asyncpg FAQ — PgBouncer transaction mode and prepared statement cache incompatibility; `statement_cache_size=0` fix
- Direct codebase inspection — `pyproject.toml`, `uv.lock`, `settings.py`, `repository.py`, `session.py`, `migrations/env.py`, `dependencies.py`, `app.py` (all files confirmed; asyncpg not yet in lock file)

### Secondary (MEDIUM confidence)
- Building High-Performance Async APIs with FastAPI, SQLAlchemy 2.0, and asyncpg (leapcell.io) — async performance patterns
- Python + PostgreSQL: SQLAlchemy vs asyncpg Performance Comparison (dasroot.net, 2026) — asyncpg performance advantage confirmed in async-only workloads
- SQL Injection Defenses: Python SQLAlchemy Parameterized Query Best Practices 2026 (johal.in) — identifier allowlist pattern
- How to properly set pool_size and max_overflow in SQLAlchemy for ASGI apps (pythontutorials.net) — pool configuration guidance
- Supabase pooling and asyncpg: PgBouncer incompatibility (medium.com) — `statement_cache_size=0` fix

---
*Research completed: 2026-03-19*
*Ready for roadmap: yes*
