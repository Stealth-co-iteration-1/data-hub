# Technology Stack

**Analysis Date:** 2026-03-18

## Languages

**Primary:**
- Python 3.12+ - All application code, async-first design

## Runtime

**Environment:**
- Python 3.12 (minimum required via `requires-python = ">=3.12"`)
- Uvicorn 0.42.0+ - ASGI server for FastAPI async request handling
- Optional: Gunicorn 23.0+ with `uvicorn.workers.UvicornWorker` for multi-process production deployments

**Package Manager:**
- UV (Rust-based, modern Python package manager)
- Lockfile: `uv.lock` (present, tracks exact versions for reproducibility)

## Frameworks

**Core:**
- FastAPI 0.135.1+ - Web framework with async-first design, auto-documentation, dependency injection
  - Location: `src/adapters/driving/fastapi/app.py` defines FastAPI application
  - Routes: `src/adapters/driving/fastapi/routes/` contains webhook, health, and metrics endpoints
  - Middleware: `src/adapters/driving/fastapi/middleware.py` implements request correlation ID context

**Data Persistence:**
- SQLAlchemy 2.0.48+ with asyncio support - Async ORM for database operations
  - Async Session: `async_sessionmaker` from `sqlalchemy.ext.asyncio`
  - Database engine: Created in app lifespan via `src/adapters/driving/fastapi/app.py`
  - Models: `src/adapters/driven/sqlite/models.py` defines `DataRecord` and `AuditLog` ORM models

**Database Migrations:**
- Alembic 1.18.4+ - Database migration framework with async support
  - Config: `alembic.ini` configured for SQLite
  - Migration scripts: `migrations/` directory with versioned SQL scripts
  - Connection string: `sqlite+aiosqlite:///./data.db` (configurable via `DATABASE_URL` env var)

**Async Runtime:**
- aiosqlite 0.20+ - Async SQLite driver for non-blocking database I/O

**Testing:**
- pytest 8.3+ - Test runner with async support
  - Config: `pyproject.toml` sets `asyncio_mode = "auto"` for automatic async fixture handling
  - Coverage: pytest-cov 6.0+ for code coverage analysis
- pytest-asyncio 0.24+ - Async test support with function-scoped event loops

**Validation:**
- Pydantic 2.12.5+ - Data validation and serialization using type hints
  - Settings: `pydantic-settings>=2.13.1` for environment-based configuration
  - Location: Schema validation in `src/kernel/validators/schema_validator.py`
  - FastAPI integration: Automatic request/response validation via `src/adapters/driving/fastapi/schemas.py`

## Key Dependencies

**Critical:**
- pydantic 2.12.5+ - Why it matters: Core validation for webhook payloads and schema enforcement. Kernel uses Pydantic for type safety across all domain models.
- sqlalchemy[asyncio] 2.0.48+ - Why it matters: Async ORM enables non-blocking database operations critical for handling webhook bursts without blocking the async event loop.
- fastapi[standard] 0.135.1+ - Why it matters: Provides web server with built-in async support, automatic OpenAPI documentation, and dependency injection for handler composition.
- structlog 25.5.0+ - Why it matters: Structured JSON logging with correlation IDs for distributed tracing and log aggregation support in production.

**Infrastructure:**
- prometheus-client 0.24.1+ - Prometheus metrics export via `/metrics` endpoint for Kubernetes/monitoring system integration
- uvicorn 0.42.0+ - ASGI server implementation handling async request/response cycle

**Development/Code Quality:**
- ruff 0.9+ - Fast Python linter and formatter (enforces 100-char line length)
- pyright 1.1+ - Static type checker in strict mode for type safety across codebase
- httpx 0.28.1+ - Async HTTP client for tests and webhook signature verification

## Configuration

**Environment:**
- `.env` file support via pydantic-settings (loads `nango_webhook_secret`, `database_url`, `env`, `log_level`)
- nango_webhook_secret (required) - HMAC-SHA256 secret for webhook signature verification, stored in environment
- database_url (optional, defaults to `sqlite+aiosqlite:///./data.db`)
- env (optional, defaults to `production`, can be `development` or `staging`)
- log_level (optional, defaults to `INFO`)

**Build:**
- `pyproject.toml` - Project metadata, dependencies, and tool configuration
  - Tool configs: ruff (line-length=100, target-version=py312), pyright (strict mode)
  - Test config: pytest with asyncio_mode="auto"
- `uv.lock` - Locked dependency versions for reproducible builds

## Platform Requirements

**Development:**
- Python 3.12+
- SQLite support (included with Python)
- Virtual environment via `.venv` (or managed by UV)
- For running: `pip install -e .` or `uv sync`

**Production:**
- Python 3.12+ runtime
- SQLite database file with read/write permissions (or configurable database URL for PostgreSQL, MySQL, etc. via SQLAlchemy)
- ASGI server: Uvicorn (directly) or Gunicorn with Uvicorn workers
- Environment variables: `NANGO_WEBHOOK_SECRET` (required), optional `DATABASE_URL`, `ENV`, `LOG_LEVEL`
- Recommended: Gunicorn for multi-process deployment: `gunicorn -w 4 -k uvicorn.workers.UvicornWorker src.adapters.driving.fastapi.app:app`

---

*Stack analysis: 2026-03-18*
