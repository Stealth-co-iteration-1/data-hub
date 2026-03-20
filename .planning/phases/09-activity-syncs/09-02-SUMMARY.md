---
phase: 09-activity-syncs
plan: "02"
subsystem: api
tags: [salesforce, nango, zod, soql, sync, events]

# Dependency graph
requires:
  - phase: 06-salesforce-sync-infrastructure
    provides: utils.ts (queryEndpoint, salesforcePaginationConfig), types.ts (sfId, sfDateTime, sfDate, sfNullableString, sfNullableNumber)
  - phase: 07-opportunities-sync
    provides: Owner relationship denormalization pattern (ownerSchema, id aliasing)
provides:
  - Salesforce Event sync (fetch-events.ts) with Who and Owner relationship denormalization
  - 13 EVNT-01 spec fields including StartDateTime, EndDateTime, DurationInMinutes, EventSubtype
  - Who.Email via SOQL relationship query for downstream join key resolution
  - Owner.Name + Owner.Email via SOQL for rep attribution
  - WhoId and WhatId preserved as sfId | null for polymorphic downstream joins
  - StartDateTime-based incremental filter (EVNT-02)
  - Sync registered in nango-integrations/index.ts
affects: [downstream attribution analysis, activity analytics, rep activity reporting]

# Tech tracking
tech-stack:
  added: []
  patterns: [Who relationship schema for polymorphic Contact/Lead join key, StartDateTime >= incremental filter for DateTime cursor fields]

key-files:
  created:
    - nango-integrations/salesforce/syncs/fetch-events.ts
  modified:
    - nango-integrations/index.ts

key-decisions:
  - "Use StartDateTime >= (not >) for incremental filter to include events starting at exact sync timestamp"
  - "whoSchema captures only Email — sufficient for downstream join key resolution without over-fetching"
  - "WhoId and WhatId typed as sfId | null (not sfNullableString) — preserves 18-char ID constraint while allowing null"

patterns-established:
  - "Who relationship schema pattern: z.object({ Email: sfNullableString }) mirrors Contact subquery for join key"
  - "DateTime cursor fields use >= instead of > to avoid off-by-one at exact boundary timestamps"

requirements-completed: [EVNT-01, EVNT-02, EVNT-03]

# Metrics
duration: 2min
completed: 2026-03-20
---

# Phase 09 Plan 02: Event Sync Summary

**Salesforce Event sync with Who/Owner relationship denormalization, StartDateTime incremental filter, and all 13 EVNT-01 spec fields via custom SOQL with relationship traversal**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-20T12:41:15Z
- **Completed:** 2026-03-20T12:43:06Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Created `fetch-events.ts` with full eventSchema (13 spec fields + Nango `id` key), whoSchema for join key resolution, ownerSchema for rep attribution
- Built `buildEventQuery` with `StartDateTime >=` incremental filter and `IsDeleted = false` base condition
- Registered sync in `nango-integrations/index.ts`; `nango compile` confirms all 7 syncs build and generate artifacts cleanly

## Task Commits

Each task was committed atomically:

1. **Task 1: Create fetch-events.ts sync with Zod schemas and SOQL query builder** - `ae870e4` (feat)
2. **Task 2: Register fetch-events sync in index.ts** - `42b9bca` (feat)

**Plan metadata:** (docs commit — see final commit hash)

## Files Created/Modified

- `nango-integrations/salesforce/syncs/fetch-events.ts` - Event sync with eventSchema, whoSchema, ownerSchema, buildEventQuery, createSync definition
- `nango-integrations/index.ts` - Added `import './salesforce/syncs/fetch-events.js'`

## Decisions Made

- Used `StartDateTime >=` (not `>`) for incremental filter — DateTime fields should use `>=` to include events at the exact boundary timestamp, avoiding missed records
- `whoSchema` captures only `Email` field — sufficient for join key resolution in downstream attribution without over-fetching Lead/Contact fields
- `WhoId` and `WhatId` typed as `z.union([sfId, z.null()])` rather than `sfNullableString` — preserves 18-char ID length validation constraint while allowing null for events without a linked person or record

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - TypeScript compile and `nango compile` both passed on first attempt.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All three Event requirements satisfied: EVNT-01 (all spec fields), EVNT-02 (StartDateTime incremental filter), EVNT-03 (WhoId/WhatId preserved)
- Phase 09 now complete: both Task sync (09-01) and Event sync (09-02) ready for Nango deployment
- No blockers

---
*Phase: 09-activity-syncs*
*Completed: 2026-03-20*
