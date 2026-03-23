# Roadmap: data-hub v0.3 Dagster Salesforce Pipeline

## Overview

v0.3 adds a pull-based Salesforce data ingestion pipeline using Dagster alongside the existing FastAPI webhook service. Four Salesforce objects (Opportunity, OpportunityHistory, Task, Event) are materialized as Dagster assets, pulling pre-synced data from Nango's Records API and persisting to dedicated PostgreSQL tables. The architecture is additive — Dagster runs as a separate process.

**Architectural decisions:**
- **Nango Records API** (GET /records) instead of proxy for direct SOQL queries — TypeScript syncs are already deployed, Dagster assets just fetch pre-synced records
- **One table per asset** (Dagster best practice) — `salesforce_opportunities`, `salesforce_opportunity_history`, `salesforce_tasks`, `salesforce_events` instead of generic `data_records` table

## Milestones

- v0.0.1 MVP (shipped 2026-03-19) — Phases 1-3
- v0.1.0 Production Storage & Query (shipped 2026-03-20) — Phases 4-5
- v0.2.0 Salesforce Revenue Reporting Syncs (shipped 2026-03-20) — Phases 6-9
- v0.3 Dagster Salesforce Pipeline (in progress) — Phases 10-12

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3...): Planned milestone work
- Decimal phases (10.1, 10.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 10: Dagster Infrastructure** - Project scaffold with PostgreSQL storage and local dev
- [ ] **Phase 11: Nango Resource & Opportunity Asset** - NangoResource wrapping Records API, first asset validates pattern
- [ ] **Phase 12: Remaining Salesforce Assets** - OpportunityHistory, Task, Event assets

## Phase Details

### Phase 10: Dagster Infrastructure
**Goal**: Dagster project scaffold that boots locally with PostgreSQL storage
**Depends on**: v0.2 complete (Phase 9)
**Requirements**: DAGSTER-01, DAGSTER-02, DAGSTER-03
**Success Criteria** (what must be TRUE):
  1. `dagster dev` boots without errors and opens webserver UI
  2. dagster.yaml configures PostgreSQL storage (not SQLite)
  3. definitions.py and workspace.yaml exist at project root
**Plans**: 1 plan

Plans:
- [ ] 10-01-PLAN.md — Dagster infrastructure with PostgreSQL storage and ping_database validation asset

### Phase 11: Nango Resource & Opportunity Asset
**Goal**: First asset validates end-to-end pattern: fetch from Nango Records API, persist to PostgreSQL
**Depends on**: Phase 10
**Requirements**: NANGO-01, NANGO-02, ASSET-01, OBS-01
**Success Criteria** (what must be TRUE):
  1. NangoResource is a Dagster ConfigurableResource wrapping existing NangoClient
  2. Opportunity asset materializes successfully and persists records to `salesforce_opportunities` table
  3. MaterializeResult includes row count metadata visible in Dagster UI
  4. Running asset twice produces same row count (idempotent full refresh)
**Plans**: TBD

Plans:
- [ ] 11-01: [TBD]

### Phase 12: Remaining Salesforce Assets
**Goal**: OpportunityHistory, Task, Event assets following established Opportunity pattern
**Depends on**: Phase 11
**Requirements**: ASSET-02, ASSET-03, ASSET-04
**Success Criteria** (what must be TRUE):
  1. OpportunityHistory asset materializes and persists records to `salesforce_opportunity_history` table with row count metadata
  2. Task asset materializes and persists records to `salesforce_tasks` table with row count metadata
  3. Event asset materializes and persists records to `salesforce_events` table with row count metadata
**Plans**: TBD

Plans:
- [ ] 12-01: [TBD]

## Progress

**Execution Order:**
Phases execute in numeric order: 10 -> 10.1 -> 10.2 -> 11 -> 12

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 10. Dagster Infrastructure | v0.3 | 0/1 | Planning complete | - |
| 11. Nango Resource & Opportunity Asset | v0.3 | 0/? | Not started | - |
| 12. Remaining Salesforce Assets | v0.3 | 0/? | Not started | - |

---
*Roadmap created: 2026-03-23*
*Last updated: 2026-03-23*
