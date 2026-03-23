# data-hub

## What This Is

A Dagster-based data pipeline for Salesforce ingestion via Nango. Materializes Salesforce objects (Opportunity, OpportunityHistory, Task, Event) as Dagster assets, pulling pre-synced data from Nango's Records API and persisting to dedicated PostgreSQL tables.

## Core Value

Data from connected integrations flows reliably into the platform — if it's in the database, it's valid.

## Requirements

### Validated

- [x] Dagster local development setup (dagster dev) — *Validated in Phase 10*
- [x] NangoResource for Nango Records API — *Validated in Phase 11*
- [x] Salesforce Opportunity asset with full refresh — *Validated in Phase 11*
- [x] Salesforce OpportunityHistory asset with full refresh — *Validated in Phase 12*
- [x] Salesforce Task asset with full refresh — *Validated in Phase 12*
- [x] Salesforce Event asset with full refresh — *Validated in Phase 12*
- [x] Raw JSON persistence to PostgreSQL — *Validated in Phase 11*
- [x] Dagster Cloud compatible project structure — *Validated in Phase 10*
- [x] Nango TypeScript syncs (Opportunity, OpportunityHistory, Task, Event) — *Validated in v0.2*

### Active

(None — ready for next milestone)

### Out of Scope

- Webhook-based ingestion — replaced by Dagster pull model
- FastAPI HTTP service — removed in v0.4 cleanup
- SQLite storage — PostgreSQL only
- Real-time streaming — batch model via Dagster schedules

## Deferred to Future Milestones

- Hourly schedule via AutomationCondition.on_cron
- Multi-connection partitioning by connection_id
- Dagster Cloud deployment config
- Incremental/cursor-based loading
- Schema drift detection

## Context

**Architecture:** Dagster assets with ConfigurableResource pattern
- **Assets:** One per Salesforce object, full refresh with DELETE+INSERT
- **Resources:** NangoResource (Records API), PostgresResource (psycopg2)
- **Storage:** PostgreSQL with JSONB for raw Salesforce data

**Integration:** Nango handles OAuth and syncs Salesforce data. Dagster assets fetch pre-synced records via Nango Records API.

**Part of:** Staq system (larger platform this component serves)

## Constraints

- **Language**: Python 3.12+ — team standard
- **Orchestrator**: Dagster — batch pipeline framework
- **Storage**: PostgreSQL — production database
- **Integration**: Nango Records API — authentication proxy

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Nango Records API over direct SOQL | TypeScript syncs already deployed; simpler integration | ✓ Validated |
| One table per asset | Dagster best practice; clear data ownership | ✓ Validated |
| DELETE+INSERT for full refresh | Idempotent; handles removed records | ✓ Validated |
| EnvVar pattern for resources | Dagster Cloud compatibility | ✓ Validated |
| JSONB with composite PK | salesforce_id + connection_id for multi-tenant | ✓ Validated |
| Remove FastAPI/webhook code | Dagster is the primary ingestion path | ✓ v0.4 cleanup |

## Project Structure

```
data-hub/
├── definitions.py          # Dagster entry point
├── assets/
│   └── salesforce/         # Salesforce asset definitions
├── resources/              # Dagster ConfigurableResources
├── nango-integrations/     # TypeScript Nango syncs
├── dagster.yaml            # PostgreSQL storage config
├── workspace.yaml          # Dagster workspace config
└── pyproject.toml          # Python dependencies
```

## Current State (v0.4)

**Updated:** 2026-03-23
**Codebase:** ~500 LOC Python + 729 LOC TypeScript (Nango syncs)
**Tech stack:** Python 3.12+, Dagster 1.12+, httpx, psycopg2-binary

**Capabilities:**
- 4 Salesforce assets with full refresh idempotency
- NangoResource with paginated Records API fetching
- MaterializeResult with row count metadata
- PostgreSQL storage for Dagster metadata (dagster schema)

**Running locally:**
```bash
source .env && dagster dev
```

---
*Last updated: 2026-03-23 after v0.4 cleanup (removed FastAPI/webhook code)*
