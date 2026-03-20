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

---
---

# Architecture Research — v0.3 Addendum: Dagster Salesforce Pipeline Integration

**Domain:** Dagster pipeline alongside existing Python hexagonal service
**Researched:** 2026-03-20
**Confidence:** HIGH

---

## Context: What Already Exists (v0.2.0)

The data-hub service is fully operational with hexagonal architecture, PostgreSQL backend, webhook ingestion, and Salesforce Nango syncs. v0.3 adds a **Dagster-based pull pipeline** — a new process that runs alongside the existing FastAPI service without modifying it.

**Existing structure (inspected directly):**

```
data-hub/
├── src/
│   ├── kernel/               # Pure Python, no external deps
│   ├── adapters/
│   │   ├── driven/
│   │   │   ├── nango/client.py         # NangoClient — async httpx
│   │   │   ├── postgresql/repository.py # PostgresDataRepository — asyncpg
│   │   │   └── repository_factory.py   # URL-scheme factory
│   │   └── driving/fastapi/            # FastAPI app
│   └── config/settings.py              # Pydantic Settings (DATABASE_URL, NANGO_SECRET_KEY)
├── nango-integrations/                 # TypeScript Nango syncs (v0.2.0)
├── pyproject.toml                      # asyncpg, psycopg2-binary already present
└── docker-compose.yml
```

**Key existing dependency:** `psycopg2-binary` is already in `pyproject.toml`. Dagster's synchronous PostgreSQL resource can use it immediately without adding a new dependency.

---

## System Overview — v0.3 Target State

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         data-hub repository                             │
│                                                                         │
│  ┌──────────────────────────┐     ┌────────────────────────────────┐    │
│  │     FastAPI Service       │     │      Dagster Pipeline          │    │
│  │   (existing, unchanged)   │     │   (new — separate process)     │    │
│  │                          │     │                                │    │
│  │  POST /webhooks/nango    │     │  dagster/                      │    │
│  │  POST /query/{model}     │     │  ├── definitions.py            │    │
│  │  GET  /health            │     │  ├── assets/                   │    │
│  │  GET  /metrics           │     │  │   ├── opportunity.py        │    │
│  │                          │     │  │   ├── opp_history.py        │    │
│  │  src/kernel/             │     │  │   ├── task.py               │    │
│  │  src/adapters/           │     │  │   └── event.py              │    │
│  │  src/config/             │     │  └── resources/                │    │
│  └──────────┬───────────────┘     │      ├── nango.py              │    │
│             │                     │      └── postgres.py           │    │
│             │ asyncpg (async)     └────────────┬───────────────────┘    │
│             │                                  │ psycopg2 (sync)        │
│  ┌──────────▼──────────────────────────────────▼───────────────────┐    │
│  │                        PostgreSQL                                 │    │
│  │        data_records table  |  audit_log table                    │    │
│  └──────────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  Nango (external)                                                  │  │
│  │  Webhook push  →  FastAPI /webhooks/nango  (existing path)        │  │
│  │  Records API   →  Dagster NangoResource    (new pull path)        │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

**Critical insight:** Dagster runs as a **separate OS process**. It never shares in-memory objects with FastAPI. Both processes connect to the same PostgreSQL database but use different drivers: FastAPI uses `asyncpg` (async), Dagster uses `psycopg2` (sync). This is correct and intentional.

---

## Recommended Project Structure

```
data-hub/
├── src/                              # Existing FastAPI service — NO CHANGES
│   ├── kernel/
│   ├── adapters/
│   │   ├── driven/
│   │   │   ├── nango/client.py       # Reused by NangoResource (safe cross-boundary import)
│   │   │   └── postgresql/
│   │   └── driving/fastapi/
│   └── config/settings.py            # Reused by Dagster resources for default values
│
├── dagster/                          # NEW — Dagster pipeline (separate entry point)
│   ├── __init__.py
│   ├── definitions.py                # Dagster entry point: Definitions(assets, resources)
│   ├── assets/
│   │   ├── __init__.py
│   │   ├── opportunity.py            # @asset — Opportunity full refresh
│   │   ├── opp_history.py            # @asset — OpportunityHistory full refresh
│   │   ├── task.py                   # @asset — Task full refresh
│   │   └── event.py                  # @asset — Event full refresh
│   └── resources/
│       ├── __init__.py
│       ├── nango.py                  # NangoResource(ConfigurableResource)
│       └── postgres.py               # PostgresResource(ConfigurableResource)
│
├── workspace.yaml                    # NEW — dagster dev entrypoint (local only)
├── dagster.yaml                      # NEW — Dagster instance config (run storage, etc.)
├── pyproject.toml                    # ADD dagster, dagster-webserver dependencies
└── tests/
    ├── (existing tests — untouched)
    └── dagster/                      # NEW — Dagster-specific tests
        ├── test_assets.py
        └── test_resources.py
```

### Structure Rationale

- **`dagster/` at project root, not inside `src/`:** Dagster is a separate process and deployment unit, not a FastAPI adapter. Placing it at root makes the process boundary explicit. The existing hexagonal `src/` layout is not violated.
- **`dagster/resources/` separate from `src/adapters/`:** Dagster resources follow the `ConfigurableResource` contract, not the kernel's `Protocol` contract. They are Dagster-specific adapters, not data-hub kernel adapters. Keeping them separate prevents confusion about which abstraction layer they belong to.
- **Reuse `src/config/settings.py`:** Safe to import from Dagster resources. `settings.py` depends only on `pydantic-settings` — no kernel, no FastAPI, no asyncpg. Avoids duplicating `NANGO_BASE_URL` and similar defaults.
- **Reuse `src/adapters/driven/nango/client.py`:** `NangoResource` delegates to the existing `NangoClient` for actual HTTP calls. The resource is a Dagster lifecycle wrapper; the client is the HTTP logic. This avoids reimplementing pagination and auth headers.
- **`workspace.yaml` at project root:** `dagster dev` looks for `workspace.yaml` in the current working directory. Placing it at root means `dagster dev` can be run from the project root alongside `uvicorn`.

---

## Architectural Patterns

### Pattern 1: ConfigurableResource Wrapping Existing Client

**What:** Dagster `ConfigurableResource` subclasses wrap existing Python clients rather than reimplementing them. The resource manages Dagster lifecycle; the wrapped client handles the actual logic.

**When to use:** When an existing HTTP or infrastructure client has already been built and tested. The `NangoClient` is a complete, tested async HTTP client — wrapping it is preferable to rewriting it.

**Trade-offs:** Thin resource, minimal duplication. The existing client stays independently testable. The resource is just a factory with config.

**Example:**
```python
# dagster/resources/nango.py
import dagster as dg
from src.adapters.driven.nango.client import NangoClient
from src.config.settings import settings

class NangoResource(dg.ConfigurableResource):
    base_url: str = settings.nango_base_url
    secret_key: str = dg.EnvVar("NANGO_SECRET_KEY")
    connection_id: str = dg.EnvVar("NANGO_CONNECTION_ID")

    def client(self) -> NangoClient:
        return NangoClient(base_url=self.base_url, secret_key=self.secret_key)
```

### Pattern 2: Synchronous psycopg2 Resource for Dagster Assets

**What:** Use synchronous `psycopg2` for Dagster's PostgreSQL resource. Dagster `@asset` functions are synchronous — there is no async context. The existing FastAPI service continues to use `asyncpg` via its own separate connection pool. Both use the same `DATABASE_URL` but different drivers.

**When to use:** All Dagster assets that write to PostgreSQL. `psycopg2-binary` is already in `pyproject.toml`.

**Trade-offs:** Two connection paths to the same database. This is correct — separate OS processes cannot share Python objects or event loops. Attempting to use `asyncpg` from a sync Dagster asset would require `asyncio.run()` wrapping every DB call, which is error-prone and adds overhead.

**Example:**
```python
# dagster/resources/postgres.py
import dagster as dg
import psycopg2
from contextlib import contextmanager
from pydantic import PrivateAttr

class PostgresResource(dg.ConfigurableResource):
    database_url: str = dg.EnvVar("DATABASE_URL")
    _conn: object = PrivateAttr()

    @contextmanager
    def yield_for_execution(self, context):
        # Strip asyncpg driver suffix for psycopg2 compatibility
        url = self.database_url.replace("postgresql+asyncpg://", "postgresql://")
        self._conn = psycopg2.connect(url)
        try:
            yield self
        finally:
            self._conn.close()

    def execute(self, sql: str, params: tuple = ()) -> list[dict]:
        with self._conn.cursor() as cur:
            cur.execute(sql, params)
            self._conn.commit()
            return []
```

### Pattern 3: Full Refresh Asset with Idempotent Upsert

**What:** Each Dagster asset pulls all records from Nango (all pages), then bulk-upserts into `data_records` using `INSERT ... ON CONFLICT (event_id) DO UPDATE SET data = EXCLUDED.data`. This overwrites stale data on re-run, matching the intent of a full refresh.

**When to use:** All four Salesforce model assets in v0.3. Incremental loads are explicitly deferred.

**Trade-offs:** Simple and correct for current data volumes. Re-fetches all records on every run. Acceptable until incremental strategy is needed (tracked as out-of-scope in PROJECT.md).

**Contrast with webhook path:** The webhook `add()` path uses `ON CONFLICT DO NOTHING` — it preserves first-seen data and is append-only. Dagster uses `DO UPDATE` — it intentionally overwrites with the latest Salesforce state. Both use `event_id` as the idempotency key.

### Pattern 4: asyncio.run() for Async Client Calls in Sync Assets

**What:** Call `asyncio.run(client.fetch_all_records(...))` inside a synchronous `@asset` function to bridge the async `NangoClient` into the sync Dagster execution model.

**When to use:** Any Dagster asset that calls the async `NangoClient`. This is the standard Python pattern for calling async code from sync context.

**Trade-offs:** Creates a new event loop per asset invocation. Acceptable for batch pipeline assets that run infrequently. Not suitable for high-frequency ops. Alternative: rewrite `NangoClient.fetch_all_records()` as a sync function using `httpx.Client` (sync) — this is cleaner but requires duplicating the pagination logic.

**Recommended decision:** Use `asyncio.run()` in v0.3 to minimize changes. If performance becomes a concern, add a sync `NangoClient` variant later.

### Pattern 5: Environment-Based Resource Configuration

**What:** `definitions.py` selects the resource configuration based on `DAGSTER_DEPLOYMENT` env var. Use `dg.EnvVar()` for all secrets — never hardcode values.

**When to use:** In `definitions.py` to wire the correct resource implementations per environment, preventing local dev from accidentally writing to production data.

**Example:**
```python
# dagster/definitions.py
import os
import dagster as dg
from dagster.assets import opportunity, opp_history, task, event
from dagster.resources.nango import NangoResource
from dagster.resources.postgres import PostgresResource

deployment = os.getenv("DAGSTER_DEPLOYMENT", "local")

resources_by_env = {
    "local": {
        "nango": NangoResource(
            secret_key=dg.EnvVar("NANGO_SECRET_KEY"),
            connection_id=dg.EnvVar("NANGO_CONNECTION_ID"),
        ),
        "postgres": PostgresResource(database_url=dg.EnvVar("DATABASE_URL")),
    },
    "production": {
        "nango": NangoResource(
            secret_key=dg.EnvVar("NANGO_SECRET_KEY"),
            connection_id=dg.EnvVar("NANGO_CONNECTION_ID"),
        ),
        "postgres": PostgresResource(database_url=dg.EnvVar("DATABASE_URL")),
    },
}

defs = dg.Definitions(
    assets=dg.load_assets_from_modules([opportunity, opp_history, task, event]),
    resources=resources_by_env[deployment],
)
```

---

## Data Flow

### Pull-Based Ingestion Flow (new in v0.3)

```
Dagster Scheduler or Manual Materialize trigger
    ↓
@asset salesforce_opportunities (or opp_history, task, event)
    ↓
NangoResource.client() → NangoClient instance
    ↓
asyncio.run(client.fetch_all_records(model="Opportunity", connection_id=...))
    ↓  (httpx paginates through /records API)
Nango Records API → list[dict] of all records
    ↓
PostgresResource._conn (psycopg2)
    ↓
INSERT INTO data_records (id, event_id, model_name, connection_id, data)
ON CONFLICT (event_id) DO UPDATE SET data = EXCLUDED.data
    ↓
dg.MaterializeResult(metadata={"record_count": len(records)})
```

### Push-Based Ingestion Flow (existing, v0.2 — unchanged)

```
Nango Webhook → POST /webhooks/nango
    ↓ (202 fast-ack, background task)
AddDataCommand → AddDataHandler → PostgresDataRepository.add()
    ↓ (asyncpg, ON CONFLICT DO NOTHING)
data_records + audit_log (same transaction)
```

### Shared Database Contract

Both flows write to `data_records`. The shared contract is:
- **Table:** `data_records` with columns `(id, event_id, model_name, connection_id, data, created_at)`
- **Idempotency key:** `event_id` (unique index)
- **Conflict behavior:** Dagster uses `DO UPDATE` (overwrites); webhook uses `DO NOTHING` (preserves first-seen)

This divergence is intentional. Dagster is a deliberate full refresh; webhooks are authoritative first-write events.

---

## Local Development Setup

```yaml
# workspace.yaml (at project root)
load_from:
  - python_module:
      module_name: dagster.definitions
```

```bash
# Terminal 1: FastAPI service (existing)
uvicorn src.adapters.driving.fastapi.app:app --reload --port 8000

# Terminal 2: Dagster UI + daemon (new)
dagster dev
# Dagster UI opens at http://localhost:3000
```

Environment variables needed locally (`.env` file, already read by `settings.py`):
- `DATABASE_URL=postgresql+asyncpg://...` — both processes use this
- `NANGO_SECRET_KEY=...` — Dagster NangoResource
- `NANGO_CONNECTION_ID=...` — Dagster assets
- `DAGSTER_DEPLOYMENT=local` — selects local resource config

---

## Dagster Cloud Deployment

```yaml
# dagster_cloud.yaml
locations:
  - location_name: data-hub
    code_source:
      python_module: dagster.definitions
    build:
      directory: .
```

Environment variables needed in Dagster Cloud:
- `DATABASE_URL` — production PostgreSQL URL (without `+asyncpg` suffix for psycopg2)
- `NANGO_SECRET_KEY` — Nango API auth
- `NANGO_CONNECTION_ID` — Salesforce connection ID(s)
- `DAGSTER_DEPLOYMENT=production`

---

## New vs Modified Component Inventory

| Component | Status | Notes |
|-----------|--------|-------|
| `dagster/definitions.py` | NEW | Dagster entry point — Definitions(assets, resources) |
| `dagster/assets/opportunity.py` | NEW | @asset for Salesforce Opportunity full refresh |
| `dagster/assets/opp_history.py` | NEW | @asset for OpportunityHistory full refresh |
| `dagster/assets/task.py` | NEW | @asset for Task full refresh |
| `dagster/assets/event.py` | NEW | @asset for Event full refresh |
| `dagster/resources/nango.py` | NEW | ConfigurableResource wrapping NangoClient |
| `dagster/resources/postgres.py` | NEW | ConfigurableResource using psycopg2 |
| `workspace.yaml` | NEW | `dagster dev` entrypoint for local dev |
| `dagster.yaml` | NEW | Dagster instance config (run storage backend) |
| `pyproject.toml` | MODIFIED | Add `dagster`, `dagster-webserver` dependencies |
| `src/` (entire FastAPI service) | NO CHANGE | Completely isolated from Dagster |
| `nango-integrations/` (TypeScript) | NO CHANGE | Nango syncs push data; Dagster pulls it |

---

## Build Order

Build order is driven by dependency graph. Each step unblocks the next.

```
Step 1: Add dagster + dagster-webserver to pyproject.toml
    Unblocks: everything else

Step 2: Create workspace.yaml + dagster/definitions.py (empty skeleton)
    Validates: dagster dev starts without error before any assets exist

Step 3: Create dagster/resources/postgres.py (PostgresResource)
    Prerequisite for: all assets that write to database

Step 4: Create dagster/resources/nango.py (NangoResource)
    Prerequisite for: all assets that pull from Nango

Step 5: Create dagster/assets/opportunity.py
    First asset — establishes the full data flow pattern end to end
    Validates: Nango → psycopg2 → data_records pipeline works

Step 6: Create dagster/assets/opp_history.py, task.py, event.py
    Follows pattern from Step 5
    Can be parallelized once Step 5 is validated

Step 7: Wire all assets into definitions.py
    Final step — register assets in Definitions

Step 8: Add schedule or sensor to definitions.py (optional for v0.3)
    Deferred: manual materialization sufficient for MVP
```

Steps 3 and 4 can be developed in parallel after Step 1.
Steps 6a–6c (opp_history, task, event) can be developed in parallel after Step 5 validates the pattern.

---

## Anti-Patterns

### Anti-Pattern 1: Importing Kernel into Dagster Assets

**What people do:** Import `AddDataCommand` or `AddDataHandler` from `src/kernel/` in Dagster assets to reuse persistence logic.

**Why it's wrong:** The kernel's `DataRepository` port is async (asyncpg). Dagster assets are sync. Bridging this requires `asyncio.run()` inside the handler, breaking the kernel's async design. More importantly, Dagster assets are the source of truth for pull-based ingestion — they should write data directly, not route through the webhook ingestion path.

**Do this instead:** Dagster assets write directly to PostgreSQL via `PostgresResource`. The `data_records` table schema is the integration contract, not the Python kernel classes.

### Anti-Pattern 2: Sharing the asyncpg Engine Across Processes

**What people do:** Instantiate one SQLAlchemy async engine and attempt to share it between FastAPI and Dagster.

**Why it's wrong:** Python objects cannot be shared across OS process boundaries. Each process needs its own connection pool. FastAPI's `asyncpg` engine lives in the FastAPI process; Dagster's `psycopg2` connection lives in the Dagster process.

**Do this instead:** Same `DATABASE_URL` env var, different drivers and connection pools in each process.

### Anti-Pattern 3: Embedding Dagster Inside FastAPI

**What people do:** Mount the Dagster webserver as an ASGI sub-application inside FastAPI, or launch `dagster dev` as a subprocess from the FastAPI lifespan.

**Why it's wrong:** Dagster has its own daemon, scheduler, and webserver. Embedding it creates port conflicts, lifecycle coupling, and breaks Dagster Cloud deployment which expects a standalone code location entry point.

**Do this instead:** Run `dagster dev` in a separate terminal (local) or as a separate container/process (production).

### Anti-Pattern 4: Hardcoding connection_id in Asset Body

**What people do:** Write `connection_id = "salesforce-prod"` directly in the asset function body.

**Why it's wrong:** Different environments (local, staging, production) and different customers have different `connection_id` values. Hardcoded values make assets non-portable.

**Do this instead:** Pass `connection_id` via `dg.EnvVar("NANGO_CONNECTION_ID")` on the resource, so the env var controls which Salesforce org Dagster pulls from.

---

## Sources

- [Dagster project structure overview](https://docs.dagster.io/guides/build/projects/project-structure/project-overview) — HIGH confidence (official docs)
- [Transitioning from development to production](https://docs.dagster.io/guides/operate/dev-to-prod) — HIGH confidence (official docs)
- [Defining resources](https://docs.dagster.io/guides/build/external-resources/defining-resources) — HIGH confidence (official docs)
- [Managing resource state / yield_for_execution](https://docs.dagster.io/guides/build/external-resources/managing-resource-state) — HIGH confidence (official docs)
- [workspace.yaml reference](https://docs.dagster.io/deployment/code-locations/workspace-yaml) — HIGH confidence (official docs)
- [Multiple code locations — monorepo](https://github.com/dagster-io/dagster/discussions/31890) — MEDIUM confidence (community discussion)
- [Connecting to APIs](https://docs.dagster.io/guides/build/external-resources/connecting-to-apis) — HIGH confidence (official docs)
- Existing codebase: `src/adapters/driven/nango/client.py`, `src/adapters/driven/postgresql/repository.py`, `src/config/settings.py`, `pyproject.toml` — HIGH confidence (inspected directly)

---
*Architecture research for: data-hub v0.3 — Dagster Salesforce Pipeline*
*Researched: 2026-03-20*
