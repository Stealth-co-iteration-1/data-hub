# Phase 11: Nango Resource & Opportunity Asset - Context

**Gathered:** 2026-03-23
**Status:** Ready for planning

<domain>
## Phase Boundary

First Dagster asset validates the end-to-end pattern: NangoResource fetches pre-synced Opportunity records from Nango Records API, persists to dedicated PostgreSQL table (`salesforce_opportunities`). This establishes the pattern that Phase 12 assets will follow.

</domain>

<decisions>
## Implementation Decisions

### NangoResource Design
- Single env var configuration: `NANGO_SECRET_KEY` only (base URL defaults to https://api.nango.dev)
- Raw HTTP calls using requests/httpx — no nango Python SDK dependency
- Connection ID passed as method parameter: `nango.get_records(model='Opportunity', connection_id='xxx')`
- Connection ID sourced from `NANGO_CONNECTION_ID` environment variable at runtime
- Raise exceptions on API errors — let Dagster handle retry/failure naturally
- NangoResource handles pagination internally — `get_records()` returns all records by following cursor

### Table Schema
- Raw JSONB storage: single `data` column with full Nango record
- Dagster-managed DDL: asset creates table with `CREATE TABLE IF NOT EXISTS` at materialization
- Tables live in `public` schema (same as data-hub tables, separate from 'dagster' metadata schema)
- Columns: `salesforce_id` + `connection_id` (composite PK), `data` (JSONB), `synced_at` (timestamp)
- Multi-tenant ready from the start

### Idempotency Strategy
- DELETE + INSERT in transaction: `DELETE WHERE connection_id=X`, then INSERT all records
- Atomic operation handles removed records correctly
- Batch inserts using executemany() or VALUES list for performance

### Record Fetching
- Model name hardcoded per asset: Opportunity asset fetches model='Opportunity'
- Store raw JSON exactly as Nango returns — no transformation or validation
- Validation deferred to query time

### Claude's Discretion
- HTTP library choice (requests vs httpx)
- Exact pagination cursor handling
- Batch size for inserts
- Error message formatting

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Nango Records API
- Nango API docs: GET /records endpoint for fetching synced records
- Authentication: Bearer token using Secret Key

### Existing Codebase
- `dagster_pipelines/definitions.py` — Current Definitions with PostgresResource pattern
- `dagster_pipelines/resources/postgres.py` — PostgresResource lifecycle pattern to follow
- `nango-integrations/salesforce/syncs/fetch-opportunities.ts` — TypeScript sync that populates Nango Records (for schema reference)
- `nango-integrations/salesforce/types.ts` — Zod schemas defining Salesforce field types

### Phase 10 Context
- `.planning/phases/10-dagster-infrastructure/10-CONTEXT.md` — EnvVar pattern, package structure decisions

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `dagster_pipelines/resources/postgres.py`: PostgresResource with `yield_for_execution` lifecycle — NangoResource should follow same pattern
- `psycopg2` already available — use for database writes

### Established Patterns
- `dg.EnvVar("...")` for all resource configuration
- `dg.ConfigurableResource` base class for resources
- `dg.MaterializeResult` with metadata dict for observability

### Integration Points
- `dagster_pipelines/definitions.py` — register NangoResource and Opportunity asset
- Same PostgreSQL database, public schema for asset tables
- Nango Records API: GET https://api.nango.dev/records?model=Opportunity&connection_id=xxx

</code_context>

<specifics>
## Specific Ideas

- Table DDL should use `salesforce_id TEXT` (not INTEGER) since Salesforce IDs are 18-char strings
- `synced_at` should be set to `NOW()` at insert time, not extracted from record
- Remove ping_database asset after Opportunity asset proves the pattern works

</specifics>

<deferred>
## Deferred Ideas

- Multi-connection partitioning (SCHED-02) — schema supports it, scheduling deferred to v0.4
- Incremental loading (ADV-01) — full refresh first, cursor-based loading later
- nango Python SDK — may revisit if raw HTTP becomes unwieldy

</deferred>

---

*Phase: 11-nango-resource-opportunity-asset*
*Context gathered: 2026-03-23*
