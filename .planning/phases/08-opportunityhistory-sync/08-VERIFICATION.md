---
phase: 08-opportunityhistory-sync
verified: 2026-03-20T00:00:00Z
status: passed
score: 3/3 must-haves verified
---

# Phase 8: OpportunityHistory Sync Verification Report

**Phase Goal:** Stage change history records available for downstream velocity analysis
**Verified:** 2026-03-20
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | OpportunityHistory records are pulled with all spec fields | VERIFIED | Schema declares all 9 HIST-01 fields (Id, OpportunityId, StageName, Amount, CloseDate, Probability, ForecastCategoryName, CreatedDate, CreatedById) plus Nango-required lowercase `id` — grep count returned 11 matches |
| 2 | Incremental sync filters by CreatedDate on subsequent runs | VERIFIED | `buildOpportunityHistoryQuery` conditionally appends `AND CreatedDate > ${lastSyncDate.toISOString()}` when `nango.lastSyncDate` is defined; property accessed correctly (not called as a method) |
| 3 | Records are ordered by OpportunityId, CreatedDate ASC for velocity derivation | VERIFIED | `ORDER BY OpportunityId, CreatedDate ASC` constant injected unconditionally into every SOQL query at line 60 |

**Score:** 3/3 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `nango-integrations/salesforce/syncs/fetch-opportunity-history.ts` | OpportunityHistory sync implementation | VERIFIED | Exists, 106 lines (min: 60), exports `default` (sync) and `NangoSyncLocal` type |
| `nango-integrations/index.ts` | Sync registration | VERIFIED | Contains `import './salesforce/syncs/fetch-opportunity-history.js'` as the 6th import |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `fetch-opportunity-history.ts` | `../utils.js` | `import queryEndpoint, salesforcePaginationConfig` | VERIFIED | Line 3: `import { queryEndpoint, salesforcePaginationConfig } from '../utils.js'`; both symbols actively used in `exec` |
| `fetch-opportunity-history.ts` | `../types.js` | `import sfId, sfNullableString, etc.` | VERIFIED | Line 4: `import { sfId, sfDateTime, sfDate, sfNullableString, sfCurrency, sfPercentage } from '../types.js'`; all 6 imported symbols used in schema |
| `index.ts` | `fetch-opportunity-history.ts` | sync registration import | VERIFIED | `import './salesforce/syncs/fetch-opportunity-history.js'` present at line 6 of index.ts |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| HIST-01 | 08-01-PLAN.md | Nango sync pulls OpportunityHistory records (Id, OpportunityId, StageName, Amount, CloseDate, Probability, ForecastCategoryName, CreatedDate, CreatedById) | SATISFIED | All 9 fields declared in `opportunityHistorySchema` with appropriate Zod types; SOQL field list string explicitly names all 9; TypeScript compiles cleanly |
| HIST-02 | 08-01-PLAN.md | Sync uses incremental CreatedDate filter for subsequent pulls | SATISFIED | `buildOpportunityHistoryQuery(lastSyncDate?)` appends `AND CreatedDate > {ISO}` when `nango.lastSyncDate` is defined; uses property access not method call |
| HIST-03 | 08-01-PLAN.md | Records ordered by OpportunityId, CreatedDate ASC for stage velocity derivation | SATISFIED | `ORDER BY OpportunityId, CreatedDate ASC` hardcoded via `orderBy` constant, placed unconditionally after the WHERE clause in every query |

No orphaned requirements — all three HIST-* IDs claimed in 08-01-PLAN.md frontmatter are mapped to Phase 8 in both ROADMAP.md and REQUIREMENTS.md, and all three are satisfied by the implementation.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | None found | — | — |

No TODOs, FIXMEs, placeholder returns, empty handlers, or stub implementations detected in either modified file.

---

### Human Verification Required

None. All behaviors are mechanically verifiable:

- Schema field presence: grep-confirmed
- SOQL clause presence: grep-confirmed
- TypeScript validity: `tsc --noEmit` passes with no output
- Registration wiring: grep-confirmed in index.ts

---

### Implementation Quality Notes

The following details were confirmed and are noteworthy:

1. **CloseDate type correctness.** The plan spec shows `CloseDate: sfDate` (not `sfNullableString`). The implementation uses `sfDate`, which is correct — CloseDate on OpportunityHistory is always present because it is a snapshot of the opportunity's CloseDate at the time of the change.

2. **Incremental cursor correctness.** Using `CreatedDate` (not `LastModifiedDate`) for the incremental filter is architecturally sound. OpportunityHistory records are immutable append-only audit entries. `LastModifiedDate` would not advance on historical records, making it an incorrect cursor.

3. **ORDER BY placement.** The SOQL builder correctly places `AND CreatedDate > {date}` before `ORDER BY`. Salesforce SOQL requires WHERE clauses before ORDER BY; incorrect ordering would cause a query parse error.

4. **`nango.lastSyncDate` as property.** The exec function accesses `nango.lastSyncDate` without parentheses, correctly treating it as a property of type `Date | undefined`. A method-call mistake (`nango.lastSyncDate()`) would cause a runtime TypeError.

---

## Summary

Phase 8 goal is fully achieved. The `fetch-opportunity-history.ts` sync is a complete, non-stub implementation that satisfies all three requirements:

- **HIST-01**: All 9 spec fields present in the Zod schema and SOQL SELECT list.
- **HIST-02**: CreatedDate-based incremental filter correctly applied when `nango.lastSyncDate` is set.
- **HIST-03**: `ORDER BY OpportunityId, CreatedDate ASC` embedded unconditionally for deterministic velocity-analysis ordering.

The sync is registered in `index.ts`, both utility dependencies (`utils.js`, `types.js`) are imported and used, and TypeScript compiles without errors.

---

_Verified: 2026-03-20_
_Verifier: Claude (gsd-verifier)_
