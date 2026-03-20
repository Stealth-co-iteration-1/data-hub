---
gsd_state_version: 1.0
milestone: v0.2
milestone_name: milestone
status: unknown
stopped_at: Completed 09-02-PLAN.md
last_updated: "2026-03-20T13:51:44.193Z"
progress:
  total_phases: 4
  completed_phases: 3
  total_plans: 4
  completed_plans: 5
---

# Project State: data-hub

**Last updated**: 2026-03-20
**Status**: Phase 09 complete — Salesforce Task sync (fetch-tasks.ts) and Event sync (fetch-events.ts) ready; TASK-01 through TASK-03 and EVNT-01 through EVNT-03 satisfied

---

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-20)

**Core Value**: Data from connected integrations flows reliably into the platform with strict validation — if it's in the database, it's valid.

**Current Focus**: v0.2.0 Salesforce Revenue Reporting Syncs — Nango syncs for Opportunities, OpportunityHistory, Tasks, Events

**Architecture**: Hexagonal (Ports & Adapters) with CQRS pattern

---

## Current Position

Phase: 09 (activity-syncs) — COMPLETE
Plan: 2 of 2 (all plans complete)

## Session Log

| Session | Date | Accomplishment |
|---------|------|----------------|
| 1 | 2026-03-19 | Created roadmap for v0.2.0 (4 phases, 17 requirements mapped) |
| 2 | 2026-03-19 | Phase 06: Salesforce sync infrastructure (utils.ts, models.ts, types.ts) |

## Performance Metrics

| Metric | Value |
|--------|-------|
| Total phases | 4 |
| Plans completed | 0 |
| Requirements satisfied | 0/17 |
| Blockers encountered | 0 |
| Phase 06-salesforce-sync-infrastructure P01 | 12 | 3 tasks | 3 files |
| Phase 07 P01 | 205 | 3 tasks | 5 files |
| Phase 08 P01 | 74 | 2 tasks | 2 files |
| Phase 09 P02 | 2 | 2 tasks | 2 files |
| Phase 09-activity-syncs P01 | 2 | 2 tasks | 2 files |

## Accumulated Context

### Key Decisions

| Decision | Rationale | Phase |
|----------|-----------|-------|
| z.union for nullables (not z.nullable) | Preserves null semantics with no coercion — per CONTEXT.md decision | 06 |
| types.ts re-exports all models.ts schemas | Single import point for downstream syncs in Phases 7-9 | 06 |
| buildQuery uses Date.toISOString() for LastModifiedDate | Salesforce accepts ISO 8601 in SOQL WHERE clauses | 06 |
| id aliasing: lowercase id added to opportunitySchema | Nango ZodModel requires id: ZodString as record key; Salesforce returns Id so we spread and alias at parse time | 07 |
| Custom buildOpportunityQuery replaces buildQuery | buildQuery does not support relationship field traversal (Account.Name, subqueries) | 07 |
| nango.lastSyncDate is a property not a method | Nango SDK exposes lastSyncDate as Date or undefined on NangoSyncBase, not a callable function | 07 |
| Use CreatedDate for incremental cursor in OpportunityHistory | History records are immutable — no LastModifiedDate changes after creation; CreatedDate is the correct cursor | 08 |
| buildOpportunityHistoryQuery builds SOQL manually | buildQuery utility doesn't support ORDER BY; ORDER BY OpportunityId, CreatedDate ASC is required for velocity derivation | 08 |
| StartDateTime >= (not >) for Event incremental filter | DateTime boundary — use >= to include events starting at exact sync timestamp, avoiding missed records at boundary | 09 |
| whoSchema captures only Email field for Event Who relationship | Sufficient for downstream join key resolution without over-fetching Contact/Lead fields | 09 |
| WhoId and WhatId typed as sfId | null (not sfNullableString) | Preserves 18-char Salesforce ID length constraint while allowing null for Events without linked person/record | 09 |
| ActivityDate filter uses >= and date-only ISO slice for Tasks | ActivityDate is a Salesforce DATE type (YYYY-MM-DD); must strip time component from lastSyncDate with split('T')[0] | 09 |

### Open Questions

- (None yet)

### Blockers

- (None)

### Deferred Items

- (None yet)

## Tech Debt Log

| Item | Severity | Added | Phase |
|------|----------|-------|-------|
| (None yet) | - | - | - |

---

## Milestone History

**v0.1.0** (shipped 2026-03-20): 2 phases, 6 plans — PostgreSQL backend + Query capability
**v0.0.1** (shipped 2026-03-19): 3 phases, 10 plans — Foundation + Persistence + Transport

---

## Session Continuity

**Last session:** 2026-03-20T12:43:57.431Z
**Stopped at:** Completed 09-02-PLAN.md

### Next Actions

1. Phase 09 complete — all 4 phases of v0.2.0 Salesforce Revenue Reporting Syncs done

### Files Modified This Session

- nango-integrations/salesforce/syncs/fetch-tasks.ts (created)
- nango-integrations/salesforce/syncs/fetch-events.ts (created)
- nango-integrations/index.ts (updated)
- .planning/phases/09-activity-syncs/09-01-SUMMARY.md (created)
- .planning/phases/09-activity-syncs/09-02-SUMMARY.md (created)
- .planning/STATE.md (updated)
- .planning/ROADMAP.md (updated)

---
*Last updated: 2026-03-19*
