# Architecture Research

**Domain:** Hexagonal Python service — PostgreSQL adapter, configurable backends, query port
**Researched:** 2026-03-19
**Confidence:** HIGH (existing codebase inspected directly; patterns verified against SQLAlchemy 2.0 official docs)

---

## Context: What Already Exists (v1.0)

This is a subsequent-milestone document. The base architecture is established and working. The question is how three new capabilities integrate without violating existing hexagonal boundaries.

**Existing structure inspected:**

```
src/
├── kernel/
│   ├── commands/add_data.py         # AddDataCommand dataclass
│   ├── handlers/add_data_handler.py # Orchestrates validate → persist → emit
│   ├── ports/
│   │   ├── repository.py            # DataRepository Protocol (add, get only)
│   │   ├── event_publisher.py       # EventPublisher Protocol
│   │   └── schema_registry.py       # SchemaRegistry Protocol
│   ├── domain/models.py             # RecordMetadata, CorrelationContext
│   └── exceptions.py
├── adapters/
│   ├── driven/
│   │   ├── sqlite/                  # SQLiteDataRepository (add, get)
│   │   ├── event_bus/               # InMemoryEventPublisher
│   │   └── schema_registry/         # PermissiveSchemaRegistry
│   └── driving/
│       └── fastapi/
│           ├── app.py               # lifespan: create_async_engine(settings.database_url)
│           ├── dependencies.py      # get_add_data_handler — hardcoded SQLiteDataRepository
│           └── routes/webhook.py    # POST /webhooks/nango
└── config/settings.py               # Pydantic Settings — database_url already present
```

**Key observation:** `settings.database_url` already exists and `app.py` already calls `create_async_engine(settings.database_url)`. The engine is URL-agnostic. The only gap is that `dependencies.py` hardcodes `SQLiteDataRepository`, bypassing the hexagonal seam.

---

## Standard Architecture

### System Overview — v2.0 Target State

```
┌──────────────────────────────────────────────────────────────────────────┐
│  DRIVING ADAPTERS (FastAPI)                                               │
│  ┌──────────────────────────┐   ┌──────────────────────────────────────┐  │
│  │  POST /webhooks/nango    │   │  GET  /query  (NEW)                  │  │
│  └────────────┬─────────────┘   └──────────────┬───────────────────────┘  │
│               │ AddDataCommand                  │ QueryDataCommand (NEW)   │
├───────────────┼─────────────────────────────────┼──────────────────────────┤
│  KERNEL                                                                    │
│  ┌────────────▼─────────────┐   ┌──────────────▼───────────────────────┐  │
│  │  AddDataHandler          │   │  QueryDataHandler (NEW)              │  │
│  └────────────┬─────────────┘   └──────────────┬───────────────────────┘  │
│               │                                │                          │
│  ┌────────────▼────────────────────────────────▼───────────────────────┐  │
│  │               DataRepository Protocol  (EXTENDED)                   │  │
│  │     add(model, connection_id, data) → str                           │  │
│  │     get(model, record_id) → dict | None                             │  │
│  │     query(sql, params) → list[dict]  (NEW METHOD)                   │  │
│  └─────────────────────────────────┬───────────────────────────────────┘  │
│                                    │ port boundary                        │
├────────────────────────────────────┼────────────────────────────────────  ┤
│  DRIVEN ADAPTERS                                                           │
│  ┌───────────────────┐  ┌──────────────────────┐  ┌────────────────────┐  │
│  │ SQLiteDataRepo    │  │ PostgresDataRepo (NEW)│  │ BackendFactory     │  │
│  │ (EXTENDED: +query)│  │ (full protocol impl.) │  │ (NEW)              │  │
│  └───────────────────┘  └──────────────────────┘  └────────────────────┘  │
│                                                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │  SQLAlchemy AsyncEngine                                              │  │
│  │  (sqlite+aiosqlite  OR  postgresql+asyncpg — selected by URL)       │  │
│  │  Created once at startup in app.py lifespan — NO CHANGE NEEDED      │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Status |
|-----------|----------------|--------|
| `DataRepository` Protocol | Persistence port contract | EXTEND — add `query()` method |
| `SQLiteDataRepository` | SQLite writes + reads | EXTEND — add `query()` method |
| `PostgresDataRepository` | PostgreSQL writes + reads | NEW |
| `BackendFactory` | Instantiate correct repo from `database_url` | NEW |
| `QueryDataCommand` | Command value object for SQL queries | NEW |
| `QueryDataHandler` | Kernel orchestrator for query operations | NEW |
| `dependencies.py` | FastAPI DI wiring | MODIFY — use factory, add query handler DI |
| `routes/query.py` | HTTP surface for QueryData | NEW |
| `app.py` lifespan | Engine creation | NO CHANGE |
| `settings.py` | Config | NO CHANGE |

---

## Recommended Project Structure (v2.0 delta)

Only the additions and modifications are highlighted:

```
src/
├── kernel/
│   ├── commands/
│   │   ├── add_data.py              # unchanged
│   │   └── query_data.py            # NEW: QueryDataCommand dataclass
│   ├── handlers/
│   │   ├── add_data_handler.py      # unchanged
│   │   └── query_data_handler.py    # NEW: QueryDataHandler
│   └── ports/
│       └── repository.py            # EXTEND: add query() to Protocol
│
├── adapters/
│   ├── driven/
│   │   ├── sqlite/
│   │   │   └── repository.py        # EXTEND: add query() method
│   │   ├── postgres/                # NEW directory
│   │   │   ├── __init__.py
│   │   │   └── repository.py        # NEW: PostgresDataRepository
│   │   └── factory.py               # NEW: create_repository(url, session_factory)
│   └── driving/
│       └── fastapi/
│           ├── dependencies.py      # MODIFY: use factory, add get_query_handler
│           └── routes/
│               └── query.py         # NEW: GET /query endpoint
│
tests/
└── unit/
    └── fakes.py                     # MODIFY: add query() to FakeDataRepository
```

### Structure Rationale

- **`adapters/driven/postgres/`**: Mirrors `adapters/driven/sqlite/` in layout. Parallel structure communicates symmetry and makes future adapters obvious to add.
- **`adapters/driven/factory.py`**: Single file where URL string becomes concrete repository. Keeps `dependencies.py` and `app.py` adapter-agnostic.
- **`kernel/commands/query_data.py`**: SQL + params travel as plain Python types. Kernel never imports SQLAlchemy. The command is the boundary where SQL crosses into the kernel as data, not behavior.
- **`routes/query.py`**: Matches the existing pattern (`webhook.py`, `health.py`, `metrics.py`) — one file per route concern.

---

## Architectural Patterns

### Pattern 1: Extend the Protocol, Not Replace It

**What:** Add `query()` as a third method on the existing `DataRepository` Protocol. Both `SQLiteDataRepository` and `PostgresDataRepository` implement the full protocol including `query()`.

**When to use:** When all backends must support the same operations. New method is required, not optional.

**Trade-offs:** Every existing adapter (including `FakeDataRepository` in tests) must be updated. This is the correct cost — it surfaces the contract change immediately at the port boundary rather than silently at runtime.

**Example:**
```python
# kernel/ports/repository.py — EXTENDED
@runtime_checkable
class DataRepository(Protocol):
    async def add(self, model: str, connection_id: str, data: dict[str, Any]) -> str: ...
    async def get(self, model: str, record_id: str) -> dict[str, Any] | None: ...
    async def query(self, sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]: ...
```

### Pattern 2: Backend Factory at the Adapter Boundary

**What:** A factory function in `adapters/driven/factory.py` inspects `database_url` and returns the appropriate concrete repository. It is the only code that knows both adapters exist. The factory receives the already-created `session_factory` from `app.state`.

**When to use:** Backend is selected at startup via configuration, not per-request. SQLAlchemy's `create_async_engine` already accepts any URL — the factory only adds the repository class selection on top.

**Trade-offs:** Simple and explicit. A factory class or abstract factory is overkill for two backends and one selection criterion (URL prefix). Keep it as a plain function.

**Example:**
```python
# adapters/driven/factory.py
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from src.kernel.ports.repository import DataRepository

def create_repository(
    database_url: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> DataRepository:
    if database_url.startswith("postgresql"):
        from .postgres.repository import PostgresDataRepository
        return PostgresDataRepository(session_factory)
    from .sqlite.repository import SQLiteDataRepository
    return SQLiteDataRepository(session_factory)
```

The import is inside the function body to keep it lazy and avoid circular imports at module load time.

### Pattern 3: Dialect-Specific INSERT for Idempotency

**What:** SQLite uses `sqlalchemy.dialects.sqlite.insert` with `.on_conflict_do_nothing()`. PostgreSQL uses `sqlalchemy.dialects.postgresql.insert` with `.on_conflict_do_nothing()`. These are separate dialect-specific constructs — there is no shared Core insert that supports the `ON CONFLICT` clause.

**When to use:** Required because the existing `SQLiteDataRepository.add()` already imports `from sqlalchemy.dialects.sqlite import insert as sqlite_insert`. The PostgreSQL adapter must import `from sqlalchemy.dialects.postgresql import insert as pg_insert`.

**Trade-offs:** The idempotency insert path is duplicated (once per adapter). This is correct — adapters are allowed to be similar; the kernel is not allowed to know about dialects. The duplication is contained and transparent.

**Example:**
```python
# adapters/driven/postgres/repository.py
from sqlalchemy.dialects.postgresql import insert as pg_insert

stmt = (
    pg_insert(DataRecord)
    .values(id=record_id, event_id=event_id, model_name=model, ...)
    .on_conflict_do_nothing(index_elements=["event_id"])
)
result = await session.execute(stmt)
status = "added" if result.rowcount > 0 else "duplicate"
```

### Pattern 4: Parameterized SQL in QueryDataCommand

**What:** `QueryDataCommand` carries `sql: str` and `params: dict` as plain Python types. The kernel handler passes them straight to `repository.query()`. The adapter executes them using SQLAlchemy `text()` with bound parameters.

**When to use:** The feature requirement is explicitly SQL-based (PROJECT.md: "SQL-based interface"). This avoids inventing an ORM abstraction layer for queries when the requirement is raw SQL access.

**Trade-offs:** SQL strings in commands means the caller controls query content. This is acceptable for an internal endpoint. The `params` dict with `text()` bindparams prevents SQL injection — never use string interpolation.

**Example:**
```python
# kernel/commands/query_data.py
@dataclass
class QueryDataCommand:
    sql: str
    params: dict[str, Any] = field(default_factory=dict)
    correlation: CorrelationContext = field(default_factory=CorrelationContext)

# adapters/driven/postgres/repository.py (query method)
from sqlalchemy import text

async def query(self, sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    async with self._session_factory() as session:
        result = await session.execute(text(sql), params or {})
        return [dict(row._mapping) for row in result]
```

---

## Data Flow

### Write Flow (existing, DI wiring changes)

```
POST /webhooks/nango
    → verify_nango_signature (dependency — unchanged)
    → get_add_data_handler (dependency — MODIFIED: uses factory)
        → factory.create_repository(settings.database_url, session_factory)
        → AddDataHandler(repository, event_publisher, schema_registry)
    → background_task: AddDataCommand → handler.handle()
        → validate → repository.add() → event_publisher.publish()
```

### Query Flow (new end-to-end)

```
GET /query?sql=SELECT...&params=...
    → get_query_handler (new dependency)
        → factory.create_repository(settings.database_url, session_factory)
        → QueryDataHandler(repository)
    → QueryDataCommand(sql, params)
    → handler.handle(command)
        → repository.query(sql, params) → list[dict]
    → JSON response: {"results": [...]}
```

### Backend Selection at Startup

```
ENV DATABASE_URL="postgresql+asyncpg://..."
    → settings.database_url
    → app.py lifespan: create_async_engine(settings.database_url)
                       async_sessionmaker(engine) → app.state.session_factory

Per-request dependency injection:
    request.app.state.session_factory
        → factory.create_repository(settings.database_url, session_factory)
        → PostgresDataRepository  (or SQLiteDataRepository for sqlite:// URLs)
```

The engine is created once at startup. `create_repository` is called per request — it is cheap (instantiates a class with the already-created session factory, no I/O).

---

## Integration Points

### New vs Modified: Explicit Inventory

| Component | New or Modified | What Changes |
|-----------|----------------|--------------|
| `kernel/ports/repository.py` | MODIFIED | Add `query(sql, params) → list[dict]` to Protocol |
| `kernel/commands/query_data.py` | NEW | `QueryDataCommand` dataclass |
| `kernel/handlers/query_data_handler.py` | NEW | `QueryDataHandler` — calls `repository.query()` |
| `adapters/driven/factory.py` | NEW | `create_repository(url, session_factory)` |
| `adapters/driven/postgres/` | NEW | `PostgresDataRepository` implementing full protocol |
| `adapters/driven/sqlite/repository.py` | MODIFIED | Add `query()` method using `text()` |
| `adapters/driving/fastapi/dependencies.py` | MODIFIED | Use factory; add `get_query_handler` dependency |
| `adapters/driving/fastapi/routes/query.py` | NEW | `GET /query` endpoint |
| `adapters/driving/fastapi/app.py` | NO CHANGE | Already `create_async_engine(settings.database_url)` |
| `config/settings.py` | NO CHANGE | `database_url` already present and ENV-driven |
| `migrations/env.py` | NO CHANGE | ORM model definitions are dialect-agnostic |
| `tests/unit/fakes.py` | MODIFIED | Add `query()` to `FakeDataRepository` |

### External Dependencies

| Dependency | Change | Notes |
|------------|--------|-------|
| `asyncpg` | ADD to `pyproject.toml` | `postgresql+asyncpg://` URL triggers the asyncpg dialect |
| `aiosqlite` | KEEP | Existing SQLite tests depend on it |
| `sqlalchemy[asyncio]` | NO VERSION CHANGE | 2.0 already installed; supports both dialects natively |

### Internal Boundaries

| Boundary | Communication | Constraint |
|----------|---------------|------------|
| Kernel ↔ Repository | Protocol only | `kernel/ports/repository.py` is the sole coupling point |
| Kernel ↔ Query Command | Plain dataclass | No SQLAlchemy types anywhere in `src/kernel/` |
| FastAPI ↔ Kernel | Handler instances in `dependencies.py` | Handlers receive protocols, not adapters |
| Factory ↔ Adapters | Import inside function body | Lazy import prevents circular deps at module load |

---

## Alembic Migration

`migrations/env.py` imports `from src.adapters.driven.sqlite.models import Base`. The ORM models (`DataRecord`, `AuditLog`) are dialect-agnostic — SQLAlchemy ORM model definitions use standard column types that map correctly to both SQLite and PostgreSQL.

**Recommended approach:** `PostgresDataRepository` reuses the same `models.py` from the SQLite adapter unchanged. A new Alembic migration version is needed only to ensure the schema is applied to PostgreSQL — the table definitions do not change.

If `models.py` needs to move to a shared location (e.g., `adapters/driven/models.py`), that is a valid refactor but not required for the feature to work. The factory pattern does not require it.

---

## Build Order

Dependencies drive the order. Each step is a prerequisite for the next.

```
Step 1: Extend DataRepository Protocol — add query()
    Unblocks: all consumers of the protocol

Step 2: Add query() to SQLiteDataRepository
    Unblocks: SQLite integration tests for query path

Step 3: Add query() to FakeDataRepository (tests/unit/fakes.py)
    Unblocks: kernel unit tests for QueryDataHandler

Step 4: Create QueryDataCommand + QueryDataHandler (kernel)
    Can start in parallel with Step 2 after Step 1
    Unblocks: handler unit tests and route implementation

Step 5: Create PostgresDataRepository adapter
    Can run in parallel with Step 4 after Step 1
    Requires: Step 1 (protocol with query method)

Step 6: Create BackendFactory (adapters/driven/factory.py)
    Requires: Steps 2 and 5 (both adapters complete)

Step 7: Modify dependencies.py — use factory, add get_query_handler
    Requires: Steps 4 (handler) and 6 (factory)

Step 8: Create GET /query route
    Requires: Step 7 (dependency wired)

Step 9: Update app.py configure_routes() to include query router
    Requires: Step 8 (route module exists)
```

Steps 4 and 5 can be developed in parallel after Step 1 completes.

---

## Anti-Patterns

### Anti-Pattern 1: Conditional Dialect Logic Inside a Repository

**What people do:** Put `if "postgresql" in self._url:` checks inside `SQLiteDataRepository.add()` instead of creating a separate PostgreSQL adapter.

**Why it's wrong:** Defeats the hexagonal model. The adapter becomes two adapters pretending to be one. Testing is combinatorial. The port boundary becomes theater.

**Do this instead:** One class per backend. The factory selects the right one at DI time.

### Anti-Pattern 2: Importing SQLAlchemy Dialect Types in the Kernel

**What people do:** Import `from sqlalchemy.dialects.postgresql import insert` anywhere inside `src/kernel/`.

**Why it's wrong:** Breaks kernel purity. Fails the testable-in-isolation constraint. The kernel becomes coupled to a specific database library version.

**Do this instead:** SQL execution lives entirely in adapters. The kernel command carries `sql: str` and `params: dict` — plain Python. The adapter calls `session.execute(text(command.sql), command.params)`.

### Anti-Pattern 3: Singleton Repository Created at Module Level in dependencies.py

**What people do:** `_repository = create_repository(settings.database_url, ...)` at module import time (similar to how `_event_publisher = InMemoryEventPublisher()` exists today).

**Why it's wrong:** The session factory comes from `app.state`, which only exists after the FastAPI lifespan runs. Module-level initialization runs at import time — before startup.

**Do this instead:** Create the repository inside the dependency function by passing `request.app.state.session_factory`. This is exactly the pattern `get_add_data_handler` uses today.

### Anti-Pattern 4: Skipping query() on FakeDataRepository

**What people do:** Leave `FakeDataRepository` without `query()` and write only integration tests for the query path.

**Why it's wrong:** `QueryDataHandler` unit tests need a fake repository. Without `query()` on the fake, handler tests require a real database, breaking the unit/integration test boundary the project already enforces.

**Do this instead:** Add `query()` to `FakeDataRepository` — store executed SQL calls in a list, return configurable results. Follow the existing `add_calls` pattern already in the class.

---

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| Current (webhook ingest + query) | Single engine per process, per-request session — correct as-is |
| High write volume | Configure `pool_size` and `max_overflow` on `create_async_engine` in `app.py` |
| High read volume (query endpoint) | Add read replica: second engine + second factory path; port boundary makes this a localized adapter change |
| Query complexity growth | If query needs grow beyond raw SQL pass-through, introduce a `QueryRepository` port separate from `DataRepository` |

---

## Sources

- SQLAlchemy 2.0 async documentation: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
- SQLAlchemy PostgreSQL dialect (ON CONFLICT): https://docs.sqlalchemy.org/en/20/dialects/postgresql.html
- SQLAlchemy SQLite dialect (ON CONFLICT): https://docs.sqlalchemy.org/en/20/dialects/sqlite.html
- Existing codebase: `src/kernel/ports/repository.py`, `src/adapters/driven/sqlite/repository.py`, `src/adapters/driving/fastapi/dependencies.py`, `src/adapters/driving/fastapi/app.py`, `src/config/settings.py` (all inspected directly — HIGH confidence)

---
*Architecture research for: data-hub v2.0 — PostgreSQL adapter, configurable backends, QueryData*
*Researched: 2026-03-19*
