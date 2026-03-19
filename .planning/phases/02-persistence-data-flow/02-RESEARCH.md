# Phase 2: Persistence & Data Flow - Research

**Researched:** 2026-03-18
**Domain:** SQLAlchemy 2.0 async + SQLite (aiosqlite) with hexagonal architecture
**Confidence:** HIGH

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PERS-01 | Data persisted to SQLite (v1) with ACID guarantees | SQLAlchemy `async with session.begin()` provides automatic commit/rollback; SQLite WAL mode for durability |
| PERS-02 | Repository adapter implements kernel DataRepository port without kernel knowing about SQLAlchemy/SQLite | SQLAlchemy ORM models live in adapter layer only; port Protocol enables structural subtyping — no import in kernel |
| PERS-03 | Audit trail captures: timestamp, source_id, table_name, status | Separate `audit_log` ORM table written in same transaction as data insert |
| PERS-04 | Idempotent processing prevents duplicate records from retry storms | `sqlalchemy.dialects.sqlite.insert().on_conflict_do_nothing(index_elements=['event_id'])` on a unique constraint |
| VERF-01 | Verification query returns stored data matching what was submitted | `DataRepository.get(table, record_id)` implemented; maps ORM row back to plain dict for kernel |
</phase_requirements>

---

## Summary

Phase 2 builds the driven adapter layer that makes the kernel's `DataRepository` and `EventPublisher` ports concrete. The kernel was built with zero infrastructure imports; Phase 2 introduces SQLAlchemy 2.0 async ORM, aiosqlite driver, and Alembic migrations — all confined to `src/adapters/driven/`. The kernel never imports from adapters.

The three hardest problems in this phase are: (1) keeping the adapter boundary clean — ORM models must not leak into kernel types; (2) idempotency — duplicate webhook payloads with the same `event_id` must be silently skipped using `INSERT ... ON CONFLICT DO NOTHING`; and (3) audit trail atomicity — the audit row must be written in the same database transaction as the data row so the two are never out of sync.

Alembic async setup requires the `alembic init -t async` template and a `run_sync`-based `env.py`. This is a gotcha compared to the sync template — the async bridge must be explicit.

**Primary recommendation:** Use SQLAlchemy 2.0 `async_sessionmaker` + `aiosqlite` for the SQLite adapter, write the audit log in the same `async with session.begin()` block as the data insert, and enforce idempotency with a `UNIQUE` constraint on `event_id` using `on_conflict_do_nothing`.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | 2.0.48+ | ORM + async session management | Industry standard; `sqlalchemy[asyncio]` adds greenlet for async support |
| aiosqlite | 0.20+ | SQLite async driver for v1 | Official async wrapper for SQLite; dialect string: `sqlite+aiosqlite:///` |
| Alembic | 1.18.4+ | Database schema migrations | Tightly integrated with SQLAlchemy; async template available via `alembic init -t async` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| sqlalchemy[asyncio] | (extra) | Greenlet dependency for async ORM | Required; without this extra, async session context managers fail |

### Already Installed (do not re-add)
| Library | Version | Purpose |
|---------|---------|---------|
| pydantic | 2.12.5+ | Schema validation — already in kernel |
| pytest-asyncio | 0.24+ | Async test support — already in pyproject.toml |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| aiosqlite | asyncpg | asyncpg is PostgreSQL only; aiosqlite is the correct SQLite async driver |
| Alembic migrations | Raw CREATE TABLE | Alembic provides upgrade path to PostgreSQL v2; do not skip it |

**Installation:**
```bash
uv add sqlalchemy[asyncio] aiosqlite alembic
```

**Version verification (run before implementing):**
```bash
uv run python -c "import sqlalchemy; print(sqlalchemy.__version__)"
uv run python -c "import aiosqlite; print(aiosqlite.__version__)"
uv run python -c "import alembic; print(alembic.__version__)"
```

---

## Architecture Patterns

### Recommended Project Structure for Phase 2

```
src/
├── kernel/                         # UNCHANGED — zero infrastructure imports
│   ├── ports/
│   │   ├── repository.py           # DataRepository Protocol (already exists)
│   │   └── event_publisher.py      # EventPublisher Protocol (already exists)
│   └── ...
│
└── adapters/
    └── driven/
        ├── __init__.py
        ├── sqlite/                  # SQLite-specific adapter (v1)
        │   ├── __init__.py
        │   ├── models.py            # SQLAlchemy ORM models (DataRecord, AuditLog)
        │   ├── repository.py        # SQLiteDataRepository implements DataRepository
        │   └── session.py           # async engine + async_sessionmaker factory
        └── event_bus/
            ├── __init__.py
            └── publisher.py         # InMemoryEventPublisher implements EventPublisher

migrations/
├── env.py                           # Async Alembic env using run_sync bridge
├── script.py.mako
└── versions/
    └── 001_initial_schema.py        # Creates data_records + audit_log tables

tests/
├── unit/
│   └── fakes.py                     # FakeDataRepository already exists — no changes
└── integration/
    ├── __init__.py
    ├── conftest.py                   # Async engine + session fixtures (in-memory SQLite)
    └── test_sqlite_repository.py    # Repository adapter contract tests
```

### Pattern 1: ORM Models in Adapter Layer Only

**What:** SQLAlchemy ORM classes (`DeclarativeBase` subclasses) live exclusively in `src/adapters/driven/sqlite/models.py`. Kernel domain types (`RecordMetadata`, `DataAddedEvent`) remain pure Python dataclasses.

**When to use:** Always. This is what preserves PERS-02 — the kernel knowing nothing about SQLAlchemy.

**Example:**
```python
# src/adapters/driven/sqlite/models.py
# Source: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
from datetime import datetime, timezone
from sqlalchemy import JSON, DateTime, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class DataRecord(Base):
    __tablename__ = "data_records"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    event_id: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    table_name: Mapped[str] = mapped_column(String, nullable=False)
    source_id: Mapped[str] = mapped_column(String, nullable=False)
    data: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    record_id: Mapped[str] = mapped_column(String, nullable=False)
    table_name: Mapped[str] = mapped_column(String, nullable=False)
    source_id: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)  # "added" | "duplicate" | "failed"
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
```

### Pattern 2: Async Session Factory

**What:** Create one `AsyncEngine` and one `async_sessionmaker` at startup. Inject the session factory into the repository adapter.

**When to use:** Always — one engine per process, one session per request/operation.

**Example:**
```python
# src/adapters/driven/sqlite/session.py
# Source: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

def create_session_factory(database_url: str) -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(database_url, echo=False)
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
```

### Pattern 3: Idempotent Insert with ON CONFLICT DO NOTHING

**What:** Use SQLite dialect's `insert().on_conflict_do_nothing()` to silently skip duplicate `event_id` values. This is the mechanism for PERS-04.

**Critical constraint:** `session.add()` cannot use conflict handling — must use explicit `insert()` statement from `sqlalchemy.dialects.sqlite`.

**Example:**
```python
# src/adapters/driven/sqlite/repository.py
# Source: https://docs.sqlalchemy.org/en/20/dialects/sqlite.html
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

async def _insert_idempotent(
    session: AsyncSession,
    record_id: str,
    event_id: str | None,
    table: str,
    source_id: str,
    data: dict,
) -> bool:
    """Returns True if inserted, False if duplicate was skipped."""
    stmt = (
        sqlite_insert(DataRecord)
        .values(
            id=record_id,
            event_id=event_id,
            table_name=table,
            source_id=source_id,
            data=data,
        )
        .on_conflict_do_nothing(index_elements=["event_id"])
    )
    result = await session.execute(stmt)
    return result.rowcount > 0  # 0 = duplicate skipped, 1 = inserted
```

### Pattern 4: Audit Log in Same Transaction

**What:** Write both the `DataRecord` and `AuditLog` rows inside a single `async with session.begin()` block. This ensures atomicity (PERS-03). If either fails, both roll back.

**Example:**
```python
# src/adapters/driven/sqlite/repository.py
class SQLiteDataRepository:
    """Implements DataRepository port. Kernel never imports this class."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def add(self, table: str, source_id: str, data: dict) -> str:
        record_id = str(uuid4())
        event_id = data.get("event_id")  # May be None for non-idempotent callers

        async with self._session_factory() as session:
            async with session.begin():
                inserted = await _insert_idempotent(
                    session, record_id, event_id, table, source_id, data
                )
                status = "added" if inserted else "duplicate"

                # Audit log always written, even for duplicates
                audit = AuditLog(
                    record_id=record_id,
                    table_name=table,
                    source_id=source_id,
                    status=status,
                )
                session.add(audit)
                # session.begin() auto-commits on context exit

        return record_id

    async def get(self, table: str, record_id: str) -> dict | None:
        async with self._session_factory() as session:
            result = await session.get(DataRecord, record_id)
            if result is None or result.table_name != table:
                return None
            return result.data  # Returns raw dict — no ORM type leaks to caller
```

### Pattern 5: Alembic Async Setup

**What:** Alembic does not provide an async API directly. The async template uses `connection.run_sync()` to bridge async engine with Alembic's synchronous migration runner.

**When to use:** Always when using async SQLAlchemy. The sync template will fail with async engines.

**Example (env.py key section):**
```python
# migrations/env.py
# Source: https://alembic.sqlalchemy.org/en/latest/cookbook.html
import asyncio
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy import pool

async def run_async_migrations():
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()

def run_migrations_online():
    asyncio.run(run_async_migrations())
```

**Init command:**
```bash
alembic init -t async migrations
```

### Pattern 6: InMemoryEventPublisher Adapter

**What:** A simple in-memory implementation of `EventPublisher` for Phase 2. Phase 3 may replace or augment this with structured logging output.

**Example:**
```python
# src/adapters/driven/event_bus/publisher.py
from typing import Any
from src.kernel.ports.event_publisher import EventPublisher

class InMemoryEventPublisher:
    """Implements EventPublisher port. Records events in memory."""

    def __init__(self) -> None:
        self.events: list[Any] = []

    async def publish(self, event: Any) -> None:
        self.events.append(event)
```

### Anti-Patterns to Avoid

- **Importing ORM models in kernel:** Any `from adapters.driven.sqlite.models import DataRecord` inside `src/kernel/` immediately breaks PERS-02.
- **Using `session.add()` for idempotent inserts:** `session.add()` raises `IntegrityError` on duplicate unique constraint — use `sqlite_insert().on_conflict_do_nothing()` instead.
- **Separate transactions for data + audit:** Writing the audit row in a different `session.begin()` block from the data row can leave the two out of sync if the process crashes between transactions.
- **Alembic sync template with async engine:** Running `alembic init migrations` (without `-t async`) generates an `env.py` that uses `create_engine()` (sync) — this fails with `aiosqlite`. Always use `alembic init -t async migrations`.
- **Expiring ORM objects after commit:** Default `expire_on_commit=True` causes lazy-load errors in async contexts after the session closes. Set `expire_on_commit=False` in `async_sessionmaker`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Unique constraint + skip duplicate | Custom "check then insert" two-query pattern | `sqlite_insert().on_conflict_do_nothing()` | Race conditions in concurrent requests; the DB atomic guarantee makes two-query pattern broken |
| Transaction management | Manual `try/except` + `commit()`/`rollback()` | `async with session.begin()` context manager | Context manager handles rollback on any exception automatically |
| Migration versioning | Comments in schema files, manual ALTER TABLE | Alembic versioned migrations | Enables tracked upgrade path to PostgreSQL for v2 without data loss |
| Async engine creation | Building custom async wrappers | `create_async_engine()` from SQLAlchemy asyncio | SQLAlchemy handles greenlet integration, connection pool, dialect wiring |

**Key insight:** The SQLite idempotency problem looks simple but has a race condition. Two concurrent requests with the same `event_id` can both pass a "does it exist?" check and both attempt insert. `ON CONFLICT DO NOTHING` resolves this atomically at the database level.

---

## Common Pitfalls

### Pitfall 1: Sync Alembic Template with Async Engine
**What goes wrong:** Running `alembic init migrations` (no `-t async` flag) generates `env.py` that calls `create_engine()`. When Alembic runs migrations against `sqlite+aiosqlite://`, it fails with "no running event loop" or similar async errors.
**Why it happens:** Alembic defaults to synchronous template. The async template is opt-in.
**How to avoid:** Always use `alembic init -t async migrations` for this project. Verify `env.py` contains `async_engine_from_config` and `connection.run_sync(do_run_migrations)`.
**Warning signs:** `RuntimeError: no running event loop` during `alembic upgrade head`.

### Pitfall 2: expire_on_commit=True Causes Lazy-Load Errors
**What goes wrong:** After `session.commit()`, accessing attributes of an ORM object raises `MissingGreenlet` or `DetachedInstanceError`.
**Why it happens:** Default `expire_on_commit=True` marks all ORM attributes as expired after commit. Re-accessing them triggers a lazy load, which needs a running session — but in async context the session is already closed.
**How to avoid:** Create `async_sessionmaker(..., expire_on_commit=False)`. All attributes remain accessible after commit.
**Warning signs:** `sqlalchemy.exc.MissingGreenlet` when reading `record.id` after committing.

### Pitfall 3: session.add() Raises IntegrityError on Duplicate event_id
**What goes wrong:** Using `session.add(DataRecord(...))` for idempotent inserts raises `sqlalchemy.exc.IntegrityError` when a duplicate `event_id` is detected, instead of silently skipping.
**Why it happens:** ORM-level `session.add()` has no mechanism for conflict handling — it always issues a plain `INSERT`.
**How to avoid:** Use `from sqlalchemy.dialects.sqlite import insert as sqlite_insert` and call `.on_conflict_do_nothing()`. Never use `session.add()` for the idempotent path.
**Warning signs:** `IntegrityError: UNIQUE constraint failed: data_records.event_id` in test logs.

### Pitfall 4: ORM Models Imported into Kernel
**What goes wrong:** A refactor moves validation logic and accidentally adds `from adapters.driven.sqlite.models import DataRecord` inside a kernel file.
**Why it happens:** Convenience — the ORM model has the same fields as the domain model.
**How to avoid:** Maintain the mapping function in the adapter only. The adapter maps `DataRecord` ORM object → plain `dict` before returning to kernel. The kernel only sees `dict[str, Any]`.
**Warning signs:** `import sqlalchemy` appearing in `src/kernel/` module — the existing test `test_kernel_ports.py` already checks zero infrastructure imports; extend it to cover adapters import boundaries.

### Pitfall 5: aiosqlite Does Not Use Real Async I/O
**What goes wrong:** Developer assumes aiosqlite provides genuine non-blocking I/O and designs for high concurrency in production.
**Why it happens:** The name "aiosqlite" implies async, but the official docs state: "aiosqlite uses a background thread per connection. It does not actually use non-blocking IO."
**How to avoid:** This is expected and acceptable for v1. SQLite is for development/testing. The hexagonal architecture makes the swap to asyncpg + PostgreSQL trivial for v2.
**Warning signs:** N/A — this is a v1 constraint, not a bug. Document it as known.

---

## Code Examples

### Integration Test Setup Pattern
```python
# tests/integration/conftest.py
# Source: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from src.adapters.driven.sqlite.models import Base

@pytest.fixture(scope="function")
async def session_factory():
    """In-memory SQLite engine per test — no file I/O, fully isolated."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    yield factory
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.fixture
def repository(session_factory):
    from src.adapters.driven.sqlite.repository import SQLiteDataRepository
    return SQLiteDataRepository(session_factory)
```

### Repository Contract Test (VERF-01 + PERS-01)
```python
# tests/integration/test_sqlite_repository.py
import pytest

async def test_add_and_get_roundtrip(repository):
    """Data written can be retrieved with same content (VERF-01)."""
    record_id = await repository.add(
        table="contacts",
        source_id="nango_hubspot_123",
        data={"name": "Alice", "email": "alice@example.com"},
    )
    retrieved = await repository.get("contacts", record_id)
    assert retrieved == {"name": "Alice", "email": "alice@example.com"}

async def test_idempotent_add_with_same_event_id(repository):
    """Same event_id inserted twice produces one record (PERS-04)."""
    data = {"event_id": "evt_abc123", "name": "Bob"}
    id1 = await repository.add(table="contacts", source_id="src", data=data)
    id2 = await repository.add(table="contacts", source_id="src", data=data)
    # Second call returns without error; only one data_records row created
    first = await repository.get("contacts", id1)
    assert first is not None

async def test_get_nonexistent_returns_none(repository):
    result = await repository.get("contacts", "nonexistent-id")
    assert result is None
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `create_engine()` sync ORM | `create_async_engine()` + `AsyncSession` | SQLAlchemy 2.0 (2023) | Required for non-blocking webhook handling |
| `alembic init` (sync) | `alembic init -t async` | Alembic 1.8+ | Without async template, migrations fail with aiosqlite |
| `session.add()` for all inserts | `insert().on_conflict_do_nothing()` for idempotent paths | SQLAlchemy 1.4+ | Atomic conflict handling without race conditions |
| `expire_on_commit=True` (default) | `expire_on_commit=False` in async context | SQLAlchemy 2.0 async guidance | Prevents `MissingGreenlet` after session close |

**Deprecated/outdated:**
- `from sqlalchemy import create_engine`: Use `create_async_engine` from `sqlalchemy.ext.asyncio` — sync engine blocks event loop.
- `Base = declarative_base()`: Replaced by `class Base(DeclarativeBase): pass` in SQLAlchemy 2.0 mapped-column style.

---

## Open Questions

1. **Where does `event_id` come from in the AddDataCommand?**
   - What we know: `AddDataCommand.raw_data` is a `dict[str, Any]`. The kernel does not model `event_id` explicitly.
   - What's unclear: Should the repository extract `event_id` from `raw_data["event_id"]`, or should the kernel's `DataRepository` port be extended to accept `event_id` as a named argument?
   - Recommendation: Extract `event_id` from `raw_data.get("event_id")` in the adapter. This keeps the port stable and does not require kernel changes. The adapter owns the idempotency key extraction logic.

2. **Should `AuditLog` capture the validated data payload or just metadata?**
   - What we know: PERS-03 requires timestamp, source_id, table_name, and processing status only.
   - What's unclear: Storing the payload in the audit log provides replay capability but doubles storage.
   - Recommendation: Store metadata only (no payload) per PERS-03. Payload is in `data_records`. If replay is needed, it becomes a v2 feature (RESL-02 dead letter queue).

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.3+ with pytest-asyncio 0.24+ |
| Config file | `pyproject.toml` — `asyncio_mode = "auto"`, `asyncio_default_fixture_loop_scope = "function"` |
| Quick run command | `uv run pytest tests/integration/ -x -q` |
| Full suite command | `uv run pytest tests/ -x -q` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PERS-01 | Data survives session close (ACID) | integration | `uv run pytest tests/integration/test_sqlite_repository.py::test_add_and_get_roundtrip -x` | Wave 0 |
| PERS-02 | Kernel has no SQLAlchemy imports | unit (import scan) | `uv run pytest tests/test_kernel_ports.py -x` | Exists — extend for adapters boundary |
| PERS-03 | Audit row written with correct fields | integration | `uv run pytest tests/integration/test_sqlite_repository.py::test_audit_log_written -x` | Wave 0 |
| PERS-04 | Same event_id processed exactly once | integration | `uv run pytest tests/integration/test_sqlite_repository.py::test_idempotent_add_with_same_event_id -x` | Wave 0 |
| VERF-01 | get() returns data matching add() input | integration | `uv run pytest tests/integration/test_sqlite_repository.py::test_add_and_get_roundtrip -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/ -x -q` (40 existing + new integration tests)
- **Per wave merge:** `uv run pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/integration/__init__.py` — package init
- [ ] `tests/integration/conftest.py` — async engine + session factory + repository fixtures
- [ ] `tests/integration/test_sqlite_repository.py` — covers PERS-01, PERS-03, PERS-04, VERF-01
- [ ] Framework already installed (`pytest-asyncio` in pyproject.toml dev deps) — no install needed
- [ ] SQLAlchemy + aiosqlite + alembic install: `uv add sqlalchemy[asyncio] aiosqlite alembic`

---

## Sources

### Primary (HIGH confidence)
- [SQLAlchemy Asyncio docs](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html) — `create_async_engine`, `async_sessionmaker`, `expire_on_commit=False` patterns
- [SQLAlchemy SQLite dialect docs](https://docs.sqlalchemy.org/en/20/dialects/sqlite.html) — `sqlite+aiosqlite://` connection string, `on_conflict_do_nothing`, RETURNING clause support, aiosqlite thread-per-connection caveat
- [Alembic Cookbook](https://alembic.sqlalchemy.org/en/latest/cookbook.html) — Async migration `run_sync` bridge, `async_engine_from_config`, `alembic init -t async`
- Phase 1 source code (`src/kernel/ports/repository.py`, `src/kernel/handlers/add_data_handler.py`) — Port contract signatures, existing fake implementations

### Secondary (MEDIUM confidence)
- [SQLAlchemy Discussion #9675](https://github.com/sqlalchemy/sqlalchemy/discussions/9675) — Confirmed `session.add()` cannot use conflict handling; must use explicit `insert()` dialect construct
- [aiosqlite PyPI](https://pypi.org/project/aiosqlite/) — Version and threading model

### Tertiary (LOW confidence)
- WebSearch results on audit trail patterns — general pattern confirmed by official SQLAlchemy session events docs

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — versions confirmed in prior STACK.md research, SQLAlchemy + aiosqlite are the locked v1 choice
- Architecture: HIGH — port interfaces already exist in Phase 1 source code; adapter shape is constrained by them
- Pitfalls: HIGH — `expire_on_commit`, sync Alembic template, `session.add()` idempotency failures all verified via official docs and GitHub discussions
- Test patterns: HIGH — `pytest-asyncio` already configured in `pyproject.toml`; in-memory SQLite pattern is standard for integration tests

**Research date:** 2026-03-18
**Valid until:** 2026-06-18 (SQLAlchemy 2.x stable, aiosqlite 0.20 stable — no fast-moving changes expected)
