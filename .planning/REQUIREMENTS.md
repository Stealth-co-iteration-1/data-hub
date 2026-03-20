# Requirements: data-hub

**Defined:** 2026-03-20
**Core Value:** Data from connected integrations flows reliably into the platform with strict validation — if it's in the database, it's valid.

## v0.2.0 Requirements

Requirements for v0.2.0 milestone: Salesforce Revenue Reporting Syncs.

### Opportunity Sync

- [ ] **OPPT-01**: Nango sync pulls Opportunity records with all spec fields (Id, Name, Amount, StageName, IsClosed, IsWon, CloseDate, CreatedDate, LastModifiedDate, ForecastCategoryName, Probability, Type, LeadSource, OwnerId)
- [ ] **OPPT-02**: Opportunity sync includes parent Account fields (Account.Name, Account.Industry, Account.AnnualRevenue)
- [ ] **OPPT-03**: Opportunity sync includes Owner fields (Owner.Name, Owner.Email)
- [ ] **OPPT-04**: Opportunity sync includes nested OpportunityContactRoles with Contact.Email as join key
- [ ] **OPPT-05**: Sync supports incremental pulls via LastModifiedDate filter

### OpportunityHistory Sync

- [ ] **HIST-01**: Nango sync pulls OpportunityHistory records (Id, OpportunityId, StageName, Amount, CloseDate, Probability, ForecastCategoryName, CreatedDate, CreatedById)
- [ ] **HIST-02**: Sync uses incremental CreatedDate filter for subsequent pulls
- [ ] **HIST-03**: Records ordered by OpportunityId, CreatedDate ASC for stage velocity derivation

### Task Sync (Conditional)

- [ ] **TASK-01**: Nango sync pulls Task records with spec fields (Id, Subject, Status, ActivityDate, CreatedDate, WhoId, Who.Email, WhatId, OwnerId, Owner.Email, Type, CallType, CallDurationInSeconds, CallDisposition, TaskSubtype)
- [ ] **TASK-02**: Sync filters by ActivityDate range for manageable result sets
- [ ] **TASK-03**: WhoId/WhatId preserved for downstream join resolution

### Event Sync (Conditional)

- [ ] **EVNT-01**: Nango sync pulls Event records with spec fields (Id, Subject, StartDateTime, EndDateTime, DurationInMinutes, ActivityDate, CreatedDate, WhoId, Who.Email, WhatId, OwnerId, Owner.Email, Type, EventSubtype)
- [ ] **EVNT-02**: Sync filters by StartDateTime range for manageable result sets
- [ ] **EVNT-03**: WhoId/WhatId preserved for downstream join resolution

### Infrastructure

- [ ] **INFR-01**: Salesforce syncs use Nango's createSync pattern with Zod schemas
- [ ] **INFR-02**: Pagination follows Salesforce REST API nextRecordsUrl pattern
- [ ] **INFR-03**: Sync models match data-hub schema validation expectations

## Future Requirements

Deferred to future milestone. Tracked but not in current roadmap.

### Bulk API

- **BULK-01**: Switch to Bulk API 2.0 for OpportunityHistory when row count exceeds 50,000
- **BULK-02**: Switch to Bulk API 2.0 for Task/Event when row count exceeds 50,000

### Attribution

- **ATTR-01**: Join key chain resolution (Task.Who.Email → OpportunityContactRole.Contact.Email → Opportunity.Id)
- **ATTR-02**: Activity-to-deal attribution with date range filtering

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Attribution calculation | Downstream in Staq data warehouse, not in sync layer |
| Stage velocity derivation | Calculation happens in data warehouse after sync |
| Custom field discovery | Spec defines fixed field set; custom fields are org-specific |
| Real-time sync | Polling-based sync per Nango pattern; no websocket push |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| OPPT-01 | TBD | Pending |
| OPPT-02 | TBD | Pending |
| OPPT-03 | TBD | Pending |
| OPPT-04 | TBD | Pending |
| OPPT-05 | TBD | Pending |
| HIST-01 | TBD | Pending |
| HIST-02 | TBD | Pending |
| HIST-03 | TBD | Pending |
| TASK-01 | TBD | Pending |
| TASK-02 | TBD | Pending |
| TASK-03 | TBD | Pending |
| EVNT-01 | TBD | Pending |
| EVNT-02 | TBD | Pending |
| EVNT-03 | TBD | Pending |
| INFR-01 | TBD | Pending |
| INFR-02 | TBD | Pending |
| INFR-03 | TBD | Pending |

**Coverage:**
- v0.2.0 requirements: 17 total
- Mapped to phases: 0
- Unmapped: 17 ⚠️

---
*Requirements defined: 2026-03-20*
*Last updated: 2026-03-20 after initial definition*
