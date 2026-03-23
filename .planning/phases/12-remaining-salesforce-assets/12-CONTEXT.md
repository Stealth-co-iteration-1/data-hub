# Phase 12: Remaining Salesforce Assets - Context

**Gathered:** 2026-03-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Three additional Salesforce assets (OpportunityHistory, Task, Event) following the exact pattern established by the Opportunity asset in Phase 11. No new patterns — pure replication with different model names and table names.

</domain>

<decisions>
## Implementation Decisions

**All decisions inherited from Phase 11. No new decisions required.**

### Inherited from Phase 11

#### NangoResource (already built)
- `get_records(model, connection_id)` with pagination
- `NANGO_SECRET_KEY` env var for auth
- `NANGO_CONNECTION_ID` env var for connection

#### Table Schema (repeat for each model)
- Raw JSONB storage: `salesforce_id` + `connection_id` (composite PK), `data` (JSONB), `synced_at`
- Dagster-managed DDL: `CREATE TABLE IF NOT EXISTS` at materialization
- Tables in `public` schema

#### Idempotency (same pattern)
- DELETE + INSERT in transaction per connection_id
- Batch inserts using `execute_values`

#### Observability (same pattern)
- `MaterializeResult` with `dagster/row_count` metadata

### Model-Specific Details

| Model | Nango Model Name | Table Name | Asset Name |
|-------|------------------|------------|------------|
| OpportunityHistory | OpportunityHistory | `salesforce_opportunity_history` | `salesforce_opportunity_history` |
| Task | Task | `salesforce_tasks` | `salesforce_tasks` |
| Event | Event | `salesforce_events` | `salesforce_events` |

### Claude's Discretion
- File organization (one file per asset vs combined)
- Import organization in `__init__.py`
- Order of asset implementation

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 11 Reference Implementation
- `dagster_pipelines/assets/salesforce/opportunity.py` — **THE pattern to follow exactly**
- `dagster_pipelines/resources/nango.py` — NangoResource (use as-is)
- `dagster_pipelines/resources/postgres.py` — PostgresResource (use as-is)
- `dagster_pipelines/definitions.py` — Registration pattern

### Phase 11 Context
- `.planning/phases/11-nango-resource-opportunity-asset/11-CONTEXT.md` — All design decisions

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `dagster_pipelines/resources/nango.py`: NangoResource — use directly, no changes needed
- `dagster_pipelines/resources/postgres.py`: PostgresResource — use directly, no changes needed
- `dagster_pipelines/assets/salesforce/opportunity.py`: **Copy and adapt** for each model

### Established Patterns
- Asset function signature: `def asset_name(nango: NangoResource, postgres_db: PostgresResource)`
- DDL at top of file as constant
- `os.environ["NANGO_CONNECTION_ID"]` for connection
- DELETE then INSERT with `execute_values`
- Return `MaterializeResult` with `dagster/row_count`

### Integration Points
- `dagster_pipelines/definitions.py` — add new assets to `assets=[]` list
- `dagster_pipelines/assets/salesforce/__init__.py` — export new assets

</code_context>

<specifics>
## Specific Ideas

- Each asset should be in its own file (like `opportunity.py`) for clarity
- Follow exact naming: `salesforce_opportunity_history`, `salesforce_tasks`, `salesforce_events`
- Nango model names match TypeScript sync names: `OpportunityHistory`, `Task`, `Event`

</specifics>

<deferred>
## Deferred Ideas

None — Phase 12 completes v0.3 milestone scope

</deferred>

---

*Phase: 12-remaining-salesforce-assets*
*Context gathered: 2026-03-23*
