# Testing

> Test framework, structure, mocking strategies, and coverage patterns for the data-hub codebase.

## Test Framework

**Primary:** pytest 8.3+ with pytest-asyncio 0.24+

**Key Dependencies:**
- `pytest` - Test runner and assertions
- `pytest-asyncio` - Async test support with `asyncio_mode = "auto"`
- `pytest-cov` - Coverage reporting
- `httpx` - HTTP client for integration tests (via TestClient)

**Configuration:** `pyproject.toml`
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
testpaths = ["tests"]
```

## Directory Structure

```
tests/
├── integration/           # Tests with real adapters
│   ├── conftest.py       # Shared fixtures (engine, session, repository)
│   ├── test_audit_log.py
│   ├── test_health.py
│   ├── test_logging.py
│   ├── test_metrics.py
│   ├── test_metrics_endpoint.py
│   ├── test_signature.py
│   ├── test_sqlite_repository.py
│   ├── test_verification.py
│   └── test_webhook_endpoint.py
├── kernel/                # Kernel domain tests
│   ├── commands/
│   │   └── test_add_data.py
│   ├── events/
│   │   └── test_data_added.py
│   └── test_schema_validator.py
├── unit/                  # Pure unit tests with fakes
│   ├── fakes.py          # Fake implementations of ports
│   ├── test_add_data_handler.py
│   ├── test_event_publisher.py
│   └── test_schema_validator.py
└── test_kernel_ports.py   # Port protocol compliance tests
```

## Test Naming Conventions

- **Files:** `test_{module}.py` or `test_{feature}.py`
- **Classes:** `TestClassName` for grouping related tests
- **Methods:** `test_{behavior}_when_{condition}` or `test_{action}_{expected_result}`

## Mocking Strategy

**No unittest.mock.** Uses manual fake implementations instead.

### Fake Implementations (`tests/unit/fakes.py`)

```python
class FakeDataRepository:
    """In-memory implementation of DataRepository for testing."""
    def __init__(self) -> None:
        self.records: dict[str, dict[str, Any]] = {}
        self.add_calls: list[tuple[str, str, dict[str, Any]]] = []

    async def add(self, table: str, source_id: str, data: dict[str, Any]) -> str:
        record_id = str(uuid4())
        self.records[record_id] = {"table": table, "source_id": source_id, "data": data}
        self.add_calls.append((table, source_id, data))
        return record_id

class FakeEventPublisher:
    """In-memory implementation of EventPublisher for testing."""
    def __init__(self) -> None:
        self.published_events: list[Any] = []

    async def publish(self, event: Any) -> None:
        self.published_events.append(event)

class FakeSchemaRegistry:
    """Pre-populated with test schemas (contact, product)."""
    def __init__(self) -> None:
        self.schemas: dict[str, type[BaseModel]] = {}
        self._register_test_schemas()
```

### Why Fakes Over Mocks

- **Explicit contracts:** Fakes implement the same port protocols as real adapters
- **Call recording:** `add_calls`, `published_events` lists for verification
- **Readable assertions:** `assert len(repository.add_calls) == 1` vs mock.assert_called_once()
- **No magic:** No patch decorators or mock setup complexity

## Fixture Patterns

### Integration Test Fixtures (`tests/integration/conftest.py`)

```python
@pytest.fixture
async def engine():
    """Create in-memory SQLite engine per test."""
    eng = create_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()

@pytest.fixture
async def session_factory(engine) -> async_sessionmaker[AsyncSession]:
    """Create session factory from test engine."""
    return create_session_factory(engine)

@pytest.fixture
async def repository(session_factory):
    """Create repository instance for testing."""
    return SQLiteDataRepository(session_factory)
```

**Environment setup:** Tests set `NANGO_WEBHOOK_SECRET` before imports to avoid Settings validation errors.

### Unit Test Setup

Uses `setup_method` for fixture initialization:
```python
class TestAddDataHandler:
    def setup_method(self) -> None:
        self.repository = FakeDataRepository()
        self.event_publisher = FakeEventPublisher()
        self.schema_registry = FakeSchemaRegistry()
        self.handler = AddDataHandler(
            repository=self.repository,
            event_publisher=self.event_publisher,
            schema_registry=self.schema_registry,
        )
```

## Common Test Patterns

### Async Test Pattern

```python
@pytest.mark.asyncio
async def test_handler_validates_and_persists_data(self) -> None:
    command = AddDataCommand(
        table="contacts",
        source_id="integration_123",
        schema_name="contact",
        raw_data={"name": "Alice", "email": "alice@example.com"},
    )
    event = await self.handler.handle(command)

    assert len(self.repository.add_calls) == 1
    table, source_id, data = self.repository.add_calls[0]
    assert table == "contacts"
```

### Error Testing Pattern

```python
@pytest.mark.asyncio
async def test_handle_raises_on_invalid_data(self) -> None:
    command = AddDataCommand(
        table="contacts",
        source_id="test",
        schema_name="contact",
        raw_data={"name": "Diana"},  # missing email
    )
    with pytest.raises(ValidationError) as exc_info:
        await self.handler.handle(command)

    assert exc_info.value.schema_name == "contact"
```

### Side Effect Verification Pattern

```python
@pytest.mark.asyncio
async def test_handle_does_not_persist_on_validation_failure(self) -> None:
    command = AddDataCommand(...)
    with pytest.raises(ValidationError):
        await self.handler.handle(command)

    # Verify no side effects occurred
    assert len(self.repository.add_calls) == 0
    assert len(self.event_publisher.published_events) == 0
```

## Coverage

**Tool:** pytest-cov

**Run with coverage:**
```bash
pytest --cov=src --cov-report=term-missing
```

## Running Tests

```bash
# All tests
pytest

# Integration only
pytest tests/integration/

# Unit only
pytest tests/unit/

# Specific test file
pytest tests/unit/test_add_data_handler.py

# With coverage
pytest --cov=src --cov-report=html
```
