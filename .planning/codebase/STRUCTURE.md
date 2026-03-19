# Structure

> Directory layout, key file locations, and naming conventions for the data-hub codebase.

## Root Layout

```
data-hub/
├── .planning/             # GSD planning artifacts (not committed)
├── src/                   # Application source code
├── tests/                 # Test suite
├── alembic/               # Database migrations
├── pyproject.toml         # Project configuration
├── alembic.ini            # Alembic configuration
├── docker-compose.yml     # Local development services
└── .env.example           # Environment variable template
```

## Source Directory (`src/`)

```
src/
├── __init__.py
├── kernel/                # Pure business logic (no I/O)
│   ├── commands/          # Command DTOs (input)
│   ├── domain/            # Domain models
│   ├── events/            # Event DTOs (output)
│   ├── exceptions/        # Domain exceptions
│   ├── handlers/          # Command handlers
│   ├── ports/             # Port protocols (interfaces)
│   └── validators/        # Schema validation
├── adapters/
│   ├── driving/           # Inbound adapters (HTTP)
│   │   └── fastapi/       # FastAPI application
│   │       ├── app.py     # FastAPI application factory
│   │       ├── routes.py  # HTTP endpoints
│   │       └── middleware.py  # Request middleware
│   └── driven/            # Outbound adapters (I/O)
│       ├── sqlite/        # SQLite persistence
│       │   ├── models.py  # SQLAlchemy models
│       │   ├── repository.py  # DataRepository impl
│       │   └── session.py # Session management
│       ├── event_bus/     # Event publishing
│       │   └── publisher.py
│       └── schema_registry/  # Schema management
│           └── permissive.py
├── config/                # Application configuration
│   ├── settings.py        # Pydantic settings
│   └── container.py       # Dependency injection
└── observability/         # Cross-cutting observability
    ├── logging.py         # Structured logging setup
    └── metrics.py         # Prometheus metrics
```

## Test Directory (`tests/`)

```
tests/
├── integration/           # Tests with real adapters
│   ├── conftest.py        # Shared fixtures
│   ├── test_webhook_endpoint.py
│   ├── test_sqlite_repository.py
│   └── ...
├── kernel/                # Kernel domain tests
│   ├── commands/
│   ├── events/
│   └── test_schema_validator.py
├── unit/                  # Pure unit tests with fakes
│   ├── fakes.py           # Fake port implementations
│   ├── test_add_data_handler.py
│   └── ...
└── test_kernel_ports.py   # Port protocol tests
```

## Key File Locations

### Entry Points

| Purpose | File |
|---------|------|
| FastAPI application | `src/adapters/driving/fastapi/app.py` |
| HTTP routes | `src/adapters/driving/fastapi/routes.py` |
| Main webhook endpoint | `src/adapters/driving/fastapi/routes.py:webhook_handler` |

### Domain Logic

| Purpose | File |
|---------|------|
| AddDataCommand | `src/kernel/commands/add_data.py` |
| DataAddedEvent | `src/kernel/events/data_added.py` |
| AddDataHandler | `src/kernel/handlers/add_data_handler.py` |
| Domain models | `src/kernel/domain/models.py` |
| Domain exceptions | `src/kernel/exceptions/__init__.py` |

### Ports (Interfaces)

| Port | File |
|------|------|
| DataRepository | `src/kernel/ports/data_repository.py` |
| EventPublisher | `src/kernel/ports/event_publisher.py` |
| SchemaRegistry | `src/kernel/ports/schema_registry.py` |

### Adapters (Implementations)

| Adapter | File |
|---------|------|
| SQLiteDataRepository | `src/adapters/driven/sqlite/repository.py` |
| InMemoryEventPublisher | `src/adapters/driven/event_bus/publisher.py` |
| PermissiveSchemaRegistry | `src/adapters/driven/schema_registry/permissive.py` |

### Configuration

| Purpose | File |
|---------|------|
| App settings | `src/config/settings.py` |
| DI container | `src/config/container.py` |

### Observability

| Purpose | File |
|---------|------|
| Structured logging | `src/observability/logging.py` |
| Prometheus metrics | `src/observability/metrics.py` |

## Naming Conventions

### Files

- **Modules:** `snake_case.py`
- **Test files:** `test_{module}.py`
- **Package init:** `__init__.py` (re-exports public API)

### Directories

- **Packages:** `snake_case/`
- **Adapter organization:** `adapters/{driving|driven}/{technology}/`

### Code

- **Classes:** `PascalCase`
- **Functions:** `snake_case`
- **Constants:** `UPPER_SNAKE_CASE`
- **Private:** `_leading_underscore`

## Import Organization

Standard import order enforced by ruff:
1. Standard library
2. Third-party packages
3. Local application imports

Package `__init__.py` files re-export public API:
```python
# src/kernel/commands/__init__.py
from src.kernel.commands.add_data import AddDataCommand
__all__ = ["AddDataCommand"]
```
