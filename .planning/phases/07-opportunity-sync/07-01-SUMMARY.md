---
phase: 07-opportunity-sync
plan: "01"
subsystem: nango-integrations/salesforce
tags: [salesforce, nango, sync, opportunities, zod, incremental]
dependency_graph:
  requires:
    - "nango-integrations/salesforce/utils.ts (queryEndpoint, salesforcePaginationConfig)"
    - "nango-integrations/salesforce/types.ts (sfId, sfDateTime, sfDate, sfNullableString, sfNullableNumber, sfCurrency, sfPercentage)"
  provides:
    - "nango-integrations/salesforce/syncs/fetch-opportunities.ts (Salesforce Opportunity sync with full relationship data)"
  affects:
    - "nango-integrations/index.ts (registered as 5th sync)"
    - "nango-integrations/.nango/ (compile artifacts updated)"
tech_stack:
  added: []
  patterns:
    - "createSync with incremental syncType and nango.lastSyncDate property for delta filtering"
    - "Custom SOQL builder for relationship traversal (bypasses buildQuery limitation)"
    - "Zod schemas with nested relationship objects and z.union for nullable Salesforce fields"
    - "id field mapping: Salesforce Id (capital I) aliased to Nango-required lowercase id"
key_files:
  created:
    - nango-integrations/salesforce/syncs/fetch-opportunities.ts
  modified:
    - nango-integrations/index.ts
    - nango-integrations/.nango/nango.json
    - nango-integrations/.nango/schema.json
    - nango-integrations/.nango/schema.ts
decisions:
  - "id aliasing: added lowercase `id: sfId` field to opportunitySchema alongside `Id: sfId` — Nango ZodModel requires id: ZodString as record key; Salesforce returns Id (capital I) so we spread and add id at parse time"
  - "buildQuery not used: custom buildOpportunityQuery replaces it because buildQuery does not support relationship field traversal (Account.Name, Owner.Email, subqueries)"
  - "nango.lastSyncDate is a property, not a method: used as `nango.lastSyncDate` (Date | undefined) directly, not called as a function"
metrics:
  duration_seconds: 205
  completed_date: "2026-03-20"
  tasks_completed: 3
  tasks_total: 3
  files_created: 1
  files_modified: 4
---

# Phase 07 Plan 01: Salesforce Opportunity Sync Summary

**One-liner:** Incremental Salesforce Opportunity sync with denormalized Account, Owner, and OpportunityContactRoles subquery via custom SOQL builder and Zod validation.

---

## Objective

Created `fetch-opportunities.ts` — a Nango sync that pulls complete Salesforce Opportunity records with relationship data for downstream revenue reporting and join key resolution.

---

## What Was Built

### nango-integrations/salesforce/syncs/fetch-opportunities.ts (152 lines)

A complete Nango sync implementation covering all 5 requirements:

- **OPPT-01 (14 core fields):** `Id`, `Name`, `Amount`, `StageName`, `IsClosed`, `IsWon`, `CloseDate`, `CreatedDate`, `LastModifiedDate`, `ForecastCategoryName`, `Probability`, `Type`, `LeadSource`, `OwnerId` — all validated via Zod schemas
- **OPPT-02 (Account fields):** `Account.Name`, `Account.Industry`, `Account.AnnualRevenue` — denormalized as `accountSchema` nested object
- **OPPT-03 (Owner fields):** `Owner.Name`, `Owner.Email` — denormalized as `ownerSchema` nested object
- **OPPT-04 (OpportunityContactRoles):** Subquery `(SELECT Id, ContactId, Role, IsPrimary, Contact.Email FROM OpportunityContactRoles)` with `opportunityContactRoleSchema` for join key resolution
- **OPPT-05 (Incremental sync):** `buildOpportunityQuery(nango.lastSyncDate)` appends `WHERE LastModifiedDate > {ISO}` when a prior sync date is available

### nango-integrations/index.ts (modified)

Added `import './salesforce/syncs/fetch-opportunities.js'` — the sync is now registered with Nango and included in `nango compile` output.

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed unused `buildQuery` import**
- **Found during:** Task 2 TypeScript compile
- **Issue:** Plan specified `import { buildQuery, queryEndpoint, salesforcePaginationConfig }` but `buildQuery` is not used (we use custom `buildOpportunityQuery` instead)
- **Fix:** Removed `buildQuery` from import to eliminate `TS6133: declared but its value is never read`
- **Files modified:** nango-integrations/salesforce/syncs/fetch-opportunities.ts

**2. [Rule 1 - Bug] Removed unused `sfNullableBoolean` import**
- **Found during:** Task 2 TypeScript compile
- **Issue:** Plan's import line included `sfNullableBoolean` but the schema does not use it
- **Fix:** Removed from import statement
- **Files modified:** nango-integrations/salesforce/syncs/fetch-opportunities.ts

**3. [Rule 1 - Bug] Fixed `nango.lastSyncDate` usage**
- **Found during:** Task 2 TypeScript compile
- **Issue:** Plan template showed `await nango.lastSyncDate()` (function call) but Nango SDK exposes it as a property `lastSyncDate?: Date` on `NangoSyncBase`
- **Fix:** Changed to `nango.lastSyncDate` (property access)
- **Files modified:** nango-integrations/salesforce/syncs/fetch-opportunities.ts

**4. [Rule 2 - Missing critical functionality] Added `id` field mapping for Nango `ZodModel` constraint**
- **Found during:** Task 2 TypeScript compile
- **Issue:** Nango's `ZodModel` type (`@nangohq/runner-sdk`) requires `id: z.ZodString` on every model schema. Salesforce returns `Id` (capital I), so `batchSave` would fail type-check and runtime validation without a lowercase `id` field
- **Fix:** Added `id: sfId` to `opportunitySchema` and mapped it from `raw['Id']` at parse time in `exec`
- **Files modified:** nango-integrations/salesforce/syncs/fetch-opportunities.ts

---

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 128ad18 | feat(07-01): define Opportunity Zod schemas and SOQL field list |
| 2 | f2867ab | feat(07-01): implement sync execution with incremental SOQL and pagination |
| 3 | d0db23e | feat(07-01): register fetch-opportunities sync in index.ts |

---

## Self-Check: PASSED
