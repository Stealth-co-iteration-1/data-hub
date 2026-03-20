# Project Research Summary

**Project:** data-hub v0.3 — Dagster-based Salesforce Pull Pipeline via Nango Proxy
**Domain:** Scheduled pull ingestion pipeline — Dagster orchestration, Nango proxy auth, Salesforce SOQL, PostgreSQL persistence
**Researched:** 2026-03-20
**Confidence:** HIGH

## Executive Summary

data-hub v0.3 adds a scheduled, pull-based Salesforce ingestion pipeline using Dagster alongside the existing FastAPI webhook service. The two pipelines are additive and complementary: the webhook path (v0.2.0) handles near-real-time push events from Nango, while the Dagster pipeline provides hourly full-refresh snapshots of four Salesforce objects (Opportunity, OpportunityHistory, Task, Event). Both write to the same `data_records` table but use different idempotency strategies — webhooks use `ON CONFLICT DO NOTHING` (append-only), Dagster uses `ON CONFLICT DO UPDATE` (full refresh overwrites stale data). This divergence is intentional and must not be collapsed into a single ingestion path.

The recommended implementation is minimal: two new packages (`dagster` runtime and `dagster-webserver` for local dev UI) plus promotion of `httpx` from dev to production. Salesforce is reached exclusively through the Nango proxy — no direct OAuth credentials are needed in the Python codebase. Nango has no official Python SDK, so a thin `ConfigurableResource` wrapping `httpx.Client` (sync) is the correct pattern. The Dagster pipeline lives in a new `dagster/` directory at the project root — a separate OS process from FastAPI, never embedded within it. All four Salesforce assets follow the same full-refresh pattern; Opportunity is the most complex due to nested SOQL relationships and should be implemented first to validate the end-to-end data flow before replicating the pattern for the three simpler objects.

The dominant risks are infrastructure-level, not business-logic-level. SQLite (Dagster's default internal storage) corrupts under concurrent asset materializations and must be replaced with PostgreSQL from day one. SOQL pagination must follow `nextRecordsUrl` link-based navigation — `OFFSET` is silently capped at 2000 records and does not raise an error. Full refresh assets must use a TRUNCATE-INSERT pattern within a single transaction or duplicates accumulate on every re-run. Dagster resources must use `EnvVar(...)` rather than `os.getenv()` to remain compatible with Dagster Cloud deployment. All eight critical pitfalls have clear, actionable prevention strategies and none require rearchitecting — they are configuration and implementation discipline issues.

---

## Key Findings

### Recommended Stack

The v0.3 stack is additive — two new packages and one promotion. `dagster>=1.12.20` is the orchestration runtime; `dagster-webserver>=1.12.20` is a dev-only dependency for the local UI. `httpx>=0.28.1` is promoted from dev to production since it is now a runtime dependency of the Nango proxy resource. Additionally, `dagster-postgres` is required to replace Dagster's default SQLite internal storage. No other new packages are needed. The Nango Python SDK does not exist (docs confirm "coming soon — use the REST API"). `dagster-salesforce` and `simple-salesforce` are explicitly ruled out — they authenticate directly to Salesforce and bypass Nango's token injection model. PostgreSQL persistence reuses the existing `data_records` table with no schema changes.

Dagster's synchronous-first execution model (assets run in threads, not an event loop) means `httpx.Client` (sync) is correct for Nango proxy calls. Using `asyncio.run()` to bridge the existing async `NangoClient` into sync Dagster assets is acceptable for v0.3 batch workloads, with a clear upgrade path to a native sync client if needed later.

**Core technologies:**
- `dagster>=1.12.20`: Asset orchestration runtime — software-defined assets provide lineage, retry semantics, and metadata out of the box; the correct abstraction for a scheduled pull pipeline
- `dagster-webserver>=1.12.20`: Local dev UI at `localhost:3000` — dev-only; not needed in production images
- `dagster-postgres`: Dagster internal storage backend — replaces SQLite to prevent concurrent materialization lock errors; required from day one
- `httpx>=0.28.1` (promoted from dev): Sync HTTP client for Nango proxy `ConfigurableResource`
- `psycopg2-binary` (already present): Sync PostgreSQL driver for Dagster assets — correct for Dagster's synchronous execution model; FastAPI continues using `asyncpg` in its separate process

### Expected Features

All v0.3 features are P1 (required for milestone) or P2 (add after P1 is stable). No features are ambiguous about their milestone placement.

**Must have (v0.3 table stakes):**
- Dagster project scaffold (`dagster/definitions.py`, `dagster/assets/`, `dagster/resources/`) — `dagster dev` must boot without errors before any asset is written
- Nango proxy `ConfigurableResource` — wraps `httpx.Client`; enforces all three required headers at instantiation; implements `nextRecordsUrl` link-based SOQL pagination
- Opportunity asset (full refresh) — most complex SOQL due to nested Account, Owner, OpportunityContactRoles; implement first to establish the end-to-end pattern
- OpportunityHistory, Task, and Event assets — follow the same full-refresh pattern as Opportunity; flat SOQL queries; parallelize implementation after Opportunity validates
- Idempotent TRUNCATE-INSERT transaction — DELETE all rows for `model_name + connection_id`, then bulk INSERT, within a single transaction; rollback on any failure preserves prior data
- `MaterializeResult` with row count metadata — visible in Dagster UI; required for operator observability

**Should have (v0.3.x after validation):**
- Hourly schedule via `AutomationCondition.on_cron("@hourly")` — add once assets are confirmed stable and API call consumption is measured
- Dagster Cloud deployment config (`dagster_cloud.yaml`) — needed for production but not for local validation
- Multi-connection partitioning by `connection_id` — defer until a second Salesforce org is onboarded

**Defer (v0.4+):**
- Incremental / cursor-based loading (`WHERE LastModifiedDate > {cursor}`) — full refresh must be proven in production first
- Schema drift detection — alert when Salesforce adds or removes fields
- Event consumers subscribing to Dagster materialization events

### Architecture Approach

Dagster runs as a completely separate OS process from FastAPI — no shared memory, no shared connection pools, no embedded mounting. The `dagster/` package lives at the project root (not inside `src/`) to make the process boundary explicit and keep the existing hexagonal `src/` layout entirely unchanged. Both processes connect to the same PostgreSQL database using different drivers: FastAPI uses `asyncpg` (async), Dagster uses `psycopg2` (sync, already in pyproject.toml). The shared contract between them is the `data_records` table schema, not any Python class or protocol.

Dagster resources wrap existing infrastructure clients rather than reimplementing them. The `NangoResource` delegates to the existing `src/adapters/driven/nango/client.py` for HTTP logic. The `PostgresResource` uses `psycopg2` directly to avoid the `asyncio.run()` overhead in every database write. All resource configuration uses `dg.EnvVar(...)` — never `os.getenv()` — to support both local OSS and Dagster Cloud deployment without code changes.

**Major components:**
1. `dagster/definitions.py` — Dagster entry point; registers all four assets and both resources; selects resource config by `DAGSTER_DEPLOYMENT` env var
2. `dagster/resources/nango.py` (`NangoResource`) — `ConfigurableResource` wrapping `NangoClient`; enforces all three required Nango proxy headers; exposes `query_soql()` with `nextRecordsUrl` pagination loop
3. `dagster/resources/postgres.py` (`PostgresResource`) — `ConfigurableResource` using `psycopg2`; manages connection lifecycle via `yield_for_execution`; strips `+asyncpg` suffix from `DATABASE_URL` for psycopg2 compatibility
4. `dagster/assets/` (opportunity, opp_history, task, event) — four `@asset` functions following the same fetch-paginate-truncate-insert pattern; each returns `MaterializeResult` with row count metadata
5. `workspace.yaml` — `dagster dev` entrypoint for local development; points to `dagster.definitions` module
6. `dagster.yaml` — Dagster instance config; configures PostgreSQL storage to replace default SQLite (must use a separate DB or schema from `data_records` to avoid Alembic conflicts)

### Critical Pitfalls

1. **Dagster SQLite storage corrupts under concurrent runs** — configure `dagster.yaml` with `dagster-postgres` storage from day one; never use the default SQLite backend; verify by materializing all four assets simultaneously with zero lock errors before proceeding
2. **SOQL OFFSET is silently capped at 2000 records** — implement `nextRecordsUrl` link-based pagination in `NangoResource.query_soql()`; never use `OFFSET` in any SOQL query; validate with a mock that verifies the second-page fetch is triggered
3. **Full refresh without TRUNCATE accumulates duplicates** — wrap `DELETE FROM data_records WHERE model_name = :m AND connection_id = :c` plus bulk `INSERT` in a single `psycopg2` transaction; run the same asset twice and confirm `COUNT(*)` is identical both times
4. **Nango proxy missing headers return opaque 400/401** — validate all three required headers at `NangoResource` instantiation time; raise `ConfigurationError` before the first HTTP call; never hardcode `connection_id` as a string literal — always use `EnvVar("NANGO_CONNECTION_ID")`
5. **`os.getenv()` in Dagster resources breaks cloud deployment** — all resource configuration must use `dg.EnvVar(...)` so Dagster can resolve config in both OSS and Dagster Cloud; grep for `os.getenv` in dagster code as a pre-deployment gate check
6. **Dagster port conflicts with FastAPI** — run as separate processes on different ports; never use `app.mount()` to embed Dagster in FastAPI (GitHub issue #12797 confirms this is broken); use `dagster dev --port 3001` if port 3000 is occupied
7. **Salesforce API rate limit exhaustion from aggressive scheduling** — count API calls per full-refresh run during development; set schedule frequency only after measuring actual consumption; target < 50% of the daily org quota
8. **`dagster instance migrate` skipped after version upgrades** — add to project upgrade runbook and Docker startup command; skipping causes silent misbehavior (lost run history, broken schedules) without a clear error message

---

## Implications for Roadmap

Based on combined research, the build order is driven by infrastructure dependencies that must be resolved before any Salesforce data can flow. Three phases are suggested.

### Phase 1: Dagster Infrastructure Setup

**Rationale:** Every subsequent step depends on a working Dagster instance. SQLite lock errors under concurrent asset materializations are the highest-probability failure mode and must be eliminated before any asset is authored. All configuration patterns (`EnvVar`, separate process model, PostgreSQL storage, port assignment) must be established first — retrofitting them after assets are written is costly and creates regressions in a working pipeline.

**Delivers:** `dagster dev` boots cleanly; all four assets can be materialized simultaneously without lock errors; `NangoResource` and `PostgresResource` are constructed and injectable with all required config; environment variable contract is documented in `.env.example`.

**Addresses (from FEATURES.md):**
- Dagster project scaffold — `src/pipeline/definitions.py`, `workspace.yaml`, `dagster.yaml` (P1)
- `dagster dev` local runnable (P1)
- `NangoResource` and `PostgresResource` construction and config validation (P1)

**Avoids (from PITFALLS.md):**
- Dagster SQLite concurrency locks — PostgreSQL storage configured from day one (Critical)
- Dev/cloud env var config mismatch — `EnvVar` pattern established before any resource is used (Critical)
- Port conflict with FastAPI — separate process model verified at setup (Critical)
- `dagster instance migrate` gap — runbook documented at setup time (Critical)

**Research flag:** Standard Dagster patterns — `ConfigurableResource`, `workspace.yaml`, `dagster.yaml`, `EnvVar` are all documented at HIGH confidence in official Dagster docs. No additional research phase needed.

---

### Phase 2: Nango Proxy Client and Opportunity Asset

**Rationale:** The proxy client is a shared dependency of all four assets. Implementing and testing it in isolation, before asset logic exists, validates the most error-prone integration point: Nango header enforcement, `nextRecordsUrl` link-based SOQL pagination, and the psycopg2 TRUNCATE-INSERT transaction pattern. Opportunity is the first asset because it is the most complex (nested SOQL for Account, Owner, OpportunityContactRoles) — proving the end-to-end pipeline on the hardest case means the remaining three assets are confident replications, not additional unknowns.

**Delivers:** Fully tested `NangoResource.query_soql()` with link-based pagination; Opportunity asset pulling all records from Salesforce via Nango and persisting via TRUNCATE-INSERT to `data_records`; row count metadata visible in Dagster UI; idempotency confirmed (two runs = same count).

**Addresses (from FEATURES.md):**
- Nango proxy `ConfigurableResource` — pagination and SOQL execution (P1)
- Opportunity asset with full refresh (P1)
- Idempotent TRUNCATE-INSERT transaction (P1)
- `MaterializeResult` with row count metadata (P1)

**Avoids (from PITFALLS.md):**
- SOQL OFFSET truncation at 2000 records — `nextRecordsUrl` pagination implemented and tested (Critical)
- Nango missing headers returning opaque errors — header validation at construction time (Critical)
- Full refresh duplicate accumulation — TRUNCATE-INSERT pattern implemented and verified (Critical)

**Research flag:** Nango proxy behavior for SOQL `nextRecordsUrl` pagination is documented at MEDIUM confidence — validate with a live Nango-proxied Salesforce query before finalizing the client implementation. A single live smoke test supersedes documentation for this integration point.

---

### Phase 3: Remaining Assets, Schedule, and Deployment Config

**Rationale:** OpportunityHistory, Task, and Event are replication of the Opportunity pattern with simpler (flat) SOQL queries. Once Opportunity validates the pipeline, these three are low-risk parallel implementations. Scheduling is deferred until assets are stable and per-run API call consumption is measured against a real org. Dagster Cloud config is the final step with no upstream dependencies other than working assets.

**Delivers:** All four Salesforce objects syncing to `data_records`; hourly schedule enabled after API consumption is measured and confirmed within quota; `dagster_cloud.yaml` and `build.yaml` ready for production deployment.

**Addresses (from FEATURES.md):**
- OpportunityHistory, Task, Event assets (P1)
- Hourly schedule via `AutomationCondition.on_cron("@hourly")` (P2)
- Dagster Cloud deployment config (P2)

**Avoids (from PITFALLS.md):**
- Salesforce API rate limit exhaustion — schedule frequency set only after measuring actual API call count per run (Critical)

**Research flag:** Asset replication of an established pattern — no research phase needed. Dagster Cloud deployment config is MEDIUM confidence (serverless vs hybrid modes differ) — confirm deployment target and validate `dagster_cloud.yaml` structure against current Dagster+ docs at Phase 3 start.

---

### Phase Ordering Rationale

- **Infrastructure before assets:** Dagster SQLite lock failures are stochastic — they may not appear on the first single materialization but emerge under concurrent runs. Establishing PostgreSQL storage, port separation, and `EnvVar` patterns before any asset is written prevents the most common v0.3 failure modes from appearing mid-implementation.
- **Nango client before asset logic:** The proxy client is shared across all four assets. A pagination bug silently truncates every asset's data. Testing the client in isolation with mocked `nextRecordsUrl` responses is far cheaper than debugging data completeness after assets are built.
- **Opportunity before other assets:** Opportunity has nested SOQL relationships that the other three objects lack. Validating the complete fetch-paginate-truncate-insert pattern on the hardest case first means the remaining three are replications, not experiments.
- **Schedule last:** The hourly schedule is a one-liner to add, but enabling it before measuring per-run API consumption risks exhausting the Salesforce daily quota. Measure first, schedule second.

### Research Flags

Phases needing live validation before finalizing implementation:
- **Phase 2 (Nango proxy client):** Confirm `nextRecordsUrl` pagination behavior with a live Nango-proxied Salesforce SOQL query. The Nango proxy is expected to return the Salesforce response body unchanged, but this should be validated against an actual connection before the client is considered complete.

Phases with standard patterns (no additional research phase needed):
- **Phase 1 (Dagster infrastructure):** `ConfigurableResource`, `workspace.yaml`, `dagster.yaml` PostgreSQL storage, and `EnvVar` usage are all documented at HIGH confidence in official Dagster docs.
- **Phase 3 (remaining assets and schedule):** Direct replication of the Phase 2 pattern; `AutomationCondition.on_cron` is a one-liner with official docs. Cloud config needs a quick docs check at Phase 3 start, not a full research cycle.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All packages verified on PyPI with exact versions; Nango SDK absence confirmed in official docs; `psycopg2-binary` confirmed already present in pyproject.toml; httpx already in lockfile |
| Features | HIGH | Feature list derived from existing TypeScript Nango sync field lists (authoritative project source) and Dagster official docs; SOQL field specifications cross-referenced against `nango-integrations/salesforce/syncs/*.ts` |
| Architecture | HIGH | Existing codebase inspected directly; Dagster process separation confirmed against official docs and GitHub issue #12797; `yield_for_execution` lifecycle verified in managing-resource-state docs |
| Pitfalls | HIGH (Dagster/Salesforce), MEDIUM (Nango proxy) | Dagster pitfalls verified against official docs and linked community issues; Nango proxy Python patterns inferred from API reference spec; no official Nango Python examples available |

**Overall confidence:** HIGH

### Gaps to Address

- **Nango proxy live behavior:** The `nextRecordsUrl` pagination pattern should be validated with a real Nango-proxied SOQL call before the client implementation is considered final. Expected to work as documented, but live validation eliminates a MEDIUM-confidence assumption.
- **Salesforce API call budget per run:** Unknown until the Opportunity asset is implemented and a full run is measured. Schedule frequency cannot be set responsibly until this number is logged from a real org.
- **Dagster Cloud deployment mode:** The project has not committed to serverless vs. hybrid Dagster+. The `dagster_cloud.yaml` structure differs between the two. Confirm deployment target before Phase 3.
- **`asyncio.run()` edge cases:** Using `asyncio.run()` to bridge the async `NangoClient` into sync Dagster assets is the Phase 2 approach. If an existing event loop is detected in the test context, this will raise a `RuntimeError`. Monitor during Phase 2; fallback is a native sync `httpx.Client` rewrite of the pagination logic.

---

## Sources

### Primary (HIGH confidence)
- [dagster on PyPI](https://pypi.org/project/dagster/) — version 1.12.20, Python 3.12 support confirmed, release date 2026-03-19
- [dagster-webserver on PyPI](https://pypi.org/project/dagster-webserver/) — version 1.12.20, co-versioned with dagster
- [Dagster project structure docs](https://docs.dagster.io/guides/build/projects/project-structure/project-overview) — `definitions.py` entry point, `workspace.yaml`, project layout conventions
- [Dagster external resources guide](https://docs.dagster.io/guides/build/external-resources) — `ConfigurableResource`, `PrivateAttr`, `yield_for_execution`
- [Dagster managing resource state docs](https://docs.dagster.io/guides/build/external-resources/managing-resource-state) — connection pooling pattern with context manager
- [Dagster unit testing assets docs](https://docs.dagster.io/guides/test/unit-testing-assets-and-ops) — `materialize()`, `build_asset_context()`, resource mocking patterns
- [Dagster transitioning dev to prod](https://docs.dagster.io/guides/operate/dev-to-prod) — environment configuration, `EnvVar` usage
- [Dagster using environment variables](https://docs.dagster.io/guides/operate/configuration/using-environment-variables-and-secrets) — `EnvVar` vs `os.getenv` distinction
- [Nango proxy GET API reference](https://nango.dev/docs/reference/api/proxy/get) — URL format `https://api.nango.dev/proxy/{path}`, required headers confirmed
- [Nango Python SDK page](https://nango.dev/docs/reference/sdks/python) — confirms no installable SDK exists; use REST API directly
- [Salesforce SOQL limits (OFFSET max 2000)](https://developer.salesforce.com/docs/atlas.en-us.salesforce_app_limits_cheatsheet.meta/salesforce_app_limits_cheatsheet/salesforce_app_limits_platform_soslsoql.htm) — OFFSET limitation confirmed
- [Salesforce API request limits](https://developer.salesforce.com/docs/atlas.en-us.salesforce_app_limits_cheatsheet.meta/salesforce_app_limits_cheatsheet/salesforce_app_limits_platform_api.htm) — daily quota structure and `REQUEST_LIMIT_EXCEEDED` response
- Existing codebase: `src/adapters/driven/nango/client.py`, `src/adapters/driven/postgresql/repository.py`, `src/config/settings.py`, `pyproject.toml`, `nango-integrations/salesforce/syncs/*.ts` — inspected directly

### Secondary (MEDIUM confidence)
- [Dagster async blog post](https://dagster.io/blog/when-sync-isnt-enough) — sync-first execution model; async requires explicit executor configuration
- [Dagster Cloud dagster_cloud.yaml reference](https://docs.dagster.io/deployment/code-locations/dagster-cloud-yaml) — deployment config structure, serverless vs hybrid mode differences
- [Nango proxy POST API reference](https://nango.dev/docs/reference/api/proxy/post) — GET pattern inferred from POST docs; headers are identical
- [Dagster SQLite vs PostgreSQL storage (community discussion)](https://github.com/dagster-io/dagster/discussions/8552) — SQLite lock contention under concurrent runs documented by community

### Tertiary (community, informational)
- [Dagster mounting in FastAPI issue #12797](https://github.com/dagster-io/dagster/issues/12797) — confirms `app.mount()` of Dagster webserver is unsupported and broken
- [Dagster incremental assets discussion #13618](https://github.com/dagster-io/dagster/issues/13618) — IO managers not suited for upsert; custom asset logic required
- [Dagster OOM with large datasets discussion #4669](https://github.com/dagster-io/dagster/discussions/4669) — streaming pages recommendation for large orgs
- [Dagster event database locked (community)](https://discuss.dagster.io/t/16769182) — SQLite lock failure mode documented in community

---
*Research completed: 2026-03-20*
*Ready for roadmap: yes*
