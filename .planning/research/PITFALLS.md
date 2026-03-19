# Pitfalls Research

**Domain:** Python hexagonal service — PostgreSQL adapter, multi-backend configuration, SQL query interface
**Researched:** 2026-03-19
**Confidence:** HIGH (all critical items verified against official docs and multiple authoritative sources)

> This file was updated for v2.0 milestone research. It supersedes the v1.0 pitfalls for the new
> active requirements: PostgreSQL adapter (asyncpg), configurable storage backend, QueryData command.
> v1.0 pitfalls that remain relevant (kernel purity, transaction boundaries, idempotency) are
> retained at the bottom under "Carried-Forward Pitfalls."

---

## Critical Pitfalls

### Pitfall 1: Dialect-Specific ON CONFLICT Breaks on Backend Swap

**What goes wrong:**
The existing `SQLiteDataRepository.add()` imports `from sqlalchemy.dialects.sqlite import insert as sqlite_insert` and calls `.on_conflict_do_nothing()`. When writing the PostgreSQL adapter, copying this pattern with the wrong import produces a runtime error. SQLAlchemy's SQLite and PostgreSQL dialects expose structurally similar but incompatible `insert` constructors. The PostgreSQL equivalent requires `from sqlalchemy.dialects.postgresql import insert as pg_insert`. Using the SQLite import against a PostgreSQL engine raises `CompileError` at query execution time, not at import time.

**Why it happens:**
Both dialects support `ON CONFLICT DO NOTHING` syntactically. Developers assume "same feature, same code" and copy the adapter without auditing the dialect import. The problem is invisible until the PostgreSQL engine executes the statement.

**How to avoid:**
Each adapter file imports only its own dialect insert. The PostgreSQL adapter uses `pg_insert(...).on_conflict_do_nothing(index_elements=["event_id"])`. Do not share insert construction logic between adapters via a common utility. Write an explicit integration test that inserts a record with a duplicate `event_id` against a real PostgreSQL connection and asserts `rowcount == 0` without raising an exception.

**Warning signs:**
- `sqlalchemy.dialects.sqlite` appears in the PostgreSQL adapter module file
- No integration test for duplicate `event_id` runs against the PostgreSQL engine (only SQLite or in-memory)
- `CompileError: Unconsumed column names` or `AttributeError` at first PostgreSQL insert

**Phase to address:**
PostgreSQL adapter phase. Acceptance criteria must include: idempotency test passes against a PostgreSQL fixture, not only the existing in-memory SQLite fixture.

---

### Pitfall 2: alembic.ini Hardcodes SQLite URL — Migrations Silently Target Wrong Database

**What goes wrong:**
`alembic.ini` line 89 is `sqlalchemy.url = sqlite+aiosqlite:///./data.db`. When `alembic upgrade head` is run in any PostgreSQL environment (CI, staging, production), if `migrations/env.py` reads the URL from `alembic.ini` without first checking `DATABASE_URL` from the environment, migrations execute against the local SQLite file. The command exits 0, the PostgreSQL instance is never migrated, and the first request fails with a missing-table error — in production.

**Why it happens:**
The current `migrations/env.py` calls `config.get_main_option("sqlalchemy.url")` directly. This works in local development where the fallback is correct. The ENV override pattern is not enforced, so any environment where `alembic.ini` is not edited will silently use the wrong database.

**How to avoid:**
Update `migrations/env.py` to read `DATABASE_URL` from the environment and set it before Alembic uses the URL:

```python
import os
url = os.environ.get("DATABASE_URL") or config.get_main_option("sqlalchemy.url")
config.set_main_option("sqlalchemy.url", url)
```

Keep `alembic.ini`'s value as the local development fallback only. Add a CI job that spins up a PostgreSQL container and runs `alembic upgrade head` against it as a required check before merging migrations.

**Warning signs:**
- `alembic upgrade head` finishes instantly with no schema changes visible in PostgreSQL
- No `alembic_version` row in the PostgreSQL database after running the command
- Production service raises `sqlalchemy.exc.OperationalError: table data_records does not exist` on first request
- `alembic.ini` contains the actual production database URL (means someone edited the file instead of using ENV)

**Phase to address:**
Migration compatibility phase, before any PostgreSQL deployment. The phase is not complete until a CI job runs migrations against a live PostgreSQL container.

---

### Pitfall 3: SQL Injection via Identifier Parameterization in QueryData

**What goes wrong:**
`QueryData` accepts user-supplied filter inputs. SQLAlchemy's `text()` with bound parameters (`:param`) safely handles values. However, SQL identifiers — table names, column names, ORDER BY fields — cannot be parameterized. If any identifier portion is derived from user input via string interpolation (`f"SELECT * FROM {model_name} WHERE ..."`), the query is directly injectable regardless of how the values are bound. The `data_records` table stores JSON blobs; a query interface that allows filtering on JSON paths or column references is particularly exposed.

**Why it happens:**
Developers correctly apply bound parameters for values and assume this protects the whole query. The false assumption: "I'm using SQLAlchemy `text()` so I'm safe." This is true only for value placeholders. Table names and column names are not parameterizable in SQL — the database treats them as structure, not data.

**How to avoid:**
Define an allowlist of permitted filter fields in the kernel's `QueryData` command or handler (e.g., `model_name`, `connection_id`, `created_at`). Validate all identifier portions against this allowlist in the adapter before constructing the query string. Values go through bound parameters; identifiers go through the allowlist with an explicit rejection if not matched.

Prefer ORM-level `select()` with explicit column references over `text()` for the query adapter. If raw SQL is necessary, build the query structure with pre-validated identifiers and only pass values as bound params.

The query HTTP endpoint must accept structured parameters (model, filters, limit) — never a raw SQL string from the client.

**Warning signs:**
- The `query_sql` or equivalent field accepts arbitrary strings from the HTTP request body
- No allowlist validation exists in the `QueryData` command, handler, or adapter
- Test suite does not include an injection attempt test (e.g., `; DROP TABLE data_records --` as a filter value)
- `session.execute(text(f"... {user_input} ..."))` appears anywhere in the query adapter

**Phase to address:**
QueryData command and query HTTP endpoint phase. Injection test cases are acceptance criteria, not a deferred security review item.

---

### Pitfall 4: Connection Pool Misconfiguration Causes Production Request Timeouts

**What goes wrong:**
The current `app.py` creates an `AsyncEngine` with no pool parameters, relying on SQLAlchemy defaults (`pool_size=5`, `max_overflow=10`). For aiosqlite, pooling is irrelevant because SQLite serializes writes. For PostgreSQL under concurrent load, the default pool is too small. With multiple Uvicorn workers, each creates its own engine with its own pool. At 4 workers: `4 × (5 + 10) = 60` maximum connections at peak. PostgreSQL's default `max_connections` is 100. Without PgBouncer the connection count grows with workers. With PgBouncer in transaction mode, asyncpg's prepared-statement cache causes intermittent `InvalidCachedStatementError`.

**Why it happens:**
Pool configuration that works for development SQLite is carried unchanged to the PostgreSQL engine. The failure only surfaces under concurrent load in production or during load tests, not in unit tests.

**How to avoid:**
When creating the PostgreSQL engine, set explicit pool parameters:
- `pool_size=5`, `max_overflow=10` per worker as a safe starting point
- `pool_recycle=300` to match PostgreSQL's `idle_in_transaction_session_timeout`
- `pool_pre_ping=True` to detect stale connections before use
- If PgBouncer is in the deployment stack: `connect_args={"statement_cache_size": 0}` to disable asyncpg prepared-statement caching

Expose `db_pool_size` and `db_max_overflow` as ENV-configurable parameters in `Settings` so pool sizing can be tuned per environment without code changes.

**Warning signs:**
- `sqlalchemy.exc.TimeoutError: QueuePool limit of size 5 overflow 10 reached` under concurrent requests
- Intermittent `asyncpg.exceptions.InvalidCachedStatementError` — PgBouncer in transaction mode with prepared statements
- `OperationalError: server closed the connection unexpectedly` after idle periods — missing `pool_recycle`
- `pool_size` is not present in the `Settings` class or the engine creation call

**Phase to address:**
PostgreSQL adapter phase. Load test with at least 20 concurrent requests before marking the phase done.

---

### Pitfall 5: Hardcoded Repository Import Bypasses the Configurable Backend

**What goes wrong:**
`dependencies.py` currently hardcodes `from src.adapters.driven.sqlite.repository import SQLiteDataRepository` and always instantiates `SQLiteDataRepository`. When the PostgreSQL adapter is added but the dependency wiring is not updated, the service always uses SQLite regardless of `DATABASE_URL`. The PostgreSQL adapter exists but is never invoked in production. This failure mode is silent — the service starts, responds to requests, and appears healthy.

**Why it happens:**
In v1 there was only one adapter so direct instantiation was appropriate. Adding a second adapter without a factory creates an implicit coupling: the driving adapter (FastAPI) selects the driven adapter (repository) inline, which is the opposite of the hexagonal intent. The "configurable backend" requirement reads like a configuration concern but is actually a composition-root concern.

**How to avoid:**
Introduce a repository factory function in the composition root (`app.py` lifespan or a dedicated factory module). The factory reads `settings.database_url` (or a `settings.storage_backend` enum) and returns the appropriate concrete repository. The factory is the only place that imports both concrete adapters.

```python
def make_repository(session_factory, database_url: str) -> DataRepository:
    if database_url.startswith("postgresql"):
        return PostgreSQLDataRepository(session_factory)
    return SQLiteDataRepository(session_factory)
```

Test the factory: assert that `DATABASE_URL=sqlite+aiosqlite://...` yields `SQLiteDataRepository` and `DATABASE_URL=postgresql+asyncpg://...` yields `PostgreSQLDataRepository`.

**Warning signs:**
- `SQLiteDataRepository` is still the only import in `dependencies.py` after the PostgreSQL adapter is merged
- There is no factory function or conditional instantiation at the composition root
- The `/health` endpoint does not report which storage backend is active

**Phase to address:**
Configurable backend phase. The factory test must run as part of the phase acceptance criteria.

---

### Pitfall 6: batch_alter_table Migrations Are SQLite-Specific — Future Migrations May Break PostgreSQL

**What goes wrong:**
`002_rename_columns.py` uses `op.batch_alter_table()` — the SQLite-specific workaround for `ALTER TABLE` operations that SQLite does not support natively. On PostgreSQL, Alembic generates standard `ALTER COLUMN` inside the batch block, which works correctly. The risk runs in the other direction: future migrations written with PostgreSQL-specific syntax (`CREATE INDEX CONCURRENTLY`, enum types, `GENERATED ALWAYS AS IDENTITY`, `JSONB` operators) will fail on SQLite. The CI test environment that runs migrations against SQLite in-memory will not catch PostgreSQL-specific failures — they only appear in production.

**Why it happens:**
The "develop on SQLite, deploy to PostgreSQL" discipline requires testing migrations against both dialects. This discipline is easy to skip under time pressure. Developers write a migration, run it locally against SQLite, see it pass, and merge it. The PostgreSQL-specific syntax fails only when the migration runs against the production database.

**How to avoid:**
- Always use `op.batch_alter_table()` for schema changes that must work on both dialects (column renames, drops, type changes that SQLite needs recreated)
- Avoid PostgreSQL-specific DDL syntax in standard migrations; isolate it behind a dialect check if unavoidable
- Add a CI job that runs `alembic upgrade head` and `alembic downgrade base` against a PostgreSQL Docker service as a required check for every migration PR
- Test both `upgrade()` and `downgrade()` against both dialects before merging

**Warning signs:**
- Migration files use `op.execute("ALTER TABLE ...")` directly without a batch context
- No PostgreSQL Docker service in CI for migration testing
- `downgrade()` is not implemented (`pass` body)
- Migrations are only validated with `sqlite+aiosqlite:///:memory:`

**Phase to address:**
Migration compatibility phase. Acceptance criteria: all three existing migrations (`001`, `002`, and any new v2.0 migration) pass `alembic upgrade head` and `alembic downgrade base` against a PostgreSQL container in CI.

---

### Pitfall 7: Unbound Query Result Size — DoS via Expensive Query

**What goes wrong:**
The `QueryData` command, if it does not enforce a result cap, allows any caller to issue a query that returns the entire `data_records` table. A single request matching all rows (e.g., filtering only on `model_name`) returns potentially millions of JSON blobs in one HTTP response. The FastAPI worker processing this response exhausts memory and crashes, or takes long enough to starve the connection pool.

**Why it happens:**
The query interface is built for developer convenience and tested with small datasets. The default behavior of `SELECT ... WHERE model_name = :m` has no implicit limit. The problem is invisible in development but catastrophic in production once data accumulates.

**How to avoid:**
Enforce a hard `LIMIT` in the query adapter — unconditionally, not only when the client requests it. Make the default limit and the maximum limit ENV-configurable:

```
DEFAULT_QUERY_LIMIT=100
MAX_QUERY_LIMIT=1000
```

The query HTTP endpoint returns a 400 if the client requests a limit above the configured maximum. The query adapter appends `LIMIT :limit` to every query regardless of client input.

**Warning signs:**
- The query adapter has no `LIMIT` clause
- `MAX_QUERY_LIMIT` is not in `Settings`
- Load testing the query endpoint with `model_name=hubspot_contact` on a populated database shows response sizes > 10MB

**Phase to address:**
QueryData command and query endpoint phase. The limit enforcement is a hard requirement, not an optimization.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| `alembic.ini` URL without ENV override | Zero config for local dev | Silent migration to wrong DB in production | Never — fix before first PostgreSQL deployment |
| Hardcoded `SQLiteDataRepository` in `dependencies.py` | Fewer files to change | PostgreSQL adapter bypassed in production | Never once the second adapter exists |
| f-string identifier interpolation in `text()` queries | Rapid query prototyping | SQL injection vulnerability in a public endpoint | Never in any externally reachable interface |
| Default pool parameters for PostgreSQL engine | Zero config change needed | Request timeouts under concurrent production load | MVP with single worker and < 5 concurrent requests |
| No `downgrade()` implementation in migrations | Faster migration authoring | Cannot roll back a bad production migration | Never in a service with live production data |
| No result cap on query endpoint | Simpler initial implementation | DoS via expensive query, worker OOM | Never once real data accumulates |
| PgBouncer in transaction mode without disabling prepared statements | PgBouncer scales connections | Intermittent `InvalidCachedStatementError` in asyncpg | Never — always set `statement_cache_size=0` with transaction-mode PgBouncer |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| asyncpg + PgBouncer | Transaction-mode pooler breaks asyncpg prepared-statement cache | Pass `connect_args={"statement_cache_size": 0}` to disable caching |
| Alembic + PostgreSQL | `alembic.ini` URL used instead of `DATABASE_URL` env var | Override URL in `env.py` from `os.environ.get("DATABASE_URL")` before running |
| SQLAlchemy `text()` + user input identifiers | Interpolating table/column names from user input into the SQL string | Values: bound params (`:param`). Identifiers: validated allowlist only |
| SQLAlchemy dialect imports | Copying `sqlite_insert` into the PostgreSQL adapter | Each adapter uses its own dialect import — no sharing of insert construction |
| FastAPI lifespan + async engine | `await engine.dispose()` omitted on shutdown | Always dispose in the lifespan exit path to prevent connection leak warnings |
| PostgreSQL `JSON` column storage | SQLite stores JSON as text; PostgreSQL stores as binary (JSONB when cast) | Use SQLAlchemy `JSON` type, not `JSONB`, if cross-dialect compatibility is needed |
| `pool_pre_ping` omitted | Stale connections after idle periods cause `OperationalError` on first use | Set `pool_pre_ping=True` on the PostgreSQL engine always |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Default `pool_size=5` per Uvicorn worker | `QueuePool limit reached` errors under concurrent requests | Set `pool_size`/`max_overflow` as ENV-configurable; tune per worker count | > 5 concurrent requests per worker |
| Missing `pool_pre_ping=True` | `OperationalError: connection closed` on first request after idle | Add `pool_pre_ping=True` to `create_async_engine()` | After ~5 minutes idle with default PostgreSQL idle timeout |
| Missing `pool_recycle=300` | Stale connections after PostgreSQL reclaims idle sessions | Set `pool_recycle=300` (match `idle_in_transaction_session_timeout`) | When idle > 300 seconds in production |
| Unbound query result size | Worker OOM or slow response on queries matching large row counts | Enforce unconditional `LIMIT` in the query adapter; ENV-configurable max | > 10k rows matching a query in production |
| Full table scan on `data_records` without index hit | Slow queries on large datasets | Existing indexes on `model_name` and `connection_id` cover primary filter paths — verify they survive migrations | > 100k rows in `data_records` |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Identifier interpolation in `text()` | SQL injection allowing data exfiltration or deletion | Allowlist all identifier inputs; reject anything not on the list |
| Accepting raw SQL strings from HTTP clients | Full SQL execution as the service DB user | Accept structured parameters only (model, filters, limit) — never a raw SQL string |
| Database user with DDL permissions | SQL injection can drop or alter tables | Create a dedicated PostgreSQL role with only `SELECT`, `INSERT` on `data_records` and `audit_log` |
| Connection string with credentials in `alembic.ini` | Credentials committed to the repository | `alembic.ini` must never contain real credentials; always load from environment |
| No result size cap on query endpoint | DoS via query returning millions of rows | Enforce a hard `LIMIT` unconditionally in the query adapter |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Query endpoint returns internal ORM fields | Consumers see `event_id`, internal adapter internals | Response schema exposes only `id`, `model_name`, `connection_id`, `data`, `created_at` |
| Query validation errors surface as 500 | Callers cannot distinguish invalid filter from server error | Return 400 with `{"error": "invalid_filter", "field": "model_name"}` for input failures |
| Active backend not visible at runtime | Operators cannot confirm which storage backend is in use | Include `storage_backend` (e.g., `"sqlite"` or `"postgresql"`) in the `/health` response body |
| Query error messages expose SQL internals | Security risk and poor UX | Catch `sqlalchemy.exc` in the adapter and return a generic structured error to the HTTP layer |

---

## "Looks Done But Isn't" Checklist

- [ ] **PostgreSQL adapter idempotency:** Duplicate `event_id` inserts tested against a real PostgreSQL connection — `rowcount == 0` without exception. Not only SQLite.
- [ ] **Backend switching:** Setting `DATABASE_URL=postgresql+asyncpg://...` actually routes to `PostgreSQLDataRepository`. Verified with a factory unit test.
- [ ] **Alembic on PostgreSQL:** `alembic upgrade head` has run successfully against a PostgreSQL container in CI, not only validated locally against SQLite.
- [ ] **QueryData injection prevention:** A test exists that submits an injection-attempt input as a filter value and confirms it is safely rejected or parameterized.
- [ ] **Engine disposal:** `await engine.dispose()` is called in the FastAPI lifespan exit path for the PostgreSQL engine.
- [ ] **Query result cap:** Every query through the query adapter includes an unconditional `LIMIT`. Cannot be omitted by the client to return unlimited rows.
- [ ] **Health endpoint reports active backend:** `/health` response body includes `storage_backend` so operators can confirm configuration at runtime.
- [ ] **Pool parameters are ENV-configurable:** `pool_size` and `max_overflow` read from environment variables — not hardcoded — so production can be tuned without a code deploy.
- [ ] **Migration downgrade works:** `alembic downgrade base` runs without error against both SQLite and PostgreSQL.
- [ ] **No credentials in alembic.ini:** The `sqlalchemy.url` line in `alembic.ini` contains only the local dev fallback — no production credentials.

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Migrations ran against SQLite instead of PostgreSQL in production | HIGH | Run `alembic upgrade head` with correct `DATABASE_URL`; if schema already exists, `alembic stamp head` to mark as current; verify with `alembic current` |
| SQL injection through query interface | HIGH | Disable query endpoint immediately; audit database access logs for exfiltration; patch with allowlist validation before re-enabling |
| Connection pool exhaustion | MEDIUM | Restart workers to release connections; add `pool_size`/`max_overflow` ENV vars and redeploy; temporarily reduce worker count |
| Wrong repository instantiated (SQLite in production) | MEDIUM | Set `DATABASE_URL` correctly and restart; verify via `/health` endpoint that `storage_backend` matches expected |
| Migration fails on PostgreSQL (dialect-specific syntax) | LOW | Rewrite migration using standard SQLAlchemy operations compatible with both dialects; test against both before re-running |
| Stale connections after idle period | LOW | Add `pool_pre_ping=True` and `pool_recycle=300`; deploy new version; no data loss, only transient errors until deployed |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Dialect-specific ON CONFLICT (SQLite import in PostgreSQL adapter) | PostgreSQL adapter | Idempotency test passes against PostgreSQL fixture — `rowcount == 0` on duplicate `event_id` |
| `alembic.ini` hardcoded URL bypasses PostgreSQL deployment | Migration compatibility | CI job: `alembic upgrade head` against PostgreSQL Docker service passes on every migration PR |
| SQL injection via identifier interpolation in QueryData | QueryData command + endpoint | Injection-attempt test is part of acceptance criteria; no identifier from user input appears unvalidated |
| Connection pool misconfiguration | PostgreSQL adapter | Load test: 20 concurrent requests complete without `QueuePool limit reached` error |
| Hardcoded repository bypasses backend switching | Configurable backend | Factory test: `sqlite://` URL → `SQLiteDataRepository`; `postgresql://` URL → `PostgreSQLDataRepository` |
| batch_alter_table migration incompatible with PostgreSQL | Migration compatibility | CI: all migrations run `upgrade` + `downgrade` against PostgreSQL without error |
| Unbound query result size | QueryData endpoint | Test: query with no limit returns at most `MAX_QUERY_LIMIT` rows; request above cap returns 400 |

---

## Carried-Forward Pitfalls (from v1.0 Research)

The following pitfalls from the original research remain relevant for this milestone and are preserved for reference:

**Kernel purity:** The PostgreSQL adapter must not bleed into the kernel. `src/kernel/` must have zero imports from `sqlalchemy`, `asyncpg`, or any external dependency. The kernel's `DataRepository` Protocol defines the query port; the adapter implements it without the kernel knowing.

**Transaction boundaries:** Both the SQLite and PostgreSQL adapters manage transactions internally using `async with session.begin()`. The kernel does not control commit/rollback. Introducing a `query()` port method must follow the same pattern — the adapter opens and closes its own session, returning a plain dict or list to the kernel.

**Idempotency:** The `ON CONFLICT DO NOTHING` logic implemented in `SQLiteDataRepository` must be replicated in `PostgreSQLDataRepository` using the PostgreSQL dialect's insert construct. Do not remove idempotency in the PostgreSQL adapter assuming "PostgreSQL is more reliable" — webhook retry storms are a transport-level concern, not a database reliability concern.

---

## Sources

- [SQLAlchemy 2.0 PostgreSQL Dialect — ON CONFLICT documentation](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html?highlight=conflict)
- [SQLAlchemy 2.0 SQLite Dialect — ON CONFLICT documentation](https://docs.sqlalchemy.org/en/20/dialects/sqlite.html)
- [Alembic — Running Batch Migrations for SQLite and Other Databases](https://alembic.sqlalchemy.org/en/latest/batch.html)
- [Alembic — Maintaining same schema for SQLite and PostgreSQL (Discussion)](https://github.com/sqlalchemy/alembic/discussions/1009)
- [Alembic — Get database URL from env instead of ini (Discussion)](https://github.com/sqlalchemy/alembic/discussions/1043)
- [asyncpg FAQ — PgBouncer and prepared statements](https://magicstack.github.io/asyncpg/current/faq.html)
- [SQLAlchemy — Async connection not returned to pool on task cancellation (Issue #8145)](https://github.com/sqlalchemy/sqlalchemy/issues/8145)
- [How to properly set pool_size and max_overflow in SQLAlchemy for ASGI apps](https://www.pythontutorials.net/blog/how-to-properly-set-pool-size-and-max-overflow-in-sqlalchemy-for-asgi-app/)
- [QueuePool limit lockup issue — fastapi/full-stack-fastapi-template (Issue #104)](https://github.com/tiangolo/full-stack-fastapi-postgresql/issues/104)
- [SQLAlchemy raw query SQL injection vulnerability — Sourcery](https://www.sourcery.ai/vulnerabilities/python-sqlalchemy-security-sqlalchemy-execute-raw-query)
- [Datadog static analysis — disable sqlalchemy text()](https://docs.datadoghq.com/security/code_security/static_analysis/static_analysis_rules/python-flask/disable-sqlalchemy-text/)
- [Preventing SQL Injection Attacks with Python — Real Python](https://realpython.com/prevent-python-sql-injection/)
- [Supabase pooling and asyncpg — PgBouncer incompatibility](https://medium.com/@patrickduch93/supabase-pooling-and-asyncpg-dont-mix-here-s-the-real-fix-44f700b05249)

---
*Pitfalls research for: PostgreSQL adapter, configurable storage backends, SQL query interface on existing hexagonal Python service*
*Researched: 2026-03-19*
