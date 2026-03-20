---
gsd_state_version: 1.0
milestone: v0.2
milestone_name: milestone
status: unknown
stopped_at: Completed 08-01-PLAN.md
last_updated: "2026-03-20T12:21:49.350Z"
progress:
  total_phases: 4
  completed_phases: 2
  total_plans: 2
  completed_plans: 3
---

# Project State: data-hub

**Last updated**: 2026-03-20
**Status**: Phase 08 complete — Salesforce OpportunityHistory sync (fetch-opportunity-history.ts) ready; HIST-01 through HIST-03 satisfied

---

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-20)

**Core Value**: Data from connected integrations flows reliably into the platform with strict validation — if it's in the database, it's valid.

**Current Focus**: v0.2.0 Salesforce Revenue Reporting Syncs — Nango syncs for Opportunities, OpportunityHistory, Tasks, Events

**Architecture**: Hexagonal (Ports & Adapters) with CQRS pattern

---

## Current Position

Phase: 08 (opportunityhistory-sync) — COMPLETE
Plan: 1 of 1 (complete)

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

**Last session:** 2026-03-20T12:21:49.348Z
**Stopped at:** Completed 08-01-PLAN.md

### Next Actions

1. Execute Phase 09 (Tasks and Events sync)

### Files Modified This Session

- nango-integrations/salesforce/syncs/fetch-opportunity-history.ts (created)
- nango-integrations/index.ts (updated)
- .planning/phases/08-opportunityhistory-sync/08-01-SUMMARY.md (created)
- .planning/STATE.md (updated)
- .planning/ROADMAP.md (updated)

---
*Last updated: 2026-03-19*
