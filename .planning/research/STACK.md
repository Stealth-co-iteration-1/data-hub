# Stack Research

**Domain:** PostgreSQL adapter, configurable storage backends, SQL query capability (data-hub v2.0)
**Researched:** 2026-03-19
**Confidence:** HIGH

## Context

This is a SUBSEQUENT MILESTONE research file. The existing v1.0 stack (FastAPI, SQLAlchemy 2.0 async, aiosqlite, Alembic, Pydantic, structlog, prometheus_client, pydantic-settings) is already validated and locked. This document covers ONLY what must be added or changed for:

1. PostgreSQL async adapter (asyncpg driver)
2. ENV-based configurable backend (sqlite/postgres)
3. QueryData kernel command with parameterized SQL read port

Nothing below modifies the existing stack. All additions are additive.

---

## New Stack Additions

### Core Driver

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| asyncpg | `>=0.31.0` | Native async PostgreSQL driver | SQLAlchemy's asyncio extension requires an async-capable DBAPI. asyncpg is the de facto standard: it is SQLAlchemy's first and primary async dialect for PostgreSQL, ships binary wheels for Python 3.12 and 3.13, and has no synchronous fallback overhead. psycopg3 is the only credible alternative; asyncpg has broader adoption in the FastAPI ecosystem and the project already names this driver in PROJECT.md. |

**pyproject.toml change:**
```toml
dependencies = [
    # ... existing deps ...
    "asyncpg>=0.31.0",  # NEW: PostgreSQL async driver
]
```

**Install:**
```bash
uv add asyncpg
```

No other new packages are required. `sqlalchemy[asyncio]` is already present and activates all PostgreSQL async dialect machinery built into SQLAlchemy 2.0.

### No Other Package Changes

SQLAlchemy 2.0.48 (already pinned) ships the `postgresql+asyncpg` dialect built-in at `sqlalchemy.dialects.postgresql`. The `create_async_engine`, `async_sessionmaker`, and `AsyncSession` already in use for SQLite work identically for PostgreSQL — only the connection URL changes.

---

## Supporting Libraries (Unchanged)

No new supporting libraries needed.

| Area | Current Library | Status |
|------|----------------|--------|
| Migrations | Alembic 1.18.4 | Unchanged — already uses async `env.py` pattern; supports PostgreSQL URL transparently |
| Config | pydantic-settings 2.13.1 | Unchanged — `database_url` field already in `Settings`; ENV override is native |
| Testing | pytest + pytest-asyncio | Unchanged — PostgreSQL adapter tests use same fixture pattern as SQLite tests |

---

## Integration Points

### 1. Connection URL — ENV-Based Backend Switching

The existing `settings.py` already has:

```python
database_url: str = "sqlite+aiosqlite:///./data.db"
```

No new setting is required. Switching backends is done at deploy time via one ENV var:

```bash
# Development (default)
DATABASE_URL=sqlite+aiosqlite:///./data.db

# Production
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname
```

SQLAlchemy infers the driver and dialect from the URL scheme. No `STORAGE_BACKEND` flag, no conditional imports, no factory pattern beyond what already exists. This is the standard SQLAlchemy 2.0 pattern.

### 2. PostgreSQL Adapter Module

The new adapter lives at `src/adapters/driven/postgres/` alongside the existing `src/adapters/driven/sqlite/`. It implements the same `DataRepository` Protocol in `src/kernel/ports/repository.py` — no kernel changes needed for `add()` and `get()`.

The key implementation difference from the SQLite adapter is the upsert import:

**SQLite adapter (existing):**
```python
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
stmt = sqlite_insert(DataRecord).values(...).on_conflict_do_nothing(index_elements=["event_id"])
```

**PostgreSQL adapter (new):**
```python
from sqlalchemy.dialects.postgresql import insert as pg_insert
stmt = pg_insert(DataRecord).values(...).on_conflict_do_nothing(index_elements=["event_id"])
```

Both dialects expose the identical `.on_conflict_do_nothing()` API. The remaining repository logic (session factory, audit log transaction, `get()` query) is structurally identical — copy and adjust the import.

The ORM models in `src/adapters/driven/sqlite/models.py` use standard SQLAlchemy column types (`String`, `JSON`, `DateTime`, `Integer`) that are PostgreSQL-compatible without modification. `sa.JSON` maps to PostgreSQL `JSON` by default; upgrading to `JSONB` for indexing is a later optimization, not required for v2.0.

### 3. Alembic Migration Config

The existing `migrations/env.py` already uses `async_engine_from_config` — the correct async Alembic pattern. No `env.py` changes are needed.

To run migrations against PostgreSQL, override the URL at runtime:

```bash
# Option A: Update alembic.ini for production
sqlalchemy.url = postgresql+asyncpg://user:pass@host:5432/dbname

# Option B: Pass via -x flag (preferred for CI)
alembic -x sqlalchemy.url=$DATABASE_URL upgrade head
```

The migration versions themselves (DDL: `CREATE TABLE`, `CREATE INDEX`) are PostgreSQL-compatible as written. SQLite-specific constructs like `sqlite_insert` exist only in application code, not migrations.

### 4. QueryData Parameterized SQL — The Critical Pattern

The `DataRepository` port needs a `query()` method. The kernel's `QueryData` command will call it with filter parameters. The correct parameterization approach with SQLAlchemy + asyncpg is:

**Use `text()` with named parameters and dict execution:**
```python
from sqlalchemy import text

result = await session.execute(
    text("SELECT * FROM data_records WHERE model_name = :model AND connection_id = :conn"),
    {"model": model_name, "conn": connection_id},
)
```

SQLAlchemy's asyncpg dialect automatically rewrites `:named_param` syntax to PostgreSQL's native `$1` positional parameters before handing to asyncpg. The rewriting is handled transparently by the dialect layer. Named parameter style is the correct and safe pattern for the kernel query contract.

**Do NOT use `exec_driver_sql()` for parameterized queries.** That method bypasses SQLAlchemy's parameter rewriting and sends SQL directly to asyncpg, which only accepts `$1` positional syntax. Named parameters passed to `exec_driver_sql()` cause `PostgresSyntaxError`. Use `session.execute(text(...), dict)` instead — this is the established SQLAlchemy 2.0 pattern.

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| `asyncpg>=0.31.0` | `psycopg[binary]` (psycopg3) | If synchronous usage alongside async is required, or if COPY protocol / logical replication features are needed. asyncpg is faster in async-only workloads and is the more battle-tested SQLAlchemy asyncio dialect as of 2026. |
| Single `database_url` ENV var | Separate `STORAGE_BACKEND` flag + conditional factory | The flag approach adds conditional import complexity for zero benefit. URL-based switching is the canonical SQLAlchemy pattern and aligns with existing `pydantic-settings` setup. |
| Shared ORM models (existing `sqlite/models.py`) | Duplicate models in `postgres/models.py` | Sharing is correct for v2.0 since both adapters use the same schema. If PostgreSQL-specific column types (e.g., native `JSONB`, `UUID`) are needed in a future milestone, a PostgreSQL-specific model override is acceptable then. |
| `text()` with named params + dict | SQLAlchemy ORM `select()` constructs | ORM `select()` is better for complex joins and IDE type safety. For `QueryData` with user-supplied filters, `text()` with strict parameter binding is simpler and more transparent. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `exec_driver_sql()` for parameterized queries | Bypasses SQLAlchemy dialect layer; asyncpg rejects `:name` syntax at driver level, raising `PostgresSyntaxError` | `session.execute(text("... :param ..."), {"param": value})` |
| `psycopg2` (sync driver) | Incompatible with SQLAlchemy asyncio extension; blocks the event loop | `asyncpg` |
| `databases` library | Superseded by SQLAlchemy 2.0 async; adds a dependency without benefit | SQLAlchemy 2.0 `create_async_engine` (already in use) |
| String formatting in `text()` queries | SQL injection vulnerability for user-supplied filter values | Named parameters: `text("... :param"), {"param": value}` |
| `pytest-postgresql` | Unnecessary complexity for v2.0; the repository Protocol can be tested with a real PostgreSQL container in CI using the same in-code fixture pattern that exists for SQLite | Docker Compose `postgres:16-alpine` service in CI + `create_async_engine` fixture |

---

## Version Compatibility

| Package | Version | Compatible With | Notes |
|---------|---------|-----------------|-------|
| `asyncpg` | `>=0.31.0` | SQLAlchemy 2.0.48, Python 3.12, Python 3.13 | 0.31.0 ships binary wheels for CPython 3.10–3.14; no compilation needed. This is the latest stable release as of November 2025. |
| `sqlalchemy[asyncio]` | 2.0.48 (already pinned) | asyncpg 0.29+, aiosqlite 0.20+ | No upgrade needed; 2.0.48 fully supports the `postgresql+asyncpg` dialect |
| `alembic` | 1.18.4 (already pinned) | asyncpg via `async_engine_from_config` | `env.py` already uses the correct async pattern; no changes needed |

---

## Stack Patterns by Variant

**If running SQLite (development / CI without PostgreSQL):**
- `DATABASE_URL=sqlite+aiosqlite:///./data.db` (default in settings.py)
- `SQLiteDataRepository` with `sqlalchemy.dialects.sqlite.insert`
- In-memory for tests: `sqlite+aiosqlite:///:memory:`

**If running PostgreSQL (staging / production):**
- `DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname`
- `PostgreSQLDataRepository` with `sqlalchemy.dialects.postgresql.insert`
- Alembic URL also needs to point at PostgreSQL for migration runs

**If adding PostgreSQL integration tests in CI:**
- Use a Docker Compose service (`postgres:16-alpine`) and set `DATABASE_URL` in CI env
- Write a `conftest.py` fixture matching the existing SQLite pattern in `tests/integration/conftest.py`:
  ```python
  eng = create_async_engine(settings.database_url, echo=False)
  async with eng.begin() as conn:
      await conn.run_sync(Base.metadata.create_all)
  ```
- No `pytest-postgresql` or `pytest-mock-resources` needed for v2.0

---

## Sources

- [asyncpg on PyPI](https://pypi.org/project/asyncpg/) — version 0.31.0 confirmed, Python 3.12/3.13 wheels verified (HIGH confidence)
- [asyncpg GitHub releases](https://github.com/MagicStack/asyncpg/releases) — 0.31.0 release date November 24, 2025 confirmed (HIGH confidence)
- [SQLAlchemy 2.0 Async I/O docs](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html) — `postgresql+asyncpg://` URL format, `create_async_engine`, session patterns (HIGH confidence)
- [SQLAlchemy 2.0 PostgreSQL dialect docs](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html) — `from sqlalchemy.dialects.postgresql import insert` for `on_conflict_do_nothing()` (HIGH confidence)
- [SQLAlchemy issue #6452](https://github.com/sqlalchemy/sqlalchemy/issues/6452) — `exec_driver_sql` vs `execute(text())` for asyncpg named parameters; `execute(text(...), dict)` is correct and safe (HIGH confidence)
- [SQLAlchemy discussion #7192](https://github.com/sqlalchemy/sqlalchemy/discussions/7192) — asyncpg parameter rewriting handled by dialect layer when using `session.execute`; `text()` with named params works correctly (HIGH confidence)
- Codebase inspection (`pyproject.toml`, `uv.lock`, `settings.py`, `repository.py`, `session.py`, `migrations/env.py`) — SQLAlchemy 2.0.48, aiosqlite 0.20, Alembic 1.18.4 confirmed; asyncpg not yet present in lock file (HIGH confidence)

---
*Stack research for: data-hub v2.0 — PostgreSQL adapter, configurable backends, SQL query capability*
*Researched: 2026-03-19*
