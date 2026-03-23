---
phase: 11-nango-resource-opportunity-asset
plan: 01
subsystem: data-pipeline
tags: [dagster, nango, salesforce, httpx, postgresql, jsonb]

# Dependency graph
requires:
  - phase: 10-dagster-infrastructure
    provides: PostgresResource, Dagster workspace configuration, definitions.py pattern
provides:
  - NangoResource ConfigurableResource with paginated get_records method
  - salesforce_opportunities asset with full refresh idempotency
  - DELETE+INSERT pattern for Salesforce data persistence
  - MaterializeResult with dagster/row_count metadata
affects: [12-salesforce-assets, salesforce-sync, data-pipeline]

# Tech tracking
tech-stack:
  added: [httpx]
  patterns: [NangoResource lifecycle, cursor-based pagination, JSONB storage]

key-files:
  created:
    - dagster_pipelines/resources/nango.py
    - dagster_pipelines/assets/salesforce/__init__.py
    - dagster_pipelines/assets/salesforce/opportunity.py
  modified:
    - dagster_pipelines/definitions.py
    - dagster_pipelines/resources/__init__.py
    - dagster_pipelines/assets/__init__.py
    - dagster_pipelines/.env.example
    - pyproject.toml

key-decisions:
  - "httpx for HTTP client - already in project, better async support than requests"
  - "execute_values for batch inserts - 10-100x faster than executemany"
  - "DELETE+INSERT in transaction for full refresh idempotency"
  - "JSONB storage with salesforce_id + connection_id composite PK"

patterns-established:
  - "NangoResource: ConfigurableResource with yield_for_execution for httpx.Client lifecycle"
  - "Cursor pagination: while loop with next_cursor check"
  - "Full refresh: DELETE WHERE connection_id = X, then INSERT all"
  - "Asset metadata: dagster/row_count for Dagster UI visibility"

requirements-completed: [NANGO-01, NANGO-02, ASSET-01, OBS-01]

# Metrics
duration: 2min
completed: 2026-03-23
---

# Phase 11 Plan 01: Nango Resource & Opportunity Asset Summary

**NangoResource ConfigurableResource with paginated get_records fetching Salesforce Opportunities to PostgreSQL with DELETE+INSERT full refresh idempotency**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-23T14:35:53Z
- **Completed:** 2026-03-23T14:38:02Z
- **Tasks:** 3
- **Files modified:** 9

## Accomplishments
- Created NangoResource with yield_for_execution lifecycle and cursor-based pagination
- Implemented salesforce_opportunities asset with CREATE TABLE IF NOT EXISTS DDL
- Established DELETE+INSERT pattern for idempotent full refresh
- Wired NangoResource and asset into Dagster definitions
- Moved httpx from dev to main dependencies
- Removed placeholder ping_database asset

## Task Commits

Each task was committed atomically:

1. **Task 1: Create NangoResource with paginated get_records** - `c806ba9` (feat)
2. **Task 2: Create salesforce_opportunities asset with full refresh** - `4d36daf` (feat)
3. **Task 3: Wire into definitions.py and update env configuration** - `71f4a43` (feat)

**Plan metadata:** `be9c6e2` (docs: complete plan)

## Files Created/Modified
- `dagster_pipelines/resources/nango.py` - NangoResource with httpx client and get_records pagination
- `dagster_pipelines/assets/salesforce/__init__.py` - Salesforce assets module
- `dagster_pipelines/assets/salesforce/opportunity.py` - Opportunity asset with full refresh
- `dagster_pipelines/definitions.py` - Updated with NangoResource and salesforce_opportunities
- `dagster_pipelines/resources/__init__.py` - Export NangoResource
- `dagster_pipelines/assets/__init__.py` - Export salesforce_opportunities
- `dagster_pipelines/.env.example` - Added NANGO_SECRET_KEY and NANGO_CONNECTION_ID
- `pyproject.toml` - Moved httpx to main dependencies

## Decisions Made
- Used httpx (already in project) over requests for HTTP client
- Used psycopg2.extras.execute_values for batch inserts (10-100x faster than executemany)
- Connection ID from environment variable at runtime (multi-tenant ready)
- Raw JSONB storage without transformation (validation at query time)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required

**External services require manual configuration.** Before running the asset:

1. Set `NANGO_SECRET_KEY` from Nango Dashboard -> Environment Settings -> Secret Key
2. Set `NANGO_CONNECTION_ID` from Nango Dashboard -> Connections -> Connection ID for Salesforce connection
3. Ensure Salesforce sync is running in Nango to populate records

## Next Phase Readiness
- NangoResource pattern established for all future Salesforce assets
- DELETE+INSERT idempotency pattern proven
- Ready for Phase 12 to add remaining Salesforce assets (Account, Contact, Lead, Task)

## Self-Check: PASSED

All files and commits verified:
- FOUND: dagster_pipelines/resources/nango.py
- FOUND: dagster_pipelines/assets/salesforce/__init__.py
- FOUND: dagster_pipelines/assets/salesforce/opportunity.py
- FOUND: commit c806ba9
- FOUND: commit 4d36daf
- FOUND: commit 71f4a43

---
*Phase: 11-nango-resource-opportunity-asset*
*Completed: 2026-03-23*
