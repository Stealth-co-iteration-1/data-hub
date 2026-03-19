# Architecture Research

**Domain:** Python data ingestion platform with hexagonal/clean architecture
**Researched:** 2026-03-18
**Confidence:** HIGH

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     DRIVING ADAPTERS                             │
│  (Primary/Input Adapters - External to Internal)                 │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │   FastAPI    │  │     CLI      │  │  Event Bus   │           │
│  │  Controller  │  │   Handler    │  │   Listener   │           │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘           │
│         │                 │                 │                    │
│         └─────────────────┴─────────────────┘                    │
│                           ↓                                      │
├─────────────────────────────────────────────────────────────────┤
│                      DRIVING PORTS                               │
│                   (Input Interfaces)                             │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────┐   │
│  │           Commands / Queries / Events                     │   │
│  │  (Abstract interfaces defined in kernel)                  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                           ↓                                      │
├─────────────────────────────────────────────────────────────────┤
│                      KERNEL (CORE)                               │
│                   (Pure Business Logic)                          │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  ┌──────────┐  ┌──────────┐  ┌────────────┐             │    │
│  │  │ Commands │  │ Queries  │  │   Events   │             │    │
│  │  │ Handlers │  │ Handlers │  │  Emitters  │             │    │
│  │  └─────┬────┘  └─────┬────┘  └─────┬──────┘             │    │
│  │        │              │             │                    │    │
│  │        └──────────────┴─────────────┘                    │    │
│  │                      ↓                                   │    │
│  │  ┌──────────────────────────────────────────────────┐   │    │
│  │  │          Domain Models & Logic                    │   │    │
│  │  │  (Entities, Value Objects, Domain Services)       │   │    │
│  │  └──────────────────────────────────────────────────┘   │    │
│  │                      ↓                                   │    │
│  │  ┌──────────────────────────────────────────────────┐   │    │
│  │  │    Schema Validators & Business Rules             │   │    │
│  │  └──────────────────────────────────────────────────┘   │    │
│  └─────────────────────────────────────────────────────────┘    │
│                           ↓                                      │
├─────────────────────────────────────────────────────────────────┤
│                      DRIVEN PORTS                                │
│                   (Output Interfaces)                            │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Repository Interfaces / Event Publisher Interfaces      │   │
│  │  (Abstract - defined in kernel, implemented by adapters) │   │
│  └──────────────────────────────────────────────────────────┘   │
│                           ↓                                      │
├─────────────────────────────────────────────────────────────────┤
│                     DRIVEN ADAPTERS                              │
│      (Secondary/Output Adapters - Internal to External)          │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │  PostgreSQL  │  │    Event     │  │    File      │           │
│  │  Repository  │  │  Publisher   │  │   Storage    │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
└─────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| **Driving Adapters** | Receive external requests, convert to kernel commands/queries | FastAPI routes, CLI commands, webhook handlers |
| **Driving Ports** | Define how external world triggers business logic | Command/Query interfaces, DTOs for input validation |
| **Kernel (Core)** | Pure business logic with no external dependencies | Command handlers, domain models, validation rules |
| **Driven Ports** | Define how kernel communicates with external systems | Repository interfaces, event publisher interfaces |
| **Driven Adapters** | Implement external system communication | SQLAlchemy repositories, message queue publishers |
| **Commands** | State-changing operations (write) | `AddDataCommand`, `DeleteDataCommand` |
| **Queries** | Data retrieval operations (read) | `GetDataQuery`, `VerifyDataQuery` |
| **Events** | Domain events emitted after state changes | `DataAddedEvent`, `ValidationFailedEvent` |

## Recommended Project Structure

```
data-hub/
├── src/
│   ├── kernel/                    # Pure business logic (no external deps)
│   │   ├── commands/              # State-changing operations
│   │   │   ├── __init__.py
│   │   │   ├── add_data.py        # AddDataCommand and handler
│   │   │   └── handlers.py        # Command handler registry
│   │   ├── queries/               # Data retrieval operations
│   │   │   ├── __init__.py
│   │   │   ├── verify_data.py     # VerifyDataQuery and handler
│   │   │   └── handlers.py        # Query handler registry
│   │   ├── events/                # Domain events
│   │   │   ├── __init__.py
│   │   │   └── data_added.py      # DataAddedEvent definition
│   │   ├── domain/                # Domain models and logic
│   │   │   ├── __init__.py
│   │   │   ├── models.py          # Domain entities/value objects
│   │   │   └── validators.py      # Schema validation logic
│   │   ├── ports/                 # Interfaces for adapters
│   │   │   ├── __init__.py
│   │   │   ├── repository.py      # Repository interface (driven port)
│   │   │   └── event_publisher.py # Event publisher interface (driven port)
│   │   └── exceptions.py          # Domain-specific exceptions
│   │
│   ├── adapters/                  # Implementations of ports
│   │   ├── driving/               # Input adapters (primary)
│   │   │   ├── __init__.py
│   │   │   ├── fastapi/           # FastAPI transport
│   │   │   │   ├── __init__.py
│   │   │   │   ├── app.py         # FastAPI app initialization
│   │   │   │   ├── routes.py      # Route definitions
│   │   │   │   ├── dependencies.py # FastAPI dependency injection
│   │   │   │   └── schemas.py     # Pydantic DTOs for API
│   │   │   └── cli/               # CLI transport (optional)
│   │   │       └── commands.py
│   │   │
│   │   └── driven/                # Output adapters (secondary)
│   │       ├── __init__.py
│   │       ├── postgresql/        # PostgreSQL adapter
│   │       │   ├── __init__.py
│   │       │   ├── repository.py  # Implementation of repository port
│   │       │   ├── models.py      # SQLAlchemy ORM models
│   │       │   └── session.py     # Database session management
│   │       └── event_bus/         # Event publishing adapter
│   │           ├── __init__.py
│   │           └── publisher.py   # Implementation of event publisher port
│   │
│   ├── config/                    # Configuration management
│   │   ├── __init__.py
│   │   └── settings.py            # Pydantic settings
│   │
│   └── main.py                    # Application entry point
│
├── tests/
│   ├── unit/                      # Unit tests for kernel (no dependencies)
│   │   ├── commands/
│   │   ├── queries/
│   │   └── domain/
│   ├── integration/               # Tests with adapters
│   │   ├── test_postgresql.py
│   │   └── test_api.py
│   └── e2e/                       # End-to-end tests
│       └── test_webhook_flow.py
│
├── migrations/                    # Database migrations (Alembic)
│   └── versions/
│
├── pyproject.toml                 # Project dependencies and config
├── requirements.txt               # Production dependencies
├── requirements-dev.txt           # Development dependencies
└── README.md
```

### Structure Rationale

- **kernel/:** Contains pure Python business logic with zero external dependencies. Can be tested without databases, web frameworks, or any infrastructure. This is the heart of hexagonal architecture.

- **adapters/driving/:** Primary adapters that receive external input (HTTP requests, CLI commands, events). They translate external formats into kernel commands/queries.

- **adapters/driven/:** Secondary adapters that implement external communication (database access, event publishing). They implement interfaces defined in kernel/ports/.

- **kernel/ports/:** Abstract interfaces (protocols or ABCs) that define contracts between kernel and adapters. Kernel depends on these abstractions, not concrete implementations.

- **kernel/commands/:** CQRS pattern - commands represent state-changing intentions. Each command has a handler that executes business logic.

- **kernel/queries/:** CQRS pattern - queries represent read operations. Separated from commands for clarity and potential optimization.

- **kernel/events/:** Domain events emitted after successful operations. Enable loose coupling between components (Command → Event → Command pattern).

## Architectural Patterns

### Pattern 1: Hexagonal Architecture (Ports & Adapters)

**What:** Separates core business logic (kernel) from external concerns (adapters) through abstract interfaces (ports). Dependencies flow from outside (adapters) to inside (kernel).

**When to use:** When you need testability, flexibility to swap implementations (e.g., different databases, web frameworks), and clean separation of business logic from infrastructure.

**Trade-offs:**
- **Pros:** High testability (kernel tests need no mocks), flexibility to change infrastructure, clear boundaries
- **Cons:** More initial boilerplate, can be overkill for simple CRUD apps

**Example:**
```python
# kernel/ports/repository.py (Driven Port - defined in kernel)
from abc import ABC, abstractmethod
from typing import Dict, Any

class DataRepository(ABC):
    """Repository interface defined in kernel - no implementation details."""

    @abstractmethod
    async def add(self, table: str, source_id: str, data: Dict[str, Any]) -> str:
        """Add data and return ID. Implementation decided by adapter."""
        pass

    @abstractmethod
    async def get(self, table: str, record_id: str) -> Dict[str, Any]:
        """Retrieve data by ID."""
        pass

# kernel/commands/add_data.py (Command and Handler in kernel)
from dataclasses import dataclass
from typing import Dict, Any
from kernel.ports.repository import DataRepository
from kernel.domain.validators import SchemaValidator
from kernel.events.data_added import DataAddedEvent

@dataclass
class AddDataCommand:
    """Command - represents user intention."""
    table: str
    source_id: str
    schema_hint: str
    raw_data: Dict[str, Any]

class AddDataHandler:
    """Handler - executes business logic using port abstractions."""

    def __init__(self, repository: DataRepository, validator: SchemaValidator):
        self.repository = repository  # Depends on port, not concrete implementation
        self.validator = validator

    async def handle(self, command: AddDataCommand) -> DataAddedEvent:
        # Business logic with validation
        validated_data = self.validator.validate(
            command.raw_data,
            command.schema_hint
        )

        # Use port abstraction - doesn't know it's PostgreSQL
        record_id = await self.repository.add(
            command.table,
            command.source_id,
            validated_data
        )

        # Return domain event
        return DataAddedEvent(
            table=command.table,
            record_id=record_id,
            source_id=command.source_id
        )

# adapters/driven/postgresql/repository.py (Driven Adapter - implements port)
from kernel.ports.repository import DataRepository
from sqlalchemy.ext.asyncio import AsyncSession

class PostgreSQLRepository(DataRepository):
    """Concrete implementation - knows about PostgreSQL, SQLAlchemy."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, table: str, source_id: str, data: Dict[str, Any]) -> str:
        # PostgreSQL-specific implementation
        # Maps domain data to ORM models, handles transactions, etc.
        pass

# adapters/driving/fastapi/routes.py (Driving Adapter - uses kernel)
from fastapi import APIRouter, Depends
from kernel.commands.add_data import AddDataCommand, AddDataHandler

router = APIRouter()

@router.post("/webhook/nango")
async def nango_webhook(
    payload: dict,
    handler: AddDataHandler = Depends(get_add_data_handler)
):
    """FastAPI adapter - translates HTTP to kernel command."""
    command = AddDataCommand(
        table=payload["table"],
        source_id=payload["source_id"],
        schema_hint=payload["schema_hint"],
        raw_data=payload["data"]
    )

    event = await handler.handle(command)
    return {"id": event.record_id, "status": "success"}
```

### Pattern 2: CQRS (Command Query Responsibility Segregation)

**What:** Separates write operations (commands) from read operations (queries). Commands change state and return events. Queries retrieve data without side effects.

**When to use:** When you want clear separation between read and write models, when commands and queries have different performance characteristics, or when building event-sourced systems.

**Trade-offs:**
- **Pros:** Clear intent (AddDataCommand vs GetDataQuery), separate optimization paths, natural event emission
- **Cons:** More classes than traditional service pattern, can feel like overkill for simple operations

**Example:**
```python
# kernel/commands/add_data.py
@dataclass
class AddDataCommand:
    """State-changing operation - write side."""
    table: str
    source_id: str
    raw_data: Dict[str, Any]

class AddDataHandler:
    async def handle(self, command: AddDataCommand) -> DataAddedEvent:
        # Changes state, returns event
        record_id = await self.repository.add(...)
        return DataAddedEvent(record_id=record_id)

# kernel/queries/verify_data.py
@dataclass
class VerifyDataQuery:
    """Read operation - read side."""
    table: str
    record_id: str

class VerifyDataHandler:
    async def handle(self, query: VerifyDataQuery) -> Dict[str, Any]:
        # No state changes, just reads
        return await self.repository.get(query.table, query.record_id)
```

### Pattern 3: Domain Events with Event-Driven Decoupling

**What:** After successful operations, emit domain events that other parts of the system can react to. Follows the pattern: Command → Event → (optional) Command. Prevents tight coupling between features.

**When to use:** When you need to trigger side effects after operations (notifications, logging, analytics), when building eventually consistent systems, or when features should be loosely coupled.

**Trade-offs:**
- **Pros:** Loose coupling, easy to add new reactions to events, supports eventual consistency
- **Cons:** Asynchronous complexity, harder to trace execution flow, eventual consistency can confuse users expecting immediate effects

**Example:**
```python
# kernel/events/data_added.py
from dataclasses import dataclass
from datetime import datetime

@dataclass
class DataAddedEvent:
    """Domain event - something happened in the system."""
    record_id: str
    table: str
    source_id: str
    timestamp: datetime = datetime.utcnow()

# kernel/ports/event_publisher.py
class EventPublisher(ABC):
    """Port for publishing events - adapter decides mechanism."""

    @abstractmethod
    async def publish(self, event: Any) -> None:
        pass

# kernel/commands/add_data.py (updated)
class AddDataHandler:
    def __init__(self, repository: DataRepository, event_publisher: EventPublisher):
        self.repository = repository
        self.event_publisher = event_publisher

    async def handle(self, command: AddDataCommand) -> DataAddedEvent:
        record_id = await self.repository.add(...)

        # Emit event - other handlers can react
        event = DataAddedEvent(record_id=record_id, table=command.table, ...)
        await self.event_publisher.publish(event)

        return event

# Example: Another handler reacts to the event
class NotifyOnDataAddedHandler:
    """Separate concern - reacts to DataAddedEvent."""

    async def handle(self, event: DataAddedEvent) -> None:
        # Send notification, log analytics, etc.
        # Original AddDataHandler doesn't know or care about this
        pass
```

### Pattern 4: Dependency Inversion with Dependency Injection

**What:** Kernel defines interfaces (ports) that adapters implement. Dependencies are injected at runtime, typically at the application entry point. Kernel never imports adapters.

**When to use:** Always in hexagonal architecture - it's the mechanism that enables the dependency rule (dependencies point inward).

**Trade-offs:**
- **Pros:** Testability (inject mocks/fakes), flexibility (swap implementations), enforces dependency rule
- **Cons:** Requires DI container or manual wiring, can be verbose in Python (no compile-time checking)

**Example:**
```python
# src/main.py (application entry point - wiring)
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from kernel.commands.add_data import AddDataHandler
from kernel.domain.validators import SchemaValidator
from adapters.driven.postgresql.repository import PostgreSQLRepository
from adapters.driven.event_bus.publisher import InMemoryEventPublisher
from adapters.driving.fastapi.routes import router

# Create concrete implementations (adapters)
engine = create_async_engine("postgresql+asyncpg://...")
session_factory = async_sessionmaker(engine, class_=AsyncSession)

def get_add_data_handler() -> AddDataHandler:
    """Dependency injection - wire kernel to adapters."""
    session = session_factory()
    repository = PostgreSQLRepository(session)  # Driven adapter
    event_publisher = InMemoryEventPublisher()  # Driven adapter
    validator = SchemaValidator()

    # Inject adapters into kernel handler
    return AddDataHandler(repository, event_publisher, validator)

# FastAPI app (driving adapter)
app = FastAPI()
app.include_router(router)
```

## Data Flow

### Request Flow (Webhook Ingestion)

```
External System (Nango)
    ↓ [HTTP POST /webhook/nango]
┌─────────────────────────────────────────────────────────────────┐
│ DRIVING ADAPTER: FastAPI Route                                  │
│  • Receives webhook payload                                     │
│  • Validates HTTP structure (Pydantic schema)                   │
│  • Converts to AddDataCommand                                   │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ KERNEL: AddDataHandler                                          │
│  • Validates data against schema (business rule)                │
│  • Executes business logic                                      │
│  • Calls repository.add() via port                              │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ DRIVEN ADAPTER: PostgreSQLRepository                            │
│  • Maps domain data to ORM models                               │
│  • Executes SQL INSERT                                          │
│  • Returns record ID                                            │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ KERNEL: AddDataHandler (continued)                              │
│  • Creates DataAddedEvent                                       │
│  • Publishes event via event_publisher.publish()                │
│  • Returns event to adapter                                     │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ DRIVEN ADAPTER: EventPublisher                                  │
│  • Notifies subscribers                                         │
│  • Triggers side effects (logging, analytics, etc.)             │
└─────────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ DRIVING ADAPTER: FastAPI Route (response)                       │
│  • Converts event to JSON response                              │
│  • Returns 200 OK with record ID                                │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
External System (Nango) receives success response
```

### Verification Flow (Query)

```
User/System Request
    ↓ [GET /data/{id} or VerifyDataQuery]
┌─────────────────────────────────────────────────────────────────┐
│ DRIVING ADAPTER: API/CLI                                        │
│  • Receives verification request                                │
│  • Creates VerifyDataQuery                                      │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ KERNEL: VerifyDataHandler                                       │
│  • Validates query parameters                                   │
│  • Calls repository.get() via port                              │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ DRIVEN ADAPTER: PostgreSQLRepository                            │
│  • Executes SQL SELECT                                          │
│  • Maps ORM models to domain data                               │
│  • Returns data or None                                         │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ KERNEL: VerifyDataHandler (continued)                           │
│  • Returns data (no event - read operation)                     │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ DRIVING ADAPTER: API/CLI (response)                             │
│  • Formats data for presentation                                │
│  • Returns to requester                                         │
└─────────────────────────────────────────────────────────────────┘
```

### Key Data Flows

1. **Webhook Ingestion (Write):** External webhook → FastAPI adapter → AddDataCommand → Kernel validation → Repository port → PostgreSQL adapter → DB write → DataAddedEvent → Event publisher → Response

2. **Data Verification (Read):** Request → API/CLI adapter → VerifyDataQuery → Kernel → Repository port → PostgreSQL adapter → DB read → Response (no event)

3. **Event Propagation:** Kernel emits event → Event publisher (driven adapter) → Subscribers → Potential new commands (async)

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| **0-10k requests/day** | Monolith is perfect. Single FastAPI app, single PostgreSQL instance. Focus on kernel purity and test coverage. No need for message queues or microservices. |
| **10k-1M requests/day** | Add connection pooling (pgbouncer), async I/O throughout (asyncio, asyncpg). Consider read replicas for queries. Event publisher can remain in-memory or switch to Redis Pub/Sub. Monitor database query performance - add indexes as needed. |
| **1M+ requests/day** | Separate command and query databases (CQRS separation). Commands write to primary DB, queries read from replicas. Event publisher becomes message queue (RabbitMQ, AWS SQS). Consider horizontal scaling of FastAPI workers (multiple containers). Database partitioning/sharding if single table grows > 100M rows. |

### Scaling Priorities

1. **First bottleneck: Database connections**
   - Symptoms: Connection pool exhaustion, slow response times
   - Solution: Add connection pooling (pgbouncer), increase pool size, use async drivers (asyncpg)
   - When: > 1000 concurrent connections

2. **Second bottleneck: Database query performance**
   - Symptoms: Slow SELECT queries, high CPU on database
   - Solution: Add indexes on foreign keys (source_id, table), implement read replicas for queries, consider materialized views for complex queries
   - When: Query response time > 100ms for simple lookups

3. **Third bottleneck: Webhook processing throughput**
   - Symptoms: Webhook timeouts, request queuing
   - Solution: Scale FastAPI horizontally (load balancer + multiple containers), implement async command processing (queue commands, process asynchronously), use background workers for non-critical operations
   - When: > 100 requests/second

## Anti-Patterns

### Anti-Pattern 1: Kernel Depending on Adapters

**What people do:** Import concrete adapter classes in kernel code (e.g., `from adapters.postgresql.repository import PostgreSQLRepository` in a command handler).

**Why it's wrong:** Violates the dependency rule - creates tight coupling, makes kernel untestable without database, defeats the purpose of hexagonal architecture.

**Do this instead:** Kernel imports only from `kernel/ports/`. Adapters implement those interfaces. Dependency injection wires concrete adapters to kernel at runtime.

```python
# WRONG - kernel importing adapter
from adapters.driven.postgresql.repository import PostgreSQLRepository

class AddDataHandler:
    def __init__(self):
        self.repository = PostgreSQLRepository()  # Tight coupling!

# RIGHT - kernel importing port
from kernel.ports.repository import DataRepository

class AddDataHandler:
    def __init__(self, repository: DataRepository):  # Depends on abstraction
        self.repository = repository
```

### Anti-Pattern 2: Fat Adapters with Business Logic

**What people do:** Put validation, business rules, or domain logic inside adapters (e.g., schema validation in FastAPI route, business rules in repository).

**Why it's wrong:** Business logic becomes scattered and untestable in isolation. Changing web frameworks or databases requires rewriting business logic.

**Do this instead:** Adapters are thin translation layers. All business logic lives in kernel. Adapters convert formats and delegate to kernel.

```python
# WRONG - business logic in adapter
@router.post("/webhook")
async def webhook(payload: dict, session: AsyncSession):
    # Validation in adapter
    if not payload.get("table"):
        raise ValueError("Missing table")

    # Business logic in adapter
    validated_data = validate_schema(payload["data"], payload["schema_hint"])

    # Direct database access
    session.add(DataModel(**validated_data))
    await session.commit()

# RIGHT - adapter delegates to kernel
@router.post("/webhook")
async def webhook(payload: dict, handler: AddDataHandler = Depends()):
    # Adapter just converts HTTP to command
    command = AddDataCommand(
        table=payload["table"],
        source_id=payload["source_id"],
        schema_hint=payload["schema_hint"],
        raw_data=payload["data"]
    )

    # Kernel handles business logic
    event = await handler.handle(command)
    return {"id": event.record_id}
```

### Anti-Pattern 3: Anemic Domain Models

**What people do:** Create domain models that are just data containers with getters/setters, putting all logic in handlers or services.

**Why it's wrong:** Misses opportunity for encapsulation and domain-driven design. Business rules become scattered across handlers instead of encapsulated in domain objects.

**Do this instead:** Rich domain models that encapsulate behavior and invariants. Let domain objects validate themselves and expose meaningful operations.

```python
# WRONG - anemic domain model
@dataclass
class DataRecord:
    table: str
    source_id: str
    data: Dict[str, Any]

# Validation logic scattered in handler
class AddDataHandler:
    def handle(self, command):
        if not command.table:
            raise ValueError("Table required")
        if not command.source_id:
            raise ValueError("Source ID required")
        # ... more validation

# RIGHT - rich domain model
class DataRecord:
    def __init__(self, table: str, source_id: str, raw_data: Dict[str, Any], schema_hint: str):
        self._validate_table(table)
        self._validate_source(source_id)
        self._table = table
        self._source_id = source_id
        self._data = self._validate_data(raw_data, schema_hint)

    def _validate_table(self, table: str) -> None:
        if not table or not table.isidentifier():
            raise ValueError(f"Invalid table name: {table}")

    def _validate_source(self, source_id: str) -> None:
        if not source_id:
            raise ValueError("Source ID required")

    def _validate_data(self, data: Dict[str, Any], schema_hint: str) -> Dict[str, Any]:
        # Schema validation logic encapsulated in domain model
        return validated_data

    @property
    def table(self) -> str:
        return self._table  # Immutable after validation
```

### Anti-Pattern 4: Using ORMs in Kernel

**What people do:** Use SQLAlchemy models or database-specific types directly in kernel code.

**Why it's wrong:** Creates dependency on ORM library in kernel, couples domain models to database schema, makes testing harder.

**Do this instead:** Use pure Python dataclasses or domain models in kernel. Map between domain models and ORM models in the adapter layer.

```python
# WRONG - SQLAlchemy in kernel
from sqlalchemy.orm import DeclarativeBase

class DataRecord(DeclarativeBase):  # Kernel depends on SQLAlchemy
    __tablename__ = "data_records"
    id = Column(Integer, primary_key=True)

# RIGHT - pure domain model in kernel
@dataclass
class DataRecord:
    id: str
    table: str
    source_id: str
    data: Dict[str, Any]

# Mapping happens in adapter
# adapters/driven/postgresql/repository.py
from sqlalchemy.orm import DeclarativeBase

class DataRecordORM(DeclarativeBase):
    __tablename__ = "data_records"
    id = Column(Integer, primary_key=True)

class PostgreSQLRepository(DataRepository):
    async def add(self, table: str, source_id: str, data: Dict[str, Any]) -> str:
        # Map domain to ORM
        orm_record = DataRecordORM(table=table, source_id=source_id, ...)
        self.session.add(orm_record)
        await self.session.commit()

        # Return domain type
        return str(orm_record.id)
```

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| **Nango (Webhooks)** | Driving adapter - FastAPI webhook endpoint receives POST requests | Validate webhook signature for security. Handle retries (Nango retries failed webhooks). Return 200 quickly - process async if needed. |
| **PostgreSQL** | Driven adapter - SQLAlchemy async with connection pooling | Use asyncpg driver for performance. Connection pool size: 10-20 for small apps, scale with workers. Handle connection errors gracefully. |
| **Event Bus (future)** | Driven adapter - implements EventPublisher port | Start with in-memory publisher for simplicity. Swap to Redis Pub/Sub or RabbitMQ when scaling. Keep port abstract - don't leak event bus details to kernel. |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| **Driving Adapter ↔ Kernel** | Direct function calls via Commands/Queries | Adapter creates command/query objects, calls handler.handle(). Synchronous or async depending on handler. FastAPI uses `await handler.handle()`. |
| **Kernel ↔ Driven Adapter** | Indirect via port interfaces | Kernel calls `repository.add()` (port method). Doesn't know if it's PostgreSQL, MongoDB, or in-memory. Dependency injection provides concrete adapter. |
| **Command Handler ↔ Event Publisher** | Handler emits events after success | After repository operation succeeds, handler creates event and publishes via port. Event publisher notifies subscribers (can be synchronous or async). |
| **Kernel ↔ Validation Logic** | Validation lives in kernel domain layer | Validators are pure functions or domain service classes. No I/O, just business rule checking. Raises domain exceptions on failure. |

## Build Order Recommendations

Based on hexagonal architecture dependency rules, build in this order:

### Phase 1: Kernel Foundation (Build First)
**Why first:** No dependencies, pure business logic, foundation for everything else

1. **Domain models** (`kernel/domain/models.py`) - Entities, value objects
2. **Port interfaces** (`kernel/ports/`) - Define contracts (DataRepository, EventPublisher)
3. **Domain validators** (`kernel/domain/validators.py`) - Schema validation logic
4. **Commands** (`kernel/commands/add_data.py`) - Command objects and handlers
5. **Events** (`kernel/events/data_added.py`) - Domain event definitions

**Testable immediately:** All kernel code can be unit tested with no mocks (just inject fake implementations of ports)

### Phase 2: Driven Adapters (Build Second)
**Why second:** Implements kernel ports, enables kernel to interact with external world

1. **PostgreSQL adapter** (`adapters/driven/postgresql/`) - Implements DataRepository port
   - ORM models (`models.py`)
   - Repository implementation (`repository.py`)
   - Session management (`session.py`)
2. **Event publisher adapter** (`adapters/driven/event_bus/`) - Implements EventPublisher port
   - Start with in-memory implementation for simplicity

**Testable:** Integration tests with real database (or test database)

### Phase 3: Driving Adapters (Build Last)
**Why last:** Depends on kernel being complete, translates external inputs to kernel commands

1. **FastAPI adapter** (`adapters/driving/fastapi/`) - Webhook endpoint
   - App initialization (`app.py`)
   - Routes (`routes.py`)
   - Dependency injection (`dependencies.py`)
   - Pydantic DTOs for API (`schemas.py`)

**Testable:** E2E tests with TestClient hitting actual endpoints

### Dependency Rationale

```
Phase 3: Driving Adapters (FastAPI)
    ↓ depends on
Phase 1: Kernel (Commands/Handlers)
    ↓ depends on (via ports)
Phase 2: Driven Adapters (PostgreSQL)
```

**Why this order works:**
- Kernel has zero dependencies → build and test first
- Driven adapters depend on kernel ports → build second to enable kernel I/O
- Driving adapters depend on kernel commands → build last to expose system

**Parallel opportunities:**
- Driven and driving adapters can be built in parallel once kernel is stable
- Multiple driven adapters (PostgreSQL, events) can be built concurrently
- Tests can be written alongside each phase

## Sources

**Hexagonal Architecture Foundations:**
- [Hexagonal Architecture Design: Python Ports and Adapters for Modularity 2026](https://johal.in/hexagonal-architecture-design-python-ports-and-adapters-for-modularity-2026/)
- [Hexagonal architecture in Python](https://blog.szymonmiks.pl/p/hexagonal-architecture-in-python/)
- [Hexagonal Architecture (Ports & Adapters) Practical Guide 2026](https://www.youngju.dev/blog/architecture/2026-03-03-hexagonal-architecture-guide.en)
- [AWS Prescriptive Guidance: Structure a Python project in hexagonal architecture](https://docs.aws.amazon.com/prescriptive-guidance/latest/patterns/structure-a-python-project-in-hexagonal-architecture-using-aws-lambda.html)

**Python Implementations:**
- [GitHub: hexagonal-architecture-python-spark (Data Engineering Example)](https://github.com/tcmlabs/hexagonal-architecture-python-spark)
- [GitHub: szymon6927/hexagonal-architecture-python](https://github.com/szymon6927/hexagonal-architecture-python)
- [GitHub: marcosvs98/hexagonal-architecture-with-python](https://github.com/marcosvs98/hexagonal-architecture-with-python)

**CQRS and Event Patterns:**
- [AWS: Building hexagonal architectures - CQRS recommendations](https://docs.aws.amazon.com/pdfs/prescriptive-guidance/latest/hexagonal-architectures/hexagonal-architectures.pdf)
- [Architecture Patterns with Python (O'Reilly Book)](https://www.oreilly.com/library/view/architecture-patterns-with/9781492052197/)

**Data Validation:**
- [How to Build a Data Validation Framework in Python 2026](https://oneuptime.com/blog/post/2026-01-25-data-validation-framework-python/view)
- [Pydantic Validation Layers 2025](https://johal.in/pydantic-validation-layers-secure-python-ml-input-sanitization-2025/)

**FastAPI + Hexagonal:**
- [Building Maintainable Python Applications with Hexagonal Architecture and DDD](https://dev.to/hieutran25/building-maintainable-python-applications-with-hexagonal-architecture-and-domain-driven-design-chp)
- [Hexagonal FastAPI by Moritz Althaus (January 2025)](https://moldhouse.de/posts/hexagonal-fastapi/)

**Clean Architecture Principles:**
- [GitHub: python-clean-architecture](https://github.com/pcah/python-clean-architecture)
- [Clean Architecture with Python](https://medium.com/@shaliamekh/clean-architecture-with-python-d62712fd8d4f)
- [Layered vs Hexagonal Architecture: Optimal Choice 2026](https://edana.ch/en/2026/02/16/layered-architecture-vs-hexagonal-architecture-choosing-between-immediate-simplicity-and-long-term-robustness/)

**Repository Pattern:**
- [A concrete example of the Hexagonal Architecture in Python (Data Engineering)](https://medium.com/towards-data-engineering/a-concrete-example-of-the-hexagonal-architecture-in-python-d821213c6fb9)

---
*Architecture research for: Python data ingestion platform with hexagonal/clean architecture*
*Researched: 2026-03-18*
