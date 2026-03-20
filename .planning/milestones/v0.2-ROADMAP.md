# Roadmap: data-hub v0.2.0

**Milestone:** v0.2.0 Salesforce Revenue Reporting Syncs
**Created:** 2026-03-19
**Granularity:** coarse
**Phases:** 4 (numbered 6-9, continuing from v0.1.0)

## Goal

Create Nango sync scripts that pull Salesforce revenue data per the Engineering Data Spec and forward to data-hub webhook.

## Phases

- [x] **Phase 6: Salesforce Sync Infrastructure** - Shared patterns, Zod schemas, pagination for all Salesforce syncs (completed 2026-03-20)
- [x] **Phase 7: Opportunity Sync** - Primary dataset with Account, Owner, and nested ContactRoles (completed 2026-03-20)
- [x] **Phase 8: OpportunityHistory Sync** - Stage change tracking for velocity analysis (completed 2026-03-20)
- [x] **Phase 9: Activity Syncs** - Tasks (emails/calls) and Events (meetings) with join keys (completed 2026-03-20)

## Phase Details

### Phase 6: Salesforce Sync Infrastructure
**Goal**: Shared sync infrastructure ready to support all Salesforce sync implementations
**Depends on**: Nothing (foundation phase)
**Requirements**: INFR-01, INFR-02, INFR-03
**Success Criteria** (what must be TRUE):
  1. Nango createSync pattern scaffolded with TypeScript and Zod validation
  2. Pagination utility handles Salesforce REST API nextRecordsUrl pattern across any query
  3. Base Zod schemas defined that match data-hub schema validation expectations
  4. Sync development environment configured (nango-integrations/salesforce/syncs/)
**Plans:** 1/1 plans complete
Plans:
- [x] 06-01-PLAN.md - Shared utilities (buildQuery, pagination config) and Zod schema helpers

### Phase 7: Opportunity Sync
**Goal**: Complete Opportunity records with nested relationships flowing to data-hub
**Depends on**: Phase 6
**Requirements**: OPPT-01, OPPT-02, OPPT-03, OPPT-04, OPPT-05
**Success Criteria** (what must be TRUE):
  1. Opportunity records include all spec fields (Id, Name, Amount, StageName, IsClosed, IsWon, CloseDate, etc.)
  2. Parent Account fields (Name, Industry, AnnualRevenue) denormalized on each Opportunity
  3. Owner fields (Name, Email) denormalized on each Opportunity
  4. OpportunityContactRoles with Contact.Email nested as array for join key resolution
  5. Incremental sync pulls only records modified since last sync via LastModifiedDate
**Plans:** 1/1 plans complete
Plans:
- [x] 07-01-PLAN.md - Opportunity sync with Account, Owner, and OpportunityContactRoles relationships

### Phase 8: OpportunityHistory Sync
**Goal**: Stage change history records available for downstream velocity analysis
**Depends on**: Phase 6
**Requirements**: HIST-01, HIST-02, HIST-03
**Success Criteria** (what must be TRUE):
  1. OpportunityHistory records include all spec fields (Id, OpportunityId, StageName, Amount, CloseDate, etc.)
  2. Incremental sync uses CreatedDate filter for subsequent pulls
  3. Records ordered by OpportunityId, CreatedDate ASC enabling stage velocity derivation
**Plans:** 1/1 plans complete
Plans:
- [x] 08-01-PLAN.md - OpportunityHistory sync with CreatedDate incremental filter and velocity ordering

### Phase 9: Activity Syncs
**Goal**: Sales activities (emails, calls, meetings) flowing with relationship keys preserved
**Depends on**: Phase 6
**Requirements**: TASK-01, TASK-02, TASK-03, EVNT-01, EVNT-02, EVNT-03
**Success Criteria** (what must be TRUE):
  1. Task records include all spec fields (Id, Subject, Status, CallType, CallDuration, TaskSubtype, etc.)
  2. Event records include all spec fields (Id, Subject, StartDateTime, DurationInMinutes, EventSubtype, etc.)
  3. Both syncs filter by date range (ActivityDate/StartDateTime) for manageable result sets
  4. WhoId/WhatId preserved on both record types for downstream join resolution
  5. Owner.Email included on both record types for rep attribution
**Plans:** 2/2 plans complete
Plans:
- [ ] 09-01-PLAN.md - Task sync with Who/Owner relationships and ActivityDate filter
- [ ] 09-02-PLAN.md - Event sync with Who/Owner relationships and StartDateTime filter

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 6. Salesforce Sync Infrastructure | 1/1 | Complete   | 2026-03-20 |
| 7. Opportunity Sync | 1/1 | Complete   | 2026-03-20 |
| 8. OpportunityHistory Sync | 1/1 | Complete   | 2026-03-20 |
| 9. Activity Syncs | 2/2 | Complete   | 2026-03-20 |

## Coverage

| Requirement | Phase | Verified |
|-------------|-------|----------|
| INFR-01 | Phase 6 | - |
| INFR-02 | Phase 6 | - |
| INFR-03 | Phase 6 | - |
| OPPT-01 | Phase 7 | - |
| OPPT-02 | Phase 7 | - |
| OPPT-03 | Phase 7 | - |
| OPPT-04 | Phase 7 | - |
| OPPT-05 | Phase 7 | - |
| HIST-01 | Phase 8 | - |
| HIST-02 | Phase 8 | - |
| HIST-03 | Phase 8 | - |
| TASK-01 | Phase 9 | - |
| TASK-02 | Phase 9 | - |
| TASK-03 | Phase 9 | - |
| EVNT-01 | Phase 9 | - |
| EVNT-02 | Phase 9 | - |
| EVNT-03 | Phase 9 | - |

**Total:** 17/17 requirements mapped

## Dependencies

```
Phase 6 (Infrastructure)
    |
    +---> Phase 7 (Opportunities)
    |
    +---> Phase 8 (OpportunityHistory)
    |
    +---> Phase 9 (Activities)
```

Phases 7, 8, and 9 can execute in parallel after Phase 6 completes.

---
*Created: 2026-03-19*
*Last updated: 2026-03-20*
