---
phase: 12-remaining-salesforce-assets
plan: 01
subsystem: data-pipeline
tags: [dagster, salesforce, nango, postgresql, assets]

# Dependency graph
requires:
  - phase: 11-nango-resource-opportunity-asset
    provides: Reference asset pattern (opportunity.py), NangoResource, PostgresResource
provides:
  - OpportunityHistory asset with full refresh to salesforce_opportunity_history table
  - Task asset with full refresh to salesforce_tasks table
  - Event asset with full refresh to salesforce_events table
  - Complete Salesforce data pipeline with 4 objects
affects: [schedules, incremental-loading, schema-drift-detection]

# Tech tracking
tech-stack:
  added: []
  patterns: [dagster-asset-full-refresh, nango-records-api, jsonb-multi-tenant-storage]

key-files:
  created:
    - dagster_pipelines/assets/salesforce/opportunity_history.py
    - dagster_pipelines/assets/salesforce/task.py
    - dagster_pipelines/assets/salesforce/event.py
  modified:
    - dagster_pipelines/assets/salesforce/__init__.py
    - dagster_pipelines/definitions.py

key-decisions:
  - "Exact pattern replication from opportunity.py ensures consistency"
  - "Composite primary key (salesforce_id + connection_id) for multi-tenant support"

patterns-established:
  - "Salesforce asset pattern: CREATE TABLE DDL + DELETE/INSERT full refresh"
  - "MaterializeResult with dagster/row_count for UI visibility"

requirements-completed: [ASSET-02, ASSET-03, ASSET-04]

# Metrics
duration: 2min
completed: 2026-03-23
---

# Phase 12 Plan 01: Remaining Salesforce Assets Summary

**Three Salesforce assets (OpportunityHistory, Task, Event) with DELETE+INSERT full refresh to PostgreSQL tables**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-23T14:58:01Z
- **Completed:** 2026-03-23T14:59:29Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Created OpportunityHistory asset materializing to salesforce_opportunity_history table
- Created Task asset materializing to salesforce_tasks table
- Created Event asset materializing to salesforce_events table
- All four Salesforce assets registered in Dagster definitions (now total of 4)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create three Salesforce asset files** - `fdf1197` (feat)
2. **Task 2: Register assets in definitions and exports** - `8668d72` (feat)

**Plan metadata:** (pending)

## Files Created/Modified
- `dagster_pipelines/assets/salesforce/opportunity_history.py` - OpportunityHistory asset with full refresh
- `dagster_pipelines/assets/salesforce/task.py` - Task asset with full refresh
- `dagster_pipelines/assets/salesforce/event.py` - Event asset with full refresh
- `dagster_pipelines/assets/salesforce/__init__.py` - Exports all four Salesforce assets
- `dagster_pipelines/definitions.py` - Registers all four assets in defs.Definitions

## Decisions Made
None - followed plan as specified. Exact pattern replication from opportunity.py.

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required. Existing NANGO_CONNECTION_ID and DAGSTER_DATABASE_URL environment variables continue to work.

## Next Phase Readiness
- All four Salesforce objects (Opportunity, OpportunityHistory, Task, Event) now available as Dagster assets
- Ready for scheduling (deferred to v0.3.x)
- Ready for incremental loading enhancements (deferred to v0.4)
- Can run `dagster dev` to materialize assets manually

---
*Phase: 12-remaining-salesforce-assets*
*Completed: 2026-03-23*

## Self-Check: PASSED

- FOUND: opportunity_history.py
- FOUND: task.py
- FOUND: event.py
- FOUND: fdf1197 (Task 1 commit)
- FOUND: 8668d72 (Task 2 commit)
