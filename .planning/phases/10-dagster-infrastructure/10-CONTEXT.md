# Phase 10: Dagster Infrastructure - Context

**Gathered:** 2026-03-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Dagster project scaffold that boots locally with PostgreSQL storage. This phase establishes the infrastructure foundation — directory structure, configuration files, and a placeholder asset to verify the end-to-end setup works. Real Salesforce assets are Phase 11+.

</domain>

<decisions>
## Implementation Decisions

### Directory Structure
- Dagster code lives in `dagster/` at project root (not inside `src/`)
- Nested internal structure: `definitions.py` + `assets/` + `resources/`
- Clear process boundary from existing hexagonal architecture

### PostgreSQL Storage
- Dagster metadata stored in same database, separate schema (`dagster`)
- Schema created manually: `CREATE SCHEMA dagster;`
- Avoids Alembic conflicts with existing data-hub migrations

### Environment Configuration
- Dagster env vars documented in `dagster/.env.example` (separate from root `.env.example`)
- Separate `DAGSTER_DATABASE_URL` env var (not shared with FastAPI's `DATABASE_URL`)
- All resource config uses `dg.EnvVar(...)` pattern (not `os.getenv`)

### Port Assignment
- Dagster webserver runs on port 3000 (Dagster default)
- FastAPI continues on port 8000
- No port conflicts in local dev

### Placeholder Asset
- Include `ping_database` asset to verify PostgresResource works end-to-end
- Validates definitions.py loads and materializes correctly
- Removed after Phase 11 introduces real assets

### PyPI Dependencies
- Add `dagster`, `dagster-postgres`, `dagster-webserver` to main `[project.dependencies]`
- All as main dependencies (not optional or dev-only)

### Local Dev Workflow
- Developers run `dagster dev` directly from project root
- No wrapper script or Makefile target needed
- workspace.yaml points to dagster package

### Claude's Discretion
- Exact dagster.yaml configuration structure
- workspace.yaml format details
- PostgresResource implementation approach

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Dagster Setup
- `.planning/research/SUMMARY.md` — Stack recommendations, architecture approach, critical pitfalls
- `.planning/research/ARCHITECTURE.md` — Component structure, resource patterns, process separation

### Existing Codebase
- `pyproject.toml` — Current dependencies, Python version, tool configs
- `src/config/settings.py` — Existing env var patterns (for consistency)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/config/settings.py`: Pydantic Settings pattern — could inform Dagster resource config style
- `psycopg2-binary` already in pyproject.toml — sync PostgreSQL driver ready

### Established Patterns
- Hexagonal architecture in `src/` — Dagster stays outside this boundary
- ENV-based configuration — Dagster follows same pattern with `EnvVar(...)`

### Integration Points
- Same PostgreSQL database, different schema (`dagster`)
- Dagster uses `psycopg2` (sync), FastAPI uses `asyncpg` (async)
- No shared Python code between processes

</code_context>

<specifics>
## Specific Ideas

- ping_database asset should verify the PostgresResource can connect and query
- Research warned about SQLite lock corruption — PostgreSQL storage from day one is non-negotiable

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 10-dagster-infrastructure*
*Context gathered: 2026-03-23*
