# Coding Conventions

**Analysis Date:** 2026-03-18

## Naming Patterns

**Files:**
- Module files: `snake_case.py` (e.g., `add_data_handler.py`, `schema_validator.py`)
- Package directories: `snake_case` (e.g., `src/kernel/`, `src/adapters/driven/`)
- Test files: `test_<module_name>.py` (e.g., `test_add_data_handler.py`, `test_schema_validator.py`)

**Functions:**
- Regular functions: `snake_case` (e.g., `validate_or_raise()`, `make_signature()`, `should_log_full_payload()`)
- Private functions: `_snake_case` prefix (e.g., `_utc_now()`, `_new_uuid()`, `_process_sync_webhook()`, `_convert_pydantic_errors()`)
- Async functions: `snake_case` with `async def` keyword (e.g., `async def handle()`, `async def dispatch()`)
- Static/class methods: `snake_case` with `@staticmethod` or `@classmethod` decorators

**Variables:**
- Instance variables: `_snake_case` prefix for private attributes (e.g., `self._repository`, `self._event_publisher`, `self._validator`)
- Local variables: `snake_case` (e.g., `correlation_id`, `validated_data`, `schema_name`)
- Constants: `UPPER_CASE` (e.g., `WEBHOOK_SECRET`, `max_keys`)
- Tuple unpacking: descriptive names (e.g., `table, source_id, data = self.repository.add_calls[0]`)

**Types:**
- Classes: `PascalCase` (e.g., `AddDataHandler`, `RecordMetadata`, `CorrelationContext`, `ValidationError`)
- Exceptions: `PascalCase` ending with `Error` or `Exception` (e.g., `ValidationError`, `SchemaNotFoundError`, `KernelError`)
- Protocols: `PascalCase` (e.g., `DataRepository`, `EventPublisher`, `SchemaRegistry`)
- Type aliases: `PascalCase` (e.g., when using `type` keyword)

## Code Style

**Formatting:**
- Line length: 100 characters (configured in `pyproject.toml` under `[tool.ruff]`)
- Indentation: 4 spaces (Python standard)
- Tool: `ruff` for formatting and linting (configured in `pyproject.toml`)

**Linting:**
- Tool: `ruff` with config in `pyproject.toml`
- Target Python version: 3.12
- No `.pylintrc` or `.flake8` - uses Ruff as single linter
- Type checking: `pyright` in strict mode (`typeCheckingMode = "strict"`)

**Docstring Style:**
- Google/NumPy style docstrings with descriptions and Args/Returns sections
- Required for: All public functions, classes, and methods
- Optional for: Internal helper functions (encouraged for clarity)
- Example format:
  ```python
  def validate_or_raise(self, schema_name: str, data: dict[str, Any]) -> dict[str, Any]:
      """Validate data and raise if invalid.

      Convenience method that raises KernelValidationError on failure.

      Args:
          schema_name: Logical schema name
          data: Raw data to validate

      Returns:
          Validated data dict on success

      Raises:
          SchemaNotFoundError: If schema not found
          ValidationError: If validation fails
      """
  ```

## Import Organization

**Order:**
1. Standard library imports (`from typing import`, `from dataclasses import`)
2. Third-party imports (`from pydantic import`, `from sqlalchemy import`, `from fastapi import`)
3. Local application imports (`from src.kernel.commands import`, `from ..ports.repository import`)

**Path Aliases:**
- Absolute imports from project root: `from src.kernel.commands import AddDataCommand`
- Relative imports within packages: `from ..ports.repository import DataRepository`
- Avoid circular imports: Layer structure enforces clear dependencies (kernel doesn't import from adapters)

**Import Examples:**
- `from typing import Any, Protocol, runtime_checkable` - Multiple standard library
- `from pydantic import BaseModel, ConfigDict` - Multiple from one package
- `from src.config.settings import settings` - Absolute import
- `from ..domain.models import RecordMetadata` - Relative import within layer

## Error Handling

**Patterns:**
- Kernel exceptions inherit from `KernelError` base class (defined in `src/kernel/exceptions.py`)
- Domain-specific exceptions: `ValidationError`, `SchemaNotFoundError`
- All exceptions contain structured data for programmatic handling
  - `ValidationError` includes: `schema_name` (str), `errors` (list[FieldError])
  - `SchemaNotFoundError` includes: `schema_name` (str)
- Route handlers catch exceptions and log with full context (see `webhook.py` exception handling)
- Validation errors in background tasks: Log warning with `schema_name`, `source_id`, `table`, `error_count`, `error_fields`
- Unexpected errors: Log exception with stack trace using `logger.exception()`

**Exception Usage:**
```python
try:
    await handler.handle(command)
except ValidationError as exc:
    # Handle validation failure
    validation_failures.labels(schema_name=exc.schema_name).inc()
    logger.warning("validation_failure", schema_name=exc.schema_name, ...)
except SchemaNotFoundError as exc:
    # Handle schema not found
    logger.warning("schema_not_found", schema_name=exc.schema_name, ...)
except Exception:
    # Unexpected error - always log with stack trace
    logger.exception("unexpected_error", ...)
```

## Logging

**Framework:** `structlog` with structured JSON logging

**Configuration:** `src/observability/logging.py`

**Patterns:**
- Get logger: `logger = get_logger(__name__)` (module-level, typically at top of file)
- Log level: Use appropriate level - `info()` for normal flow, `warning()` for failures, `exception()` for errors with traceback
- Structured logging: Always use kwargs for context fields
  ```python
  logger.info("webhook_received", webhook_type=webhook_type, connection_id=payload.get("connectionId"))
  logger.warning("validation_failure", schema_name=exc.schema_name, error_count=len(exc.errors))
  logger.exception("webhook_processing_error", source_id=command.source_id)
  ```
- Correlation IDs: Automatically bound to all logs via `structlog.contextvars` (middleware handles this)
- Development vs Production:
  - Development: Pretty console output with colors
  - Production: JSON output for log aggregation
  - Full payloads logged in development only: Use `should_log_full_payload()` check

**Log Entry Fields (auto-included):**
- `correlation_id` - From middleware via contextvars
- `timestamp` - ISO format
- `level` - Log level
- `message` - Log event name (first positional arg)
- Additional kwargs are appended as context fields

## Comments

**When to Comment:**
- Complex business logic or non-obvious algorithms
- Important design decisions or trade-offs (e.g., "Fast-ack: schedule background processing")
- Workarounds or temporary solutions
- Links to related issues or requirements (e.g., "per CONTEXT.md decisions", "OBSV-01")

**When NOT to Comment:**
- Self-documenting code (good naming makes comments redundant)
- Docstrings should suffice for public APIs
- Comments should not restate what code obviously does

**JSDoc/TSDoc:**
- Not applicable (Python project)
- Use docstrings with type hints instead
- Type hints are enforced via `pyright` strict mode

## Function Design

**Size:** Keep functions focused and concise
- Single responsibility principle: One function does one thing well
- Example: `_process_sync_webhook()` handles background processing orchestration
- Example: `_convert_pydantic_errors()` converts one error format to another

**Parameters:**
- Use explicit parameters (no *args/**kwargs unless necessary)
- Type hints required for all parameters and returns
- Optional parameters with defaults: `data: dict[str, Any] | None = None`
- Async functions clearly marked: `async def handle()`

**Return Values:**
- Always use explicit return types: `-> str`, `-> dict[str, Any]`, `-> None`
- Return only what's needed (avoid unnecessary wrapping)
- Use dataclasses for structured returns (e.g., `ValidationResult`, `RecordMetadata`)

**Example:**
```python
async def handle(self, command: AddDataCommand) -> DataAddedEvent:
    """Process an AddDataCommand.

    Validates data, persists it, and emits an event.

    Args:
        command: The command containing data to add

    Returns:
        DataAddedEvent with record metadata

    Raises:
        SchemaNotFoundError: If schema_name is not in the registry
        ValidationError: If data fails validation
    """
    # Step 1: Validate
    validated_data = self._validator.validate_or_raise(command.schema_name, command.raw_data)

    # Step 2: Persist
    record_id = await self._repository.add(table=command.table, source_id=command.source_id, data=validated_data)

    # Step 3: Create metadata and event
    # ...

    return event
```

## Module Design

**Exports:**
- All public classes and functions explicitly imported in `__init__.py` files
- Example `src/kernel/handlers/__init__.py`: `from .add_data_handler import AddDataHandler`
- Allows clean imports: `from src.kernel.handlers import AddDataHandler`

**Barrel Files:**
- Each package has `__init__.py` for explicit exports
- Private modules not exposed (e.g., `_convert_pydantic_errors()` stays internal)

**Module Organization:**
- Domain models and value objects: `src/kernel/domain/`
- Ports (interfaces): `src/kernel/ports/`
- Handlers (command orchestration): `src/kernel/handlers/`
- Adapters (infrastructure): `src/adapters/` (split into `driving/` and `driven/`)
- Configuration: `src/config/`
- Observability: `src/observability/`

---

*Convention analysis: 2026-03-18*
