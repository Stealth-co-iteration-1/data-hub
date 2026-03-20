---
phase: 08-opportunityhistory-sync
plan: "01"
subsystem: nango-integrations/salesforce
tags: [salesforce, nango, sync, opportunity-history, stage-velocity, incremental]
dependency_graph:
  requires:
    - nango-integrations/salesforce/utils.ts (queryEndpoint, salesforcePaginationConfig)
    - nango-integrations/salesforce/types.ts (sfId, sfDateTime, sfDate, sfNullableString, sfCurrency, sfPercentage)
  provides:
    - fetch-opportunity-history.ts (OpportunityHistory Nango sync)
    - index.ts registration for fetch-opportunity-history
  affects:
    - nango-integrations/index.ts (added import)
tech_stack:
  added: []
  patterns:
    - Nango createSync with incremental syncType
    - Zod schema with lowercase id alias for Nango record key
    - SOQL ORDER BY for deterministic stage velocity derivation
key_files:
  created:
    - nango-integrations/salesforce/syncs/fetch-opportunity-history.ts
  modified:
    - nango-integrations/index.ts
decisions:
  - "Use CreatedDate for incremental filter: OpportunityHistory records are immutable after creation — no LastModifiedDate changes, so CreatedDate is the correct incremental cursor"
  - "id aliased from Salesforce Id: consistent with fetch-opportunities.ts pattern — Nango ZodModel requires lowercase id as record key"
  - "buildOpportunityHistoryQuery builds SOQL manually: buildQuery utility does not support ORDER BY clauses, so custom builder used (same rationale as Phase 7)"
  - "ORDER BY OpportunityId, CreatedDate ASC: required for HIST-03 — downstream velocity derivation depends on sequential stage changes per opportunity"
metrics:
  duration: "74s"
  completed_date: "2026-03-20"
  tasks_completed: 2
  files_created: 1
  files_modified: 1
requirements_satisfied: [HIST-01, HIST-02, HIST-03]
---

# Phase 08 Plan 01: OpportunityHistory Sync Summary

**One-liner:** Nango sync for Salesforce OpportunityHistory using CreatedDate incremental filter and ORDER BY OpportunityId, CreatedDate ASC for stage velocity derivation.

---

## What Was Built

`fetch-opportunity-history.ts` — A Nango sync that pulls Salesforce `OpportunityHistory` records. OpportunityHistory is an immutable audit log of every Amount/Stage/CloseDate/Probability change, providing the stage change timestamps needed to derive time-in-stage metrics.

**Key implementation details:**
- Zod schema with all 9 HIST-01 fields (`Id`, `OpportunityId`, `StageName`, `Amount`, `CloseDate`, `Probability`, `ForecastCategoryName`, `CreatedDate`, `CreatedById`) plus Nango-required lowercase `id`
- SOQL uses `CreatedDate >` filter for incremental runs (HIST-02) — correct cursor for immutable history records
- `ORDER BY OpportunityId, CreatedDate ASC` ensures sequential stage changes per opportunity for velocity derivation (HIST-03)
- `every hour` frequency with `incremental` syncType
- Registered in `nango-integrations/index.ts` as the 6th import

---

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create OpportunityHistory sync with Zod schema and SOQL builder | 87a2af4 | nango-integrations/salesforce/syncs/fetch-opportunity-history.ts |
| 2 | Register sync in index.ts | ff60402 | nango-integrations/index.ts |

---

## Requirements Satisfied

| Requirement | Description | Verification |
|-------------|-------------|--------------|
| HIST-01 | All spec fields in schema | 9 fields + Nango id in opportunityHistorySchema |
| HIST-02 | CreatedDate incremental filter | `AND CreatedDate > {ISO}` in buildOpportunityHistoryQuery |
| HIST-03 | ORDER BY for velocity derivation | `ORDER BY OpportunityId, CreatedDate ASC` in SOQL |

---

## Decisions Made

1. **CreatedDate for incremental cursor** — OpportunityHistory records are immutable: once created, they never change. Using `CreatedDate >` (not `LastModifiedDate >`) is the correct incremental filter for this object.

2. **id alias from Salesforce Id** — Consistent with `fetch-opportunities.ts` pattern. Nango's ZodModel requires a lowercase `id: ZodString` field as the record key. We spread the raw record and add `id: raw['Id']` before parsing.

3. **Custom SOQL builder** — `buildQuery` from `utils.ts` does not support `ORDER BY` clauses. A custom `buildOpportunityHistoryQuery` function is used, consistent with Phase 7's `buildOpportunityQuery` approach.

4. **ORDER BY is load-bearing** — Stage velocity analysis requires records in chronological order per opportunity. The `ORDER BY OpportunityId, CreatedDate ASC` clause is a correctness requirement, not an optimization.

---

## Deviations from Plan

None — plan executed exactly as written.

---

## Self-Check: PASSED

| Item | Status |
|------|--------|
| nango-integrations/salesforce/syncs/fetch-opportunity-history.ts | FOUND |
| nango-integrations/index.ts | FOUND |
| Commit 87a2af4 (Task 1) | FOUND |
| Commit ff60402 (Task 2) | FOUND |
