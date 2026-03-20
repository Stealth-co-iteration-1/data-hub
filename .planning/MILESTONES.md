# Milestones

## v0.1.0 Production Storage & Query (Shipped: 2026-03-20)

**Delivered:** Production-ready storage with configurable backends and query capability — PostgreSQL adapter alongside SQLite, ENV-based switching, and parameterized SQL queries via kernel and HTTP.

**Phases completed:** 2 phases, 6 plans
**Lines of code:** ~5,948 LOC Python
**Tests:** 134 passing (127 run, 15 PostgreSQL tests skip without TEST_POSTGRES_URL)
**Requirements:** 11/11 satisfied

**Key accomplishments:**

- PostgreSQL adapter with asyncpg driver for async operations
- Repository factory with URL scheme detection (sqlite/postgres via DATABASE_URL)
- Idempotent inserts on both backends (ON CONFLICT parity)
- QueryData kernel command with zero ORM dependencies
- DataRepository.query() port with connection_id filtering
- POST /query/{model} HTTP endpoint with SQL injection prevention (bindparams only)

**Archives:**

- [v0.1.0-ROADMAP.md](milestones/v0.1.0-ROADMAP.md)
- [v0.1.0-REQUIREMENTS.md](milestones/v0.1.0-REQUIREMENTS.md)

---

## v0.0.1 MVP (Shipped: 2026-03-19)

**Delivered:** Data webhook ingestion platform with strict validation — receives Nango webhooks, validates against schemas, persists to SQLite with audit trail.

**Phases completed:** 3 phases, 10 plans
**Lines of code:** 3,797 LOC Python (1,697 src + 2,100 tests)
**Tests:** 80 passing (unit + integration)
**Requirements:** 17/17 satisfied

**Key accomplishments:**

- Pure kernel architecture with AddDataCommand, DataAddedEvent, and port interfaces (zero external dependencies)
- Schema validation engine using Pydantic with structured error reporting
- SQLite persistence with async SQLAlchemy, idempotent inserts (ON CONFLICT DO NOTHING), and atomic audit trail
- FastAPI webhook transport with HMAC-SHA256 signature verification and fast-ack pattern
- Full observability: structlog with correlation IDs, Prometheus metrics (/metrics), health check (/health)
- Hexagonal architecture enabling future PostgreSQL swap without kernel changes

**Archives:**

- [v0.0.1-ROADMAP.md](milestones/v0.0.1-ROADMAP.md)
- [v0.0.1-REQUIREMENTS.md](milestones/v0.0.1-REQUIREMENTS.md)
- [v0.0.1-MILESTONE-AUDIT.md](milestones/v0.0.1-MILESTONE-AUDIT.md)

---
