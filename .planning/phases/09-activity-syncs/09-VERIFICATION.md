---
phase: 09-activity-syncs
verified: 2026-03-20T13:00:00Z
status: passed
score: 10/10 must-haves verified
re_verification: false
---

# Phase 9: Activity Syncs Verification Report

**Phase Goal:** Sales activities (emails, calls, meetings) flowing with relationship keys preserved
**Verified:** 2026-03-20T13:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

All must-haves drawn from plan frontmatter for both 09-01 (Task sync) and 09-02 (Event sync).

| #  | Truth                                                                   | Status     | Evidence                                                                          |
|----|-------------------------------------------------------------------------|------------|-----------------------------------------------------------------------------------|
| 1  | Task sync pulls all spec fields including call tracking fields           | VERIFIED   | taskSchema includes Subject, Status, ActivityDate, CreatedDate, Type, TaskSubtype, CallType, CallDurationInSeconds, CallDisposition (lines 33-55)   |
| 2  | Who.Email included via SOQL relationship query (Task) for join key      | VERIFIED   | TASK_SOQL_FIELDS string contains `Who.Email` (line 69); whoSchema z.object({Email}) at line 11 |
| 3  | Owner.Email included via SOQL relationship query (Task) for rep attr    | VERIFIED   | TASK_SOQL_FIELDS string contains `Owner.Name, Owner.Email` (line 69); ownerSchema at line 16     |
| 4  | Task sync filters by ActivityDate for incremental pulls                 | VERIFIED   | buildTaskQuery adds `AND ActivityDate >= ${lastSyncDate.toISOString().split('T')[0]}` (line 91)  |
| 5  | WhoId and WhatId preserved as raw polymorphic IDs (Task)                | VERIFIED   | `WhoId: z.union([sfId, z.null()])` and `WhatId: z.union([sfId, z.null()])` (lines 40-41)        |
| 6  | Event sync pulls all spec fields including duration and subtype         | VERIFIED   | eventSchema includes Subject, StartDateTime, EndDateTime, DurationInMinutes, ActivityDate, CreatedDate, Type, EventSubtype (lines 33-52) |
| 7  | Who.Email included via SOQL relationship query (Event) for join key     | VERIFIED   | EVENT_SOQL_FIELDS contains `Who.Email` (line 64); whoSchema at line 11           |
| 8  | Owner.Email included via SOQL relationship query (Event) for rep attr   | VERIFIED   | EVENT_SOQL_FIELDS contains `Owner.Name, Owner.Email` (line 64); ownerSchema at line 16          |
| 9  | Event sync filters by StartDateTime for incremental pulls               | VERIFIED   | buildEventQuery adds `AND StartDateTime >= ${lastSyncDate.toISOString()}` (line 86)              |
| 10 | WhoId and WhatId preserved as raw polymorphic IDs (Event)               | VERIFIED   | `WhoId: z.union([sfId, z.null()])` and `WhatId: z.union([sfId, z.null()])` (lines 42-43)        |

**Score:** 10/10 truths verified

---

### Required Artifacts

| Artifact                                                   | Expected                                       | Status     | Details                                            |
|------------------------------------------------------------|------------------------------------------------|------------|----------------------------------------------------|
| `nango-integrations/salesforce/syncs/fetch-tasks.ts`       | Task sync with relationship denormalization    | VERIFIED   | 137 lines (min 80), exports NangoSyncLocal + default sync |
| `nango-integrations/salesforce/syncs/fetch-events.ts`      | Event sync with relationship denormalization   | VERIFIED   | 132 lines (min 80), exports NangoSyncLocal + default sync |
| `nango-integrations/index.ts`                              | Sync registration for both syncs               | VERIFIED   | Lines 7-8: `import './salesforce/syncs/fetch-tasks.js'` and `import './salesforce/syncs/fetch-events.js'` |

---

### Key Link Verification

| From                    | To                          | Via                                        | Status   | Details                                                       |
|-------------------------|-----------------------------|--------------------------------------------|----------|---------------------------------------------------------------|
| `fetch-tasks.ts`        | `salesforce/utils.ts`       | `import { queryEndpoint, salesforcePaginationConfig }` | WIRED    | Line 3: `import { queryEndpoint, salesforcePaginationConfig } from '../utils.js'`; both used at lines 118-119 |
| `fetch-tasks.ts`        | `salesforce/types.ts`       | `import { sfId, ... } from '../types.js'`  | WIRED    | Line 4: import present; sfId used at lines 30, 33, 40-42; sfNullableString/Number used throughout schema |
| `fetch-events.ts`       | `salesforce/utils.ts`       | `import { queryEndpoint, salesforcePaginationConfig }` | WIRED    | Line 3: `import { queryEndpoint, salesforcePaginationConfig } from '../utils.js'`; both used at lines 113-114 |
| `fetch-events.ts`       | `salesforce/types.ts`       | `import { sfId, ... } from '../types.js'`  | WIRED    | Line 4: import present; sfId used at lines 30, 33, 42-44; sfNullableString/Number used throughout schema |

---

### Requirements Coverage

| Requirement | Source Plan  | Description                                                                                                   | Status     | Evidence                                                       |
|-------------|--------------|---------------------------------------------------------------------------------------------------------------|------------|----------------------------------------------------------------|
| TASK-01     | 09-01-PLAN   | Task sync pulls spec fields (Id, Subject, Status, ActivityDate, CreatedDate, WhoId, Who.Email, WhatId, OwnerId, Owner.Email, Type, CallType, CallDurationInSeconds, CallDisposition, TaskSubtype) | SATISFIED  | All 15 fields present in taskSchema and TASK_SOQL_FIELDS       |
| TASK-02     | 09-01-PLAN   | Sync filters by ActivityDate range                                                                            | SATISFIED  | buildTaskQuery: `AND ActivityDate >= YYYY-MM-DD` at line 91    |
| TASK-03     | 09-01-PLAN   | WhoId/WhatId preserved for downstream join                                                                    | SATISFIED  | `z.union([sfId, z.null()])` for both fields, lines 40-41       |
| EVNT-01     | 09-02-PLAN   | Event sync pulls spec fields (Id, Subject, StartDateTime, EndDateTime, DurationInMinutes, ActivityDate, CreatedDate, WhoId, Who.Email, WhatId, OwnerId, Owner.Email, Type, EventSubtype)        | SATISFIED  | All 14 fields present in eventSchema and EVENT_SOQL_FIELDS     |
| EVNT-02     | 09-02-PLAN   | Sync filters by StartDateTime range                                                                           | SATISFIED  | buildEventQuery: `AND StartDateTime >= ISO-string` at line 86  |
| EVNT-03     | 09-02-PLAN   | WhoId/WhatId preserved for downstream join                                                                    | SATISFIED  | `z.union([sfId, z.null()])` for both fields, lines 42-43       |

No orphaned requirements — all 6 IDs (TASK-01 through EVNT-03) are claimed by plans and verified.

---

### Anti-Patterns Found

None detected.

Scanned both sync files for: TODO/FIXME/HACK/PLACEHOLDER, `return null`, `return {}`, `return []`, empty handlers, console.log-only implementations. Zero matches in either file.

---

### Human Verification Required

None required for this phase. All critical behaviors are statically verifiable:

- Field presence verified via schema inspection
- SOQL filter logic verified via grep (no branching edge cases)
- Registration verified via index.ts import lines
- Commits cited in summaries confirmed present in git log (23bd909, b03fbc5, ae870e4, 42b9bca)

Actual Nango deployment and live Salesforce API connectivity are explicitly out of scope for static verification.

---

### Summary

Phase 9 goal is fully achieved. Both sync files exist with substantive implementations (130+ lines each), are correctly wired to the shared utils and types infrastructure, and are registered in index.ts. All six requirements (TASK-01 through EVNT-03) are satisfied with direct code evidence.

Key design decisions confirmed in code:
- ActivityDate filter extracts date-only portion (`.split('T')[0]`) — correct for Salesforce DATE type
- StartDateTime filter uses full ISO string — correct for Salesforce DATETIME type
- Both filters use `>=` (not `>`) — boundary-inclusive as specified
- WhoId/WhatId typed as `z.union([sfId, z.null()])` not `sfNullableString` — preserves 18-char ID length constraint

No gaps. No blockers.

---

_Verified: 2026-03-20T13:00:00Z_
_Verifier: Claude (gsd-verifier)_
