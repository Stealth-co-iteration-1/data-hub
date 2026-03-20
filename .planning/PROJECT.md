# data-hub

## What This Is

The data component of the Staq system — a Python service that receives raw integration data from external sources via Nango webhooks, validates it against schemas, and persists it to the database. Built with a clean kernel/transport separation where the kernel contains pure business logic with no external dependencies. Uses SQLite for v0.0.1 development, with PostgreSQL planned for production via hexagonal architecture swap.

## Core Value

Data from connected integrations flows reliably into the platform with strict validation — if it's in the database, it's valid.

## Requirements

### Validated

- [x] AddData command accepts table name, source ID, schema hint, and raw data — *Validated in Phase 1: Foundation & Kernel*
- [x] Strict schema validation rejects malformed data — *Validated in Phase 1: Foundation & Kernel*
- [x] DataAdded event emitted on successful persistence — *Validated in Phase 1: Foundation & Kernel*
- [x] Data persisted to SQLite with ACID guarantees — *Validated in Phase 2: Persistence & Data Flow*
- [x] Audit trail captures timestamp, source_id, table_name, status — *Validated in Phase 2: Persistence & Data Flow*
- [x] Idempotent processing prevents duplicate records — *Validated in Phase 2: Persistence & Data Flow*
- [x] Verification capability to confirm data storage — *Validated in Phase 2: Persistence & Data Flow*
- [x] FastAPI endpoint receives Nango webhooks — *Validated in Phase 3: Webhook Transport & Observability*
- [x] Webhook signature verified on raw bytes — *Validated in Phase 3: Webhook Transport & Observability*
- [x] Health check endpoint returns service status — *Validated in Phase 3: Webhook Transport & Observability*
- [x] Structured logging with correlation IDs — *Validated in Phase 3: Webhook Transport & Observability*

- [x] PostgreSQL adapter with asyncpg driver — *Validated in Phase 4: PostgreSQL Backend*
- [x] Configurable storage backend (sqlite/postgres via ENV) — *Validated in Phase 4: PostgreSQL Backend*
- [x] QueryData command with SQL-based interface — *Validated in Phase 5: Query Capability*
- [x] DataRepository.query() read port — *Validated in Phase 5: Query Capability*
- [x] Query HTTP endpoint — *Validated in Phase 5: Query Capability*

- [x] Salesforce sync infrastructure (utils, Zod schemas, types) — *Validated in Phase 6: Salesforce Sync Infrastructure*
- [x] Opportunity sync with nested OpportunityContactRoles — *Validated in Phase 7: Opportunity Sync*
- [x] OpportunityHistory sync for stage tracking — *Validated in Phase 8: OpportunityHistory Sync*
- [x] Task sync for emails and calls — *Validated in Phase 9: Activity Syncs*
- [x] Event sync for meetings — *Validated in Phase 9: Activity Syncs*

### Active

(None — planning next milestone)

### Out of Scope

- Event consumers — deferred to future milestone
- Schema drift detection — deferred to future milestone
- Real-time streaming — batch/webhook model for now

## Context

**Architecture pattern:** Hexagonal / Ports & Adapters
- **Kernel:** Commands, Queries, Events — pure Python, no dependencies
- **Adapters:** SQLite repository (v1), FastAPI transport (Phase 3)
- **Ports:** Interfaces defined in kernel, implemented by adapters

**Integration source:** Nango handles OAuth and connection management for external services (CRMs, analytics tools, etc.). When data syncs, Nango sends webhook callbacks to data-hub.

**Part of:** Staq system (larger platform this component serves)

## Constraints

- **Language**: Python — team standard
- **Kernel purity**: No external dependencies in kernel module — business logic must be testable in isolation
- **Storage**: SQLite (v1), PostgreSQL (production) — hexagonal architecture enables swap
- **Integration**: Nango webhooks — existing integration layer

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Kernel/transport separation | Testability, flexibility to add transports later | ✓ Validated (Phase 1) |
| Strict schema validation | Data integrity over flexibility — bad data rejected at entry | ✓ Validated (Phase 1) |
| Generic AddData (table in payload) | Flexibility for multiple data types without per-type commands | ✓ Validated (Phase 1) |
| Events over callbacks | Decoupled notification of state changes | ✓ Validated (Phase 1) |
| SQLite for v1 | Zero-config development, easy PostgreSQL swap via hexagonal architecture | ✓ Validated (Phase 2) |
| Idempotent inserts via ON CONFLICT | Prevents duplicate records from webhook retry storms | ✓ Validated (Phase 2) |
| Atomic audit trail | Audit log written in same transaction as data for consistency | ✓ Validated (Phase 2) |
| FastAPI with fast-ack | 202 response before background processing for webhook reliability | ✓ Validated (Phase 3) |
| Structlog with correlation IDs | Request tracing from ingestion through processing for debugging | ✓ Validated (Phase 3) |
| Prometheus-style metrics | Counters and histograms for operational monitoring | ✓ Validated (Phase 3) |
| PostgreSQL adapter via factory | Scheme-based backend selection from DATABASE_URL | ✓ Validated (Phase 4) |
| Repository factory pattern | Create correct adapter based on URL scheme, fail fast on unknown | ✓ Validated (Phase 4) |

## Current State (v0.0.1 Shipped)

**Shipped:** 2026-03-19
**Codebase:** 3,797 LOC Python (1,697 src + 2,100 tests)
**Tests:** 80 passing
**Tech stack:** Python 3.12+, FastAPI, SQLAlchemy 2.0 async, structlog, prometheus_client, Pydantic, Alembic

**Endpoints:**
- `POST /webhooks/nango` — webhook ingestion with HMAC signature verification
- `GET /health` — health check with DB connectivity test
- `GET /metrics` — Prometheus metrics

**Known tech debt:**
- No automated migration on startup (manual `alembic upgrade head` required)
- InMemoryEventPublisher stores events that are never consumed
- session.py helpers unused in production (app.py reimplements inline)

## Current State (v0.1.0 Shipped)

**Shipped:** 2026-03-20
**Codebase:** ~5,948 LOC Python
**Tests:** 134 passing
**Tech stack:** Python 3.12+, FastAPI, SQLAlchemy 2.0 async, asyncpg, structlog, prometheus_client, Pydantic, Alembic

**Capabilities:**
- Webhook ingestion with HMAC verification (POST /webhooks/nango)
- Schema validation with structured error reporting
- SQLite or PostgreSQL persistence via DATABASE_URL
- Query API (POST /query/{model}) with injection prevention
- Health check, Prometheus metrics, structured logging

## Current State (v0.2.0 Shipped)

**Shipped:** 2026-03-20
**Codebase:** ~5,948 LOC Python + 729 LOC TypeScript (Nango syncs)
**Tests:** 134 passing (Python)
**Syncs:** 4 Salesforce syncs (Opportunity, OpportunityHistory, Task, Event)

**Capabilities (added in v0.2.0):**
- Salesforce Opportunity sync with nested Account, Owner, and ContactRoles relationships
- OpportunityHistory sync with CreatedDate incremental filter and velocity ordering
- Task sync with Who/Owner denormalization and ActivityDate filter
- Event sync with Who/Owner denormalization and StartDateTime filter
- Shared Salesforce sync infrastructure (pagination, SOQL builder, Zod schemas)
- Event_id generation from payload hash for idempotent sync tracking
- Audit log error status tracking for failed syncs

---
*Last updated: 2026-03-20 after v0.2.0 milestone complete*
