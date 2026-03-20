---
phase: 07-opportunity-sync
verified: 2026-03-20T00:00:00Z
status: passed
score: 6/6 must-haves verified
re_verification: false
---

# Phase 7: Opportunity Sync Verification Report

**Phase Goal:** Complete Opportunity records with nested relationships flowing to data-hub
**Verified:** 2026-03-20
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Opportunity sync pulls records with all 14 spec fields (Id, Name, Amount, StageName, IsClosed, IsWon, CloseDate, CreatedDate, LastModifiedDate, ForecastCategoryName, Probability, Type, LeadSource, OwnerId) | VERIFIED | All 14 fields present in `opportunitySchema` (lines 48-61 of fetch-opportunities.ts); all included in `OPPORTUNITY_SOQL_FIELDS` constant (line 86) |
| 2 | Each Opportunity includes parent Account fields (Name, Industry, AnnualRevenue) denormalized via relationship query | VERIFIED | `accountSchema` defined with all 3 fields (lines 11-15); `Account.Name, Account.Industry, Account.AnnualRevenue` in SOQL field list (line 87); `Account: z.union([accountSchema, z.null()])` in main schema (line 64) |
| 3 | Each Opportunity includes Owner fields (Name, Email) denormalized via relationship query | VERIFIED | `ownerSchema` with `Name` and `Email` (lines 18-21); `Owner.Name, Owner.Email` in SOQL field list (line 88); `Owner: ownerSchema` in main schema (line 67) |
| 4 | Each Opportunity includes OpportunityContactRoles array with Contact.Email for join key resolution | VERIFIED | `opportunityContactRoleSchema` with `Id`, `ContactId`, `Role`, `IsPrimary`, `Contact` (lines 29-35); subquery `(SELECT Id, ContactId, Role, IsPrimary, Contact.Email FROM OpportunityContactRoles)` in SOQL (line 89); `OpportunityContactRoles` field in main schema (lines 71-74) |
| 5 | Incremental sync filters by LastModifiedDate when lastSyncDate is available | VERIFIED | `buildOpportunityQuery(lastSyncDate?: Date)` at line 102 appends `WHERE LastModifiedDate > {ISO}` when `lastSyncDate !== undefined`; called with `nango.lastSyncDate` (property, not method) at line 129 |
| 6 | Sync is registered in index.ts and included in nango compile output | VERIFIED | `import './salesforce/syncs/fetch-opportunities.js'` present at line 5 of index.ts; 3 commits confirm the registration (d0db23e) |

**Score:** 6/6 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `nango-integrations/salesforce/syncs/fetch-opportunities.ts` | Nango sync for Salesforce Opportunities with nested relationships | VERIFIED | 152 lines (above 80-line minimum); contains `createSync`, `opportunitySchema`, `OpportunityContactRole`, `nango.paginate`, `nango.batchSave`; exports `NangoSyncLocal` and `default sync` |
| `nango-integrations/index.ts` | Sync registration entry point | VERIFIED | Contains `import './salesforce/syncs/fetch-opportunities.js'` at line 5; no duplicate imports |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `fetch-opportunities.ts` | `../utils.js` | `import { queryEndpoint, salesforcePaginationConfig }` | VERIFIED | Import present at line 3; both symbols used at lines 132-133 in `nango.paginate` call |
| `fetch-opportunities.ts` | `../types.js` | `import { sfId, sfDateTime, sfDate, sfNullableString, sfNullableNumber, sfCurrency, sfPercentage }` | VERIFIED | Import present at line 4; all 7 symbols used in schema definitions |
| `index.ts` | `fetch-opportunities.ts` | `import './salesforce/syncs/fetch-opportunities.js'` | VERIFIED | Present at index.ts line 5 |
| `fetch-opportunities.ts` SOQL | Salesforce REST API | `SELECT ... FROM Opportunity WHERE LastModifiedDate` | VERIFIED | `buildOpportunityQuery` at line 103 constructs `SELECT ${OPPORTUNITY_SOQL_FIELDS} FROM Opportunity`; WHERE clause appended at line 105 |

**Plan deviation (correctly handled):** The PLAN specified `import { buildQuery, queryEndpoint, salesforcePaginationConfig }` but `buildQuery` was intentionally omitted because it does not support relationship field traversal. The SUMMARY documents this as an auto-fixed bug. The replacement `buildOpportunityQuery` function covers the same purpose and is wired correctly. This is not a gap.

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| OPPT-01 | 07-01-PLAN.md | Nango sync pulls Opportunity records with all 14 spec fields | SATISFIED | All 14 fields present in `opportunitySchema` and in `OPPORTUNITY_SOQL_FIELDS` |
| OPPT-02 | 07-01-PLAN.md | Opportunity sync includes parent Account fields (Account.Name, Account.Industry, Account.AnnualRevenue) | SATISFIED | `accountSchema` defined; fields in SOQL; nested via `Account: z.union([accountSchema, z.null()])` |
| OPPT-03 | 07-01-PLAN.md | Opportunity sync includes Owner fields (Owner.Name, Owner.Email) | SATISFIED | `ownerSchema` defined; fields in SOQL; nested via `Owner: ownerSchema` |
| OPPT-04 | 07-01-PLAN.md | Opportunity sync includes nested OpportunityContactRoles with Contact.Email as join key | SATISFIED | `opportunityContactRoleSchema` with `Contact: contactSchema`; subquery in SOQL; schema field defined |
| OPPT-05 | 07-01-PLAN.md | Sync supports incremental pulls via LastModifiedDate filter | SATISFIED | `buildOpportunityQuery` appends WHERE clause; `nango.lastSyncDate` property passed as argument |

No orphaned requirements. REQUIREMENTS.md marks OPPT-01 through OPPT-05 as checked (`[x]`). All 5 requirements are fully accounted for by 07-01-PLAN.md.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | None found | — | — |

No TODO, FIXME, placeholder comments, empty returns, or stub implementations detected.

---

### Human Verification Required

None. All aspects of the sync implementation are verifiable statically:

- Schema field coverage is verifiable by grep.
- SOQL structure is verifiable by inspection.
- Incremental filter logic is deterministic and fully visible in source.
- Registration wiring is a direct import statement.

The only runtime behavior — whether Nango actually executes the sync against a live Salesforce org — is outside the scope of this phase's deliverable (a correctly structured sync file). That is an integration/deployment concern.

---

### Implementation Notes

**id aliasing decision (documented in SUMMARY):** Nango's `ZodModel` requires a lowercase `id: z.ZodString` field on every model used with `batchSave`. Salesforce returns `Id` (capital I). The implementation adds `id: sfId` to `opportunitySchema` and spreads `id: raw['Id']` at parse time (line 140). This is correct behavior and does not indicate a defect.

**nango.lastSyncDate as property:** The PLAN template incorrectly showed `await nango.lastSyncDate()` as a function call. The implementation correctly accesses it as a property (`nango.lastSyncDate`, type `Date | undefined`). This was caught and fixed during TypeScript compilation.

---

### Gaps Summary

No gaps. All 6 observable truths verified, both artifacts pass all three levels (exists, substantive, wired), all 4 key links confirmed, all 5 requirements satisfied. The implementation is 152 lines — within the expected 100-150 line range noted in the plan's success criteria.

---

_Verified: 2026-03-20_
_Verifier: Claude (gsd-verifier)_
