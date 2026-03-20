# Requirements: data-hub

**Defined:** 2026-03-19
**Core Value:** Data from connected integrations flows reliably into the platform with strict validation — if it's in the database, it's valid.

## v0.1.0 Requirements

Requirements for v0.1.0 milestone: Production Storage & Query.

### PostgreSQL

- [x] **PGRS-01**: User can run data-hub against PostgreSQL via DATABASE_URL
- [x] **PGRS-02**: PostgreSQL adapter uses asyncpg driver for async operations
- [x] **PGRS-03**: Idempotent inserts on PostgreSQL prevent duplicate records (ON CONFLICT parity with SQLite)

### Backend Configuration

- [x] **CONF-01**: Repository factory creates correct adapter based on DATABASE_URL scheme
- [x] **CONF-02**: SQLite and PostgreSQL adapters coexist without code changes to switch

### Query

- [x] **QURY-01**: DataRepository.query() read port accepts parameterized SQL
- [x] **QURY-02**: QueryData query in kernel follows same pattern as AddDataCommand (CQRS)
- [x] **QURY-03**: Query handler executes parameterized SQL via repository port
- [x] **QURY-04**: Both SQLite and PostgreSQL adapters implement query() method
- [ ] **QURY-05**: Query HTTP endpoint exposes query capability via API (POST /query)
- [ ] **QURY-06**: Query parameters use bindparams only — no raw SQL from callers

## Future Requirements

Deferred to future milestone+. Tracked but not in current roadmap.

### Resilience

- **RESL-01**: Automatic retry with exponential backoff for transient failures
- **RESL-02**: Dead letter queue stores failed records for inspection and replay

### Schema Management

- **SCHM-01**: Schema drift detection alerts when incoming data shape changes unexpectedly
- **SCHM-02**: Schema versioning tracks evolution over time

### Extended Observability

- **EOBS-01**: Column-level lineage tracks source field to destination mapping
- **EOBS-02**: Dashboard visualizes data quality metrics over time

### Advanced Query

- **QURY-07**: Query results paginated for large datasets
- **QURY-08**: Connection pool config via ENV vars (pool_size, max_overflow)

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Real-time streaming | Webhooks are micro-batch; <5s latency is sufficient |
| Multiple active backends | One backend per deployment; no routing layer |
| ORM query builder in kernel | Leaks ORM types; keep kernel SQL as strings with params |
| Free-form SQL from HTTP callers | SQL injection risk; callers provide structured params |
| Database-specific query syntax | Keep queries simple enough for both backends |
| Event consumers | Deferred to future milestone |
| Schema drift detection | Deferred to future milestone |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| PGRS-01 | Phase 4 | Complete |
| PGRS-02 | Phase 4 | Complete |
| PGRS-03 | Phase 4 | Complete |
| CONF-01 | Phase 4 | Complete |
| CONF-02 | Phase 4 | Complete |
| QURY-01 | Phase 5 | Complete |
| QURY-02 | Phase 5 | Complete |
| QURY-03 | Phase 5 | Complete |
| QURY-04 | Phase 5 | Complete |
| QURY-05 | Phase 5 | Pending |
| QURY-06 | Phase 5 | Pending |

**Coverage:**
- v0.1.0 requirements: 11 total
- Mapped to phases: 11
- Unmapped: 0

---
*Requirements defined: 2026-03-19*
*Last updated: 2026-03-19 after roadmap v0.1.0 created*
