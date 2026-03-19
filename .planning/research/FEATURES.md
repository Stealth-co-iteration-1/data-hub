# Feature Research

**Domain:** Data Hub Platform — v2.0 Production Storage & Query
**Researched:** 2026-03-19
**Confidence:** HIGH

> **Milestone scope:** This file focuses on NEW features for v2.0. The v1.0 features
> (AddData, SQLite persistence, webhook ingestion, audit trail, HMAC verification) are
> already validated and are treated as existing dependencies below.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete for v2.0.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **PostgreSQL adapter (asyncpg)** | Production deployments require PostgreSQL, not SQLite; any production data service is expected to run on a server-grade DB | MEDIUM | `postgresql+asyncpg://` URL; `sqlalchemy.dialects.postgresql.insert` for ON CONFLICT; replaces `sqlite_insert` import in repository |
| **ENV-based backend selection** | Standard twelve-factor app practice; operators switch `DATABASE_URL` to change backend | LOW | Already works via `settings.database_url`; needs a factory that routes to the right repository class based on URL scheme |
| **Idempotent inserts on PostgreSQL** | SQLite adapter already has this; users expect parity; duplicate webhooks are a production reality | MEDIUM | Use `sqlalchemy.dialects.postgresql.insert(...).on_conflict_do_nothing(index_elements=["event_id"])` — parallel to SQLite path |
| **QueryData command in kernel** | Any service storing data must expose a way to read it back; required before query HTTP endpoint | MEDIUM | Pure Python in `kernel/commands/` or `kernel/queries/`; parameterized SQL via `text()` with bound params; zero ORM leakage |
| **DataRepository.query() read port** | Port must be extended before adapters can implement it; kernel can't call `query()` if the protocol doesn't declare it | LOW | Add `query(sql: str, params: dict) -> list[dict]` to the `DataRepository` Protocol in `kernel/ports/repository.py` |
| **Query HTTP endpoint** | Data stored but not retrievable is useless; consumers of the hub need read access | MEDIUM | `POST /query` or `GET /data` with Pydantic-validated body; returns JSON list |
| **Alembic migration parity** | PostgreSQL DDL must match SQLite schema exactly; missing migration means data loss risk on first deploy | MEDIUM | Models already defined; confirm Alembic generates correct PG-compatible DDL; JSON column handled natively in PG |
| **Connection pool configuration** | PostgreSQL is a server process with a connection limit (default 100); async apps need pool_size + max_overflow | LOW | `create_async_engine(..., pool_size=5, max_overflow=10)` for PG; SQLite doesn't pool so this is PG-only |

### Differentiators (Competitive Advantage)

Features that elevate v2.0 beyond a minimal adapter swap.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Transparent backend swap with zero kernel changes** | Hexagonal architecture proof-of-concept; the kernel's handlers and commands don't know which DB is running | LOW | Factory creates correct repository class; kernel imports only the Protocol; this is the design goal of the architecture |
| **Parameterized SQL queries (injection-safe)** | Raw SQL queries over webhook data are high-risk if user input reaches the query; parameterized binding eliminates this | LOW | SQLAlchemy `text("SELECT ... WHERE model_name = :model", params={"model": value})`; bindparams enforced at protocol level |
| **Shared ORM models across adapters** | Same `DataRecord` and `AuditLog` model classes work for both SQLite and PostgreSQL; no model duplication | LOW | SQLAlchemy's `DeclarativeBase` generates compatible DDL for both dialects from same Python model; already nearly true |
| **Query results as plain dicts** | Consistent with existing pattern of never leaking ORM objects to kernel; query results are `list[dict]` | LOW | Iterate over `result.mappings()` and return `[dict(row) for row in result]`; same discipline as `repository.get()` |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **ORM query builder in kernel** | "Let's expose SQLAlchemy selects through the port" | Leaks ORM types into kernel, violating kernel purity constraint; kernel becomes coupled to SQLAlchemy | Keep kernel SQL as `str` with named bind params; adapter executes with `text()` |
| **Free-form SQL string from HTTP callers** | "Give callers full SQL control" | SQL injection surface is huge; any user input directly in a query string is dangerous; also couples callers to schema | Expose structured filter params (model_name, connection_id, date range); build SQL internally; never accept raw SQL from HTTP |
| **Separate PostgreSQL models** | "Duplicate the models.py for postgres-specific types" | Maintenance burden; two sources of truth for same schema | Single models.py in shared location; SQLAlchemy handles dialect-specific DDL automatically |
| **Synchronous Alembic env for async engine** | "Just add `run_sync` wrappers everywhere" | Works but creates async/sync impedance mismatch warnings; harder to maintain | Use `async_engine_from_config` in `alembic/env.py` with `connection.run_sync(do_run_migrations)` — the established async-alembic pattern |
| **Multiple active backends simultaneously** | "Route some traffic to SQLite, some to PG" | Splits the audit trail; causes consistency nightmares; not justified by any current requirement | One backend per deployment, selected by ENV; if multi-backend is needed later, add a routing layer on top of the protocol |
| **Database-specific query syntax per adapter** | "Use PG-specific window functions when PG is active" | Query logic in kernel uses whatever SQL is in the command; adapters can't interpret kernel intent to switch syntax | For v2.0, keep queries simple enough to run on both backends; diverge only if performance requires it and document clearly |

---

## Feature Dependencies

```
[PostgreSQL adapter]
    └──requires──> [DataRepository Protocol unchanged OR extended with query()]
    └──requires──> [Alembic migration for PG dialect]
    └──depends-on──> [Existing DataRecord / AuditLog ORM models]

[QueryData command]
    └──requires──> [DataRepository.query() read port declared in Protocol]
                       └──requires──> [PostgreSQL adapter implements query()]
                       └──requires──> [SQLite adapter implements query()]

[Query HTTP endpoint]
    └──requires──> [QueryData command]
    └──requires──> [FastAPI route wired to QueryDataHandler]

[ENV backend configuration]
    └──requires──> [Factory function / composition root that reads DATABASE_URL scheme]
    └──enhances──> [PostgreSQL adapter] (selects it when scheme == postgresql)
    └──enhances──> [SQLite adapter] (keeps it when scheme == sqlite)

[PostgreSQL connection pool]
    └──requires──> [PostgreSQL adapter]
    └──enhances──> [Performance under concurrent webhook ingestion]
```

### Dependency Notes

- **PostgreSQL adapter requires existing models unchanged:** `DataRecord` and `AuditLog` are already SQLAlchemy-generic; the adapter layer only needs a new repository class and a dialect-specific `insert()` import.
- **QueryData command requires Protocol extension first:** The `DataRepository` Protocol in `kernel/ports/repository.py` must declare `query()` before any handler can call it; both adapters must implement it before the handler ships.
- **Query HTTP endpoint is the last step in the chain:** It depends on QueryData command, which depends on the read port, which depends on both adapters implementing it. Phase ordering must reflect this.
- **ENV backend selection is a composition root concern:** `app.py` lifespan already creates the engine from `settings.database_url`; the factory just adds an `if "postgresql" in url` branch to pick the repository class.

---

## MVP Definition for v2.0

### Launch With (v2.0)

Minimum viable milestone — what's needed to promote to production.

- [ ] **PostgreSQL adapter class** — `PostgresDataRepository` implementing the existing Protocol; uses `asyncpg` driver via SQLAlchemy
- [ ] **Idempotent inserts on PostgreSQL** — `postgresql.insert().on_conflict_do_nothing()` to match SQLite behavior
- [ ] **ENV-based backend factory** — `app.py` or `dependencies.py` selects `SQLiteDataRepository` or `PostgresDataRepository` based on `DATABASE_URL` scheme
- [ ] **`DataRepository.query()` read port** — Added to Protocol; takes `sql: str` and `params: dict`, returns `list[dict[str, Any]]`
- [ ] **`QueryData` command + handler** — Pure kernel; handler calls `repository.query()`; no ORM imports
- [ ] **Both adapters implement `query()`** — SQLite and PostgreSQL repositories both implement the new port method
- [ ] **Query HTTP endpoint** — `POST /query` with Pydantic-validated request body; returns query results as JSON

### Add After Validation (v2.x)

- [ ] **Automated Alembic migration on startup** — Currently manual `alembic upgrade head`; known tech debt from v1.0; can now target PostgreSQL in CI
- [ ] **Query result pagination** — Add `limit`/`offset` to `query()` port signature when result sets grow large
- [ ] **Connection pool tuning** — Start with conservative defaults; tune after observing production connection patterns

### Future Consideration (v3+)

Already explicitly out of scope per PROJECT.md:

- [ ] **Event consumers** — Deferred to v3.0
- [ ] **Schema drift detection** — Deferred to v3.0
- [ ] **Real-time streaming** — Batch/webhook model is sufficient

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| PostgreSQL adapter (asyncpg) | HIGH | MEDIUM | P1 |
| Idempotent inserts on PostgreSQL | HIGH | LOW | P1 |
| ENV-based backend selection | HIGH | LOW | P1 |
| `DataRepository.query()` port extension | HIGH | LOW | P1 |
| `QueryData` command + handler (kernel) | HIGH | MEDIUM | P1 |
| SQLite adapter implements `query()` | HIGH | LOW | P1 |
| PostgreSQL adapter implements `query()` | HIGH | LOW | P1 |
| Query HTTP endpoint | HIGH | MEDIUM | P1 |
| Connection pool configuration | MEDIUM | LOW | P2 |
| Automated migration on startup | MEDIUM | MEDIUM | P2 |
| Query pagination | LOW | LOW | P2 |
| Schema drift detection | LOW | HIGH | P3 |
| Event consumers | LOW | HIGH | P3 |

**Priority key:**
- P1: Must have for v2.0 milestone completion
- P2: Should have, add when P1 features are stable
- P3: Explicitly deferred to v3.0 or later

---

## Implementation Complexity Assessment

### Low Complexity (hours, not days)

- `DataRepository.query()` read port declaration — add one method signature to the Protocol
- ENV-based backend factory — `if "postgresql" in settings.database_url` branch in lifespan
- Connection pool defaults in engine creation
- SQLite adapter `query()` implementation — `session.execute(text(sql).bindparams(**params))` + `result.mappings()`
- PostgreSQL adapter `query()` implementation — identical pattern; async session works the same

### Medium Complexity (1-3 days)

- `PostgresDataRepository` class — new file in `adapters/driven/postgres/`; mirrors SQLite repository structure; dialect-specific `insert()` import
- `QueryData` command + handler — new kernel files; command carries `sql: str`, `params: dict`; handler maps to read port
- Query HTTP endpoint — new FastAPI route; Pydantic request model; call query handler; format results

### High Complexity (not applicable for v2.0)

Nothing in v2.0 is architecturally novel. The hexagonal structure is established. The new features are extensions of existing patterns, not new patterns.

---

## Existing Features as Dependencies

These v1.0 features are load-bearing for v2.0. They must not be broken during the milestone.

| Existing Feature | How v2.0 Depends On It |
|------------------|------------------------|
| `DataRepository` Protocol | PostgreSQL adapter must implement the same Protocol; query port is added here |
| SQLite adapter | Continues to work for local development; must also implement `query()` |
| `AddData` handler | Unchanged; PostgreSQL adapter is a drop-in replacement behind the same Protocol |
| `settings.database_url` | Already the ENV variable; factory reads the scheme from this existing field |
| SQLAlchemy async session pattern | PostgreSQL adapter uses the same `async_sessionmaker` pattern; no new session management needed |
| Alembic migrations | PostgreSQL needs its own migration run; SQLite batch migrations are a separate concern |

---

## Sources

- [SQLAlchemy 2.0 Async Documentation](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html) — HIGH confidence
- [SQLAlchemy 2.1 PostgreSQL Dialect](https://docs.sqlalchemy.org/en/21/dialects/postgresql.html) — HIGH confidence (ON CONFLICT DO NOTHING)
- [Building High-Performance Async APIs with FastAPI, SQLAlchemy 2.0, and Asyncpg](https://leapcell.io/blog/building-high-performance-async-apis-with-fastapi-sqlalchemy-2-0-and-asyncpg) — MEDIUM confidence
- [Python + PostgreSQL: SQLAlchemy vs asyncpg Performance Comparison](https://dasroot.net/posts/2026/02/python-postgresql-sqlalchemy-asyncpg-performance-comparison/) — MEDIUM confidence
- [SQL Injection Defenses: Python SQLAlchemy Parameterized Query Best Practices 2026](https://johal.in/sql-injection-defenses-python-sqlalchemy-parameterized-query-best-practices-2026/) — MEDIUM confidence
- [Alembic Async Migration Discussion](https://github.com/sqlalchemy/alembic/discussions/1208) — MEDIUM confidence
- [Alembic Batch Migrations for SQLite](https://alembic.sqlalchemy.org/en/latest/batch.html) — HIGH confidence

---

*Feature research for: Data Hub Platform v2.0 — PostgreSQL adapter, configurable backends, SQL query capability*
*Researched: 2026-03-19*
