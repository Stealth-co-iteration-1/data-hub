---
phase: 06-salesforce-sync-infrastructure
plan: 01
subsystem: infra
tags: [nango, salesforce, zod, soql, typescript, esm]

# Dependency graph
requires: []
provides:
  - buildQuery helper for SOQL generation with optional incremental LastModifiedDate filter
  - salesforcePaginationConfig for nango.paginate() with nextRecordsUrl following
  - queryEndpoint helper to build Salesforce REST API query URLs
  - Shared Zod schemas: sfId, sfDateTime, sfDate, sfNullableString, sfNullableNumber, sfNullableBoolean, sfCurrency, sfPercentage
  - Inferred TypeScript types: SalesforceId, SalesforceDateTime, SalesforceDate, NullableString, NullableNumber, NullableBoolean, Currency, Percentage
  - Single import point (types.ts) for all shared schemas and types
affects: [07-salesforce-opportunities, 08-salesforce-opportunity-history, 09-salesforce-activities]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "z.union([z.string(), z.null()]) for nullable Salesforce fields — preserves null semantics, no coercion"
    - "z.infer<typeof schema> for TypeScript types derived from runtime schemas"
    - "queryEndpoint + salesforcePaginationConfig composable pattern for nango.paginate()"
    - "Re-export pattern: types.ts is single import point for both schemas and types"

key-files:
  created:
    - nango-integrations/salesforce/utils.ts
    - nango-integrations/salesforce/models.ts
    - nango-integrations/salesforce/types.ts
  modified: []

key-decisions:
  - "z.union for nullables (not z.nullable or z.optional) to preserve null semantics with no coercion"
  - "types.ts re-exports all models.ts schemas so downstream syncs have a single import point"
  - "salesforcePaginationConfig kept as plain object (not function) — it is stateless and shared"
  - "buildQuery uses Date.toISOString() for LastModifiedDate — Salesforce accepts ISO 8601 in SOQL WHERE clauses"

patterns-established:
  - "SOQL building: buildQuery(model, fields, lastSyncDate?) + queryEndpoint(soql) → endpoint string"
  - "Pagination: { endpoint: queryEndpoint(soql), paginate: salesforcePaginationConfig } passed to nango.paginate()"
  - "Nullable fields: sfNullableString / sfNullableNumber / sfNullableBoolean (z.union pattern)"
  - "Field IDs: sfId (18-char string), dates: sfDateTime (ISO8601), sfDate (YYYY-MM-DD)"
  - "Import convention: import from '../types.js' for both schemas and TypeScript types"

requirements-completed: [INFR-01, INFR-02, INFR-03]

# Metrics
duration: 12min
completed: 2026-03-19
---

# Phase 6 Plan 01: Salesforce Sync Infrastructure Summary

**Shared Salesforce sync foundation: SOQL buildQuery helper, nextRecordsUrl pagination config, and Zod schemas (sfId, sfDateTime, sfNullableString, etc.) enabling incremental syncs for Phases 7-9**

## Performance

- **Duration:** 12 min
- **Started:** 2026-03-20T01:14:04Z
- **Completed:** 2026-03-20T01:26:00Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- Created `utils.ts` with `buildQuery` (SOQL + incremental filter), `queryEndpoint`, `salesforcePaginationConfig`, and `SALESFORCE_API_VERSION` constant
- Created `models.ts` with eight shared Zod schema helpers covering all common Salesforce field patterns (ID, datetime, date, nullable primitives, currency, percentage)
- Created `types.ts` as a single import point re-exporting all schemas plus TypeScript types inferred via `z.infer`

## Task Commits

Each task was committed atomically:

1. **Task 1: Create utils.ts with buildQuery and pagination config** - `6816a1b` (feat)
2. **Task 2: Create models.ts with shared Zod schema helpers** - `784aaf4` (feat)
3. **Task 3: Create types.ts with TypeScript types inferred from Zod schemas** - `ff18dcb` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `nango-integrations/salesforce/utils.ts` - SOQL query builder, pagination config, query endpoint helper, API version constant
- `nango-integrations/salesforce/models.ts` - Shared Zod schemas for Salesforce field patterns using z.union for nullables
- `nango-integrations/salesforce/types.ts` - TypeScript types inferred from schemas, re-exports all schemas as single import point

## Decisions Made

- Used `z.union([z.string(), z.null()])` pattern (not `z.nullable()`) to preserve null semantics per CONTEXT.md decision
- `types.ts` re-exports all of `models.ts` so downstream syncs only need one import path
- `buildQuery` uses `Date.toISOString()` for the `LastModifiedDate` filter — Salesforce accepts ISO 8601 in SOQL
- `salesforcePaginationConfig` is a plain object constant (not a function) since it is stateless and shared across all syncs

## Deviations from Plan

None - plan executed exactly as written.

The per-file `npx tsc --noEmit salesforce/file.ts` command in the plan verification produces node_modules/zod v4 locales errors unrelated to our code (a known artifact of single-file compilation vs full project check). The full project `npx tsc --noEmit` compiles cleanly — used as the authoritative verification.

## Issues Encountered

None of consequence. The zod v4 locale type definition errors appear only when compiling a single file standalone (not with `--skipLibCheck` or full project compile). This is a pre-existing environment artifact, not caused by the new files.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `nango-integrations/salesforce/syncs/` directory is empty and ready for sync implementations
- Phases 7-9 can import from `../utils.js` and `../types.js` for all shared infrastructure
- No blockers — all three modules compile cleanly in full project mode

---
*Phase: 06-salesforce-sync-infrastructure*
*Completed: 2026-03-19*
