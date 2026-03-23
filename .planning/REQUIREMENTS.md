# Requirements: data-hub

**Defined:** 2026-03-23
**Core Value:** Data from connected integrations flows reliably into the platform with strict validation — if it's in the database, it's valid.

## v0.3 Requirements

Requirements for Dagster Salesforce Pipeline milestone. Each maps to roadmap phases.

### Dagster Infrastructure

- [ ] **DAGSTER-01**: Dagster project scaffold with definitions.py and workspace.yaml
- [ ] **DAGSTER-02**: dagster.yaml with PostgreSQL storage (not SQLite)
- [ ] **DAGSTER-03**: dagster dev boots locally without errors

### Nango Client

- [ ] **NANGO-01**: NangoResource ConfigurableResource wrapping existing NangoClient
- [ ] **NANGO-02**: Fetch records via Nango Records API (GET /records)

### Salesforce Assets

- [ ] **ASSET-01**: Opportunity asset with full refresh from Nango Records
- [ ] **ASSET-02**: OpportunityHistory asset with full refresh from Nango Records
- [ ] **ASSET-03**: Task asset with full refresh from Nango Records
- [ ] **ASSET-04**: Event asset with full refresh from Nango Records

### Observability

- [ ] **OBS-01**: MaterializeResult with row count metadata on each asset

## Future Requirements

Deferred to v0.4 or later. Tracked but not in current roadmap.

### Scheduling

- **SCHED-01**: Hourly schedule via AutomationCondition.on_cron("@hourly")
- **SCHED-02**: Multi-connection partitioning by connection_id

### Deployment

- **DEPLOY-01**: Dagster Cloud deployment config (dagster_cloud.yaml)

### Advanced Features

- **ADV-01**: Incremental / cursor-based loading
- **ADV-02**: Schema drift detection

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Nango proxy for direct Salesforce SOQL | Using Nango Records API instead — syncs already deployed |
| Idempotent TRUNCATE-INSERT | Not selected for v0.3 — standard INSERT sufficient |
| Event consumers | Deferred to future milestone |
| Replacing webhook pipeline | Dagster is additive, not a replacement |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DAGSTER-01 | TBD | Pending |
| DAGSTER-02 | TBD | Pending |
| DAGSTER-03 | TBD | Pending |
| NANGO-01 | TBD | Pending |
| NANGO-02 | TBD | Pending |
| ASSET-01 | TBD | Pending |
| ASSET-02 | TBD | Pending |
| ASSET-03 | TBD | Pending |
| ASSET-04 | TBD | Pending |
| OBS-01 | TBD | Pending |

**Coverage:**
- v0.3 requirements: 10 total
- Mapped to phases: 0
- Unmapped: 10 (pending roadmap)

---
*Requirements defined: 2026-03-23*
*Last updated: 2026-03-23 after initial definition*
