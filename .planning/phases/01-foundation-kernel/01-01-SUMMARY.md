---
phase: 01-foundation-kernel
plan: 01
subsystem: kernel
tags: [foundation, ports, protocols, exceptions]
dependency_graph:
  requires: []
  provides: [port-interfaces, domain-exceptions, project-structure]
  affects: [all-future-adapters]
tech_stack:
  added: [uv, pytest, pydantic, python-protocols]
  patterns: [hexagonal-architecture, dependency-inversion]
key_files:
  created:
    - pyproject.toml
    - src/kernel/ports/repository.py
    - src/kernel/ports/event_publisher.py
    - src/kernel/ports/schema_registry.py
    - src/kernel/exceptions.py
    - tests/test_kernel_ports.py
  modified:
    - src/kernel/__init__.py
decisions:
  - Used Python Protocols (not ABCs) for port interfaces - enables structural subtyping and runtime_checkable decorator
  - Defined exceptions as dataclasses with structured error data - enables programmatic error handling downstream
  - Zero infrastructure imports in kernel - enforces hexagonal architecture dependency rule
metrics:
  duration: 230
  tasks_completed: 3
  tests_added: 6
  files_created: 11
  completed_at: "2026-03-18T19:59:10Z"
---

# Phase 01 Plan 01: Project Structure & Port Interfaces Summary

**One-liner:** Python project initialized with uv, kernel port interfaces defined as runtime-checkable Protocols, domain exceptions with structured error data.

## What Was Built

### 1. Project Infrastructure
- Created `pyproject.toml` with Python 3.12+ requirement
- Configured Pydantic 2.12.5+ as core dependency
- Set up pytest, pytest-asyncio, ruff, pyright for testing and code quality
- Established directory structure: `src/kernel/`, `src/kernel/ports/`, `tests/`
- Installed and locked dependencies with uv (19 packages)

### 2. Port Interfaces (Hexagonal Architecture)
- **DataRepository Protocol**: Defines `add()` and `get()` methods for data persistence
  - `add(table, source_id, data) -> str` - persist data, return record ID
  - `get(table, record_id) -> dict[str, Any] | None` - retrieve data by ID
- **EventPublisher Protocol**: Defines `publish(event) -> None` for domain events
- **SchemaRegistry Protocol**: Defines `get_schema(schema_name) -> Any | None` for schema lookup
- All protocols use `@runtime_checkable` decorator for isinstance() checks
- Zero infrastructure imports (no SQLAlchemy, FastAPI, asyncpg)

### 3. Domain Exceptions
- **FieldError**: Dataclass with `field_path`, `message`, `expected`, `actual` for structured validation errors
- **KernelError**: Base exception for all kernel errors
- **ValidationError**: Contains list of FieldError instances, schema_name, formatted __str__()
- **SchemaNotFoundError**: Raised when schema not found in registry

### 4. Test Coverage
- 6 tests covering port interface structure and behavior
- Tests verify Protocol pattern, method signatures, runtime_checkable decorator
- Test ensures no infrastructure imports leak into kernel
- All tests pass (TDD RED-GREEN cycle completed)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking Issue] Added .gitignore for Python artifacts**
- **Found during:** Task completion, git status showed untracked __pycache__ directories
- **Issue:** No .gitignore file existed, generated Python cache files would pollute git status
- **Fix:** Created .gitignore excluding __pycache__, *.pyc, .venv, IDE files, test caches
- **Files modified:** .gitignore (created)
- **Commit:** e18a4c7

**2. [Rule 3 - Blocking Issue] Installed dev dependencies before TDD**
- **Found during:** Task 2 RED phase, pytest was not available
- **Issue:** Plan specified pyproject.toml has dev dependencies, but they weren't installed
- **Fix:** Ran `uv sync --all-extras` to install pytest, pytest-asyncio, pytest-cov, ruff, pyright
- **Files modified:** uv.lock (updated with 11 new packages)
- **Commit:** (included in test commit f675471)

## Key Technical Decisions

### 1. Python Protocols vs ABCs
**Decision:** Use typing.Protocol with @runtime_checkable decorator instead of ABC.

**Rationale:**
- Protocols enable structural subtyping (duck typing with type checking)
- More Pythonic for hexagonal architecture port definitions
- Allows adapters to implement interfaces without explicit inheritance
- runtime_checkable enables isinstance() checks at runtime

**Trade-offs:**
- Pros: Flexible, decoupled, enables gradual typing
- Cons: Less explicit than inheritance, requires Python 3.8+

### 2. Structured Error Data
**Decision:** Use dataclasses for FieldError and ValidationError instead of string messages.

**Rationale:**
- Enables programmatic error processing downstream (API responses, logging, analytics)
- Provides field_path for precise error location
- Includes expected vs actual values for debugging
- Follows hexagonal architecture principle: kernel data structures independent of transport

**Trade-offs:**
- Pros: Structured, testable, transport-agnostic
- Cons: More complex than simple string exceptions

### 3. Zero Infrastructure Imports
**Decision:** Enforce zero imports of SQLAlchemy, FastAPI, asyncpg in kernel.

**Rationale:**
- Core principle of hexagonal architecture: kernel has no external dependencies
- Enables pure business logic testing without mocks
- Allows swapping infrastructure (e.g., PostgreSQL → MongoDB) without kernel changes
- Verified with automated test (test_no_infrastructure_imports_in_port_files)

**Trade-offs:**
- Pros: Testability, flexibility, clean architecture
- Cons: Requires port interfaces and dependency injection (added in later phases)

## Verification Results

✓ All acceptance criteria met:
- pyproject.toml contains `name = "data-hub"`, `requires-python = ">=3.12"`, `pydantic>=2.12.5`
- Directory structure created: src/kernel/, src/kernel/ports/, tests/
- DataRepository Protocol with add() and get() methods
- EventPublisher Protocol with publish() method
- SchemaRegistry Protocol with get_schema() method
- All protocols have @runtime_checkable decorator
- No infrastructure imports in any kernel file
- All imports work: `from src.kernel.ports import DataRepository, EventPublisher, SchemaRegistry`
- All imports work: `from src.kernel import ValidationError, FieldError, KernelError, SchemaNotFoundError`
- 6/6 tests pass

✓ Kernel purity verified:
```bash
! grep -rE "^from (sqlalchemy|fastapi|asyncpg|uvicorn)" src/kernel/
# No matches found - kernel is pure
```

## Files Created/Modified

### Created (11 files)
1. `pyproject.toml` - Project configuration with dependencies and tool settings
2. `uv.lock` - Locked dependency versions
3. `src/__init__.py` - Empty package marker
4. `src/kernel/__init__.py` - Kernel package exports (FieldError, ValidationError, etc.)
5. `src/kernel/ports/__init__.py` - Port re-exports
6. `src/kernel/ports/repository.py` - DataRepository Protocol
7. `src/kernel/ports/event_publisher.py` - EventPublisher Protocol
8. `src/kernel/ports/schema_registry.py` - SchemaRegistry Protocol
9. `src/kernel/exceptions.py` - Domain exception classes
10. `tests/__init__.py` - Empty test package marker
11. `tests/test_kernel_ports.py` - Port interface tests (6 tests)

### Modified (1 file)
1. `src/kernel/__init__.py` - Updated with exception exports

## Commits

| Task | Type | Hash | Message |
|------|------|------|---------|
| 1 | chore | c222ad4 | Initialize Python project with uv |
| 2 (RED) | test | f675471 | Add failing test for port interfaces |
| 2 (GREEN) | feat | 3776845 | Implement port interfaces as Python Protocols |
| 3 | feat | 66c754b | Define domain exceptions with structured error data |
| - | chore | e18a4c7 | Add .gitignore for Python artifacts |

## Integration Points

### Upstream Dependencies
- None - this is the foundation plan

### Downstream Impact
- **Phase 01 Plan 02**: Will use port interfaces to build commands and handlers
- **Phase 01 Plan 03**: Will use ValidationError and SchemaNotFoundError
- **Phase 02**: Will implement DataRepository port with PostgreSQL adapter
- **Phase 02**: Will implement EventPublisher port with event bus adapter
- **Phase 03**: FastAPI adapter will catch ValidationError and convert to HTTP 422 responses

## Testing Strategy

### Unit Tests (6 tests, 100% pass)
- Protocol structure verification (3 tests - one per port)
- runtime_checkable decorator verification (1 test)
- Infrastructure import prohibition (1 test)
- Method signature verification (2 tests - DataRepository methods)

### Integration Tests
- Not applicable - no external dependencies yet

### Manual Verification
- Imports work correctly: `python -c "from src.kernel.ports import ..."`
- uv sync succeeds: `uv sync --dry-run`
- Directory structure exists: `ls -la src/kernel/ports/`

## Next Steps

### Immediate (Phase 01 Plan 02)
1. Define AddDataCommand and handler
2. Implement command handler using ports (dependency injection)
3. Define DataAddedEvent

### Future Phases
1. Implement PostgreSQL adapter (DataRepository implementation)
2. Implement event publisher adapter
3. Create FastAPI driving adapter (webhook handler)
4. Wire dependencies with DI container

## Lessons Learned

1. **TDD with Protocols works well**: Writing tests before implementation caught missing runtime_checkable decorator
2. **uv is fast**: 19 packages installed in 19ms (first sync), lockfile resolved in 4ms (subsequent syncs)
3. **Pre-existing directories**: Plan didn't account for existing `domain`, `commands`, `events` dirs from earlier work - no conflict, just noted
4. **Gitignore essential early**: Should be in plan Task 1, not discovered later - prevents polluted git status

## Self-Check

✓ **PASSED**

### Files Verified
- [x] pyproject.toml exists: `test -f pyproject.toml` → true
- [x] src/kernel/ports/repository.py exists: `test -f src/kernel/ports/repository.py` → true
- [x] src/kernel/ports/event_publisher.py exists: `test -f src/kernel/ports/event_publisher.py` → true
- [x] src/kernel/ports/schema_registry.py exists: `test -f src/kernel/ports/schema_registry.py` → true
- [x] src/kernel/exceptions.py exists: `test -f src/kernel/exceptions.py` → true
- [x] tests/test_kernel_ports.py exists: `test -f tests/test_kernel_ports.py` → true

### Commits Verified
- [x] c222ad4 exists: `git log --oneline --all | grep c222ad4` → found
- [x] f675471 exists: `git log --oneline --all | grep f675471` → found
- [x] 3776845 exists: `git log --oneline --all | grep 3776845` → found
- [x] 66c754b exists: `git log --oneline --all | grep 66c754b` → found
- [x] e18a4c7 exists: `git log --oneline --all | grep e18a4c7` → found

### Tests Verified
- [x] All 6 tests pass: `uv run pytest tests/test_kernel_ports.py -v` → 6 passed

---

*Plan executed: 2026-03-18*
*Duration: 230 seconds (~4 minutes)*
*Tasks completed: 3/3*
*Tests: 6 passed*
