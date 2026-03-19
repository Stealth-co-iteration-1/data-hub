# Architecture

**Analysis Date:** 2026-03-18

## Pattern Overview

**Overall:** Hexagonal Architecture (Ports & Adapters) with Clean Architecture principles

**Key Characteristics:**
- **Kernel-centric**: Pure business logic isolated from infrastructure concerns
- **Dependency inversion**: Kernel depends on ports (abstractions), adapters implement ports
- **Async-first**: All I/O operations are async (FastAPI, SQLAlchemy async)
- **Event-driven**: Domain events emitted after state changes for loose coupling
- **Fast-ack pattern**: Webhook handler acknowledges immediately (202), processes in background

## Layers

**Kernel (Core Business Logic):**
- Purpose: Pure Python business logic with zero external infrastructure dependencies
- Location: `src/kernel/`
- Contains: Commands, domain models, handlers, validators, events, ports, exceptions
- Depends on: Python standard library only (dataclasses, typing, uuid, datetime)
- Used by: All adapters inject kernel handlers and dependencies

**Driving Adapters (Entry Points):**
- Purpose: Handle inbound requests and transform them into kernel commands
- Location: `src/adapters/driving/fastapi/`
- Contains: FastAPI app configuration, HTTP routes, request/response schemas, middleware, dependencies
- Depends on: Kernel (commands, handlers, models, exceptions), FastAPI, Starlette
- Used by: External HTTP clients (Nango webhook service)

**Driven Adapters (Output/Infrastructure):**
- Purpose: Implement kernel ports using specific technologies
- Location: `src/adapters/driven/`
- Contains:
  - SQLite repository: `src/adapters/driven/sqlite/` - persistent data storage via SQLAlchemy ORM
  - In-memory event publisher: `src/adapters/driven/event_bus/` - domain event publication
  - Permissive schema registry: `src/adapters/driven/schema_registry/` - schema lookup for validation
- Depends on: Kernel (ports), SQLAlchemy, Pydantic
- Used by: Kernel handlers inject these implementations

**Configuration:**
- Purpose: Application settings and environment configuration
- Location: `src/config/settings.py`
- Contains: Pydantic-based settings with `.env` file support
- Key settings: `nango_webhook_secret`, `database_url`, `env` (development/staging/production), `log_level`

**Observability:**
- Purpose: Logging and metrics collection
- Location: `src/observability/`
- Contains: Structured logging via structlog with JSON output, Prometheus metrics
- Depends on: structlog, prometheus_client

## Data Flow

**Webhook Ingestion (Happy Path):**

1. **HTTP Request**: Nango sends POST to `/webhooks/nango` with webhook payload
2. **Signature Verification** (dependency): `verify_nango_signature()` validates HMAC-SHA256 signature, raises HTTPException 401 on failure
3. **Fast Ack** (route): Handler immediately returns 202 Accepted with `WebhookResponse(status="accepted")`
4. **Background Processing**: FastAPI BackgroundTasks schedules `_process_sync_webhook()` to run after response sent
5. **Command Creation**: Background task builds `AddDataCommand` from webhook payload with correlation context
6. **Handler Execution**: `AddDataHandler.handle(command)` orchestrates:
   - **Validation**: `SchemaValidator.validate_or_raise()` looks up schema from registry, validates data using Pydantic
   - **Persistence**: `SQLiteDataRepository.add()` writes data to SQLite in transaction with audit log
   - **Event Publishing**: `InMemoryEventPublisher.publish(DataAddedEvent)` stores event
7. **Logging**: Each step logs with correlation ID, automatically propagated via structlog contextvars
8. **Metrics**: Prometheus counters incremented for webhooks received, records added, validation failures, processing latency

**Error Handling:**

- **Validation Failure**: `ValidationError` caught in `_process_sync_webhook()`, logged with field paths and error count
- **Schema Not Found**: `SchemaNotFoundError` caught, logged with schema name
- **Unexpected Errors**: `Exception` caught, logged with full stack trace
- **Non-sync Webhooks**: Logged at INFO level, ignored (auth, forward types), never processed

**State Management:**

- **Per-Request Context**: Correlation ID generated or extracted from header, bound to structlog contextvars via `CorrelationIdMiddleware`
- **Background Task Context**: Correlation ID explicitly re-bound in background task since it runs outside request context
- **Transaction Semantics**: SQLAlchemy `async_sessionmaker` creates isolated sessions, `session.begin()` ensures atomic writes

## Key Abstractions

**Commands:**
- Purpose: Represent user intentions for state-changing operations
- Location: `src/kernel/commands/add_data.py`
- Pattern: Dataclass with required fields (table, source_id, schema_name, raw_data) and optional correlation context
- Example: `AddDataCommand(table="contact", source_id="nango_hubspot_123", schema_name="hubspot_contact", raw_data={...})`

**Events:**
- Purpose: Immutable records of state changes, emitted after persistence succeeds
- Location: `src/kernel/events/data_added.py`
- Pattern: Frozen dataclass with record metadata, correlation ID, and occurrence timestamp
- Used by: Future handlers can subscribe to events for downstream processing (Phase 3+)

**Ports (Abstract Interfaces):**
- `DataRepository` (`src/kernel/ports/repository.py`): Implemented by SQLiteDataRepository, provides `add()` and `get()`
- `EventPublisher` (`src/kernel/ports/event_publisher.py`): Implemented by InMemoryEventPublisher, provides `publish()`
- `SchemaRegistry` (`src/kernel/ports/schema_registry.py`): Implemented by PermissiveSchemaRegistry, provides `get_schema()`

**Domain Models:**
- `RecordMetadata`: Immutable value object with record_id, table, source_id, schema_name, created_at
- `CorrelationContext`: Immutable observability context with correlation_id, timestamp, optional source
- `ValidationResult`: Result of validation with is_valid, validated_data, errors

**Validators:**
- `SchemaValidator`: Uses Pydantic's `model_validate()` (compiled Rust, fast) for validation
- Converts Pydantic errors to kernel `FieldError` format (field_path, message, expected, actual)
- Location: `src/kernel/validators/schema_validator.py`

## Entry Points

**HTTP Endpoint:**
- Location: `src/adapters/driving/fastapi/routes/webhook.py` -> `nango_webhook()`
- Triggers: POST request to `/webhooks/nango` with Nango sync webhook payload
- Responsibilities: Verify signature, acknowledge immediately (202), schedule background processing

**Background Task:**
- Location: `src/adapters/driving/fastapi/routes/webhook.py` -> `_process_sync_webhook()`
- Triggers: Scheduled by FastAPI BackgroundTasks after 202 response
- Responsibilities: Validate data, persist to database, emit domain event, handle errors

**Application Startup:**
- Location: `src/adapters/driving/fastapi/app.py` -> `lifespan()` context manager
- Triggers: FastAPI app startup
- Responsibilities: Configure logging, create SQLAlchemy async engine, store in app.state for DI

## Error Handling

**Strategy:** Typed exception hierarchy + structured error information

**Patterns:**

1. **Domain Exceptions**: Kernel defines `KernelError` base with subclasses:
   - `ValidationError(schema_name, errors: list[FieldError])`: Structured validation failures
   - `SchemaNotFoundError(schema_name)`: Missing schema in registry
   - Each error includes context fields for debugging

2. **HTTP Error Handling**: Route handler catches kernel exceptions:
   - ValidationError/SchemaNotFoundError: Logged as warnings, does NOT propagate to HTTP (202 still returned)
   - Unexpected exceptions: Logged with stack trace via `logger.exception()`
   - HTTP 401: Only for signature verification failures (security-critical)

3. **Async Context**: Background task explicitly handles exceptions after request completes:
   - Clears previous contextvars and re-binds correlation_id
   - All exceptions caught and logged, preventing task crash

## Cross-Cutting Concerns

**Logging:** Structured JSON logging via structlog with contextvars
- Configuration: `src/observability/logging.py` -> `configure_logging()`
- Per-request: Correlation ID automatically included in all logs via `CorrelationIdMiddleware`
- Development: Pretty-printed console output with colors
- Production: JSON output for log aggregation
- Sensitive data: Full payloads logged in development only (env check)

**Validation:** Pydantic-based schema validation with extra fields allowed
- Location: `src/kernel/validators/schema_validator.py`
- Extra fields: Preserved in validated_data (permissive schema registry for v1)
- Error format: Field paths (e.g., 'contact.email'), messages, expected types, actual values
- Performance: Uses Pydantic's compiled Rust implementation, NOT custom field validators

**Authentication:** HMAC-SHA256 signature verification on webhook payloads
- Location: `src/adapters/driving/fastapi/dependencies.py` -> `verify_nango_signature()`
- Timing-safe comparison using `hmac.compare_digest()` to prevent timing attacks
- Secret stored in environment variable `nango_webhook_secret` (Pydantic Settings)
- Verification happens before JSON parsing (raw bytes used for HMAC)

**Observability (Metrics):** Prometheus counters and histograms
- Location: `src/observability/metrics.py`
- Tracked: `webhooks_received` (by type), `records_added`, `validation_failures` (by schema), `processing_latency`
- Increment locations: Route handler (webhook count) and background task (records, failures, latency)

---

*Architecture analysis: 2026-03-18*
