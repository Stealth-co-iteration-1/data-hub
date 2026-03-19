# Roadmap: data-hub

## Milestones

- [x] **v1.0 MVP** - Phases 1-3 (shipped 2026-03-19)
- [ ] **v2.0 Production Storage & Query** - Phases 4-5 (in progress)

## Phases

<details>
<summary>v1.0 MVP (Phases 1-3) - SHIPPED 2026-03-19</summary>

### Phase 1: Foundation & Kernel
**Goal**: Pure kernel with port interfaces, command handling, and schema validation in place
**Plans**: 4 plans

Plans:
- [x] 01-01: Project structure and port interfaces
- [x] 01-02: AddData command and handler
- [x] 01-03: Schema validation engine
- [x] 01-04: Events and integration tests

### Phase 2: Persistence & Data Flow
**Goal**: Data flows from command through repository to SQLite with audit trail and verification
**Plans**: 3 plans

Plans:
- [x] 02-01: SQLite repository adapter
- [x] 02-02: Audit trail and InMemoryEventPublisher
- [x] 02-03: Alembic async migrations and verification

### Phase 3: Webhook Transport & Observability
**Goal**: External webhook traffic is received, validated, processed, and observable
**Plans**: 3 plans

Plans:
- [x] 03-01: FastAPI webhook transport adapter
- [x] 03-02: Structured logging and correlation IDs
- [x] 03-03: Prometheus metrics and health check endpoint

</details>

### v2.0 Production Storage & Query (In Progress)

**Milestone Goal:** Production-ready storage with configurable SQLite/PostgreSQL backends and SQL-based query capability via kernel command and HTTP endpoint.

- [ ] **Phase 4: PostgreSQL Backend** - PostgreSQL adapter with asyncpg, ENV-based backend factory, migration CI hardening
- [ ] **Phase 5: Query Capability** - QueryData kernel command, both adapters implement query(), injection-safe HTTP endpoint

## Phase Details

### Phase 4: PostgreSQL Backend
**Goal**: The service runs against PostgreSQL via DATABASE_URL with idempotent inserts, and the backend is selected automatically — no code changes required to switch between SQLite and PostgreSQL.
**Depends on**: Phase 3 (v1.0 complete)
**Requirements**: PGRS-01, PGRS-02, PGRS-03, CONF-01, CONF-02
**Success Criteria** (what must be TRUE):
  1. Setting DATABASE_URL to a PostgreSQL connection string causes all data operations to target PostgreSQL without any code change
  2. Setting DATABASE_URL to a SQLite path continues to work exactly as before
  3. Duplicate webhook events sent to PostgreSQL-backed service are silently ignored (no error, no duplicate record)
  4. Alembic migrations run successfully against PostgreSQL — tables are created and the service accepts requests
  5. The /health endpoint reports which backend is active
**Plans**: TBD

Plans:
- [ ] 04-01: asyncpg dependency, DataRepository Protocol query() extension, FakeDataRepository updated
- [ ] 04-02: PostgresDataRepository implementing full protocol (add, get, idempotent insert)
- [ ] 04-03: Backend factory, dependencies.py wiring, migration ENV override, CI hardening

### Phase 5: Query Capability
**Goal**: Stored data is queryable via a parameterized SQL interface through both the kernel and an HTTP endpoint, with injection prevention and unconditional result limits enforced.
**Depends on**: Phase 4
**Requirements**: QURY-01, QURY-02, QURY-03, QURY-04, QURY-05, QURY-06
**Success Criteria** (what must be TRUE):
  1. A caller can POST to /query with structured filter parameters and receive matching records from the active backend
  2. Both SQLite and PostgreSQL backends return identical results for the same query parameters
  3. A query with no limit parameter still returns at most DEFAULT_QUERY_LIMIT records — the cap is enforced unconditionally
  4. Passing a raw SQL string as a filter value does not execute it — only bindparams are accepted from callers
  5. The QueryData kernel command has zero imports from sqlalchemy, asyncpg, or any external dependency
**Plans**: TBD

Plans:
- [ ] 05-01: QueryData command and handler in kernel, FakeDataRepository query() implementation
- [ ] 05-02: SQLiteDataRepository.query() and PostgresDataRepository.query() implementations
- [ ] 05-03: POST /query FastAPI route with Pydantic validation, LIMIT enforcement, allowlist identifier guard

## Progress

**Execution Order:** 4 → 5

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Foundation & Kernel | v1.0 | 4/4 | Complete | 2026-03-18 |
| 2. Persistence & Data Flow | v1.0 | 3/3 | Complete | 2026-03-18 |
| 3. Webhook Transport & Observability | v1.0 | 3/3 | Complete | 2026-03-18 |
| 4. PostgreSQL Backend | v2.0 | 0/3 | Not started | - |
| 5. Query Capability | v2.0 | 0/3 | Not started | - |
