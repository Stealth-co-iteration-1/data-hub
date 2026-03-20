# Feature Research

**Domain:** Dagster-based pull pipeline — Salesforce data ingestion via Nango proxy
**Researched:** 2026-03-20
**Confidence:** HIGH

> **Milestone scope:** This file focuses ONLY on NEW features for v0.3. Existing features
> (webhook ingestion, schema validation, PostgreSQL persistence, query API, Salesforce Nango
> syncs in TypeScript) are already validated and treated as load-bearing dependencies below.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features that a Dagster-based Salesforce pipeline must have to be considered complete and usable.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Dagster project structure** | `dagster dev` requires a `definitions.py` entry point and a `pyproject.toml` `[tool.dagster]` section; without this the UI won't load and assets can't be discovered | LOW | Standard layout: `pipeline/definitions.py` + `pipeline/assets/` + `pipeline/resources.py`; co-located in data-hub repo under `src/pipeline/` |
| **Nango proxy client (Python/httpx)** | Assets must call Salesforce SOQL endpoints through Nango proxy — Nango injects auth credentials so the asset never holds OAuth tokens directly | MEDIUM | No official Nango Python SDK (docs say "coming soon — use REST API"); must build a thin httpx wrapper; endpoint: `GET https://api.nango.dev/proxy/services/data/v60.0/query?q=<SOQL>`; required headers: `Authorization: Bearer <secret>`, `Provider-Config-Key: salesforce`, `Connection-Id: <id>` |
| **Dagster ConfigurableResource for Nango** | Dagster's dependency injection model requires external clients to be wrapped as `ConfigurableResource` subclasses; this makes the client testable (swap in a fake) and surfaces config in the UI | LOW | Fields: `base_url`, `secret_key`; expose a `proxy_get(connection_id, endpoint, params)` method; inject into assets as a parameter |
| **Opportunity asset with full refresh** | Core business object; downstream analytics (revenue reporting) depends on this table being populated | MEDIUM | Full refresh: `DELETE FROM salesforce_opportunities WHERE connection_id = ?` then bulk insert; use existing `DataRepository.add()` or a new direct PostgreSQL bulk insert path |
| **OpportunityHistory asset with full refresh** | Stage velocity analysis requires this; already has TypeScript sync collecting it hourly | MEDIUM | Same pattern as Opportunity; must preserve `ORDER BY OpportunityId, CreatedDate` semantics in the loaded data |
| **Task asset with full refresh** | Activity tracking for emails/calls; already collected by TypeScript sync | MEDIUM | Same full-refresh pattern; flat structure (no nested relationships like Opportunity has) |
| **Event asset with full refresh** | Meeting tracking; same collection cadence as Task | MEDIUM | Same full-refresh pattern; flat structure |
| **Raw JSON persistence to PostgreSQL** | Data lands in the existing `data_records` table as JSON payloads; existing `DataRepository.add()` handles this | LOW | Reuse existing `AddDataHandler` + `DataRepository` infrastructure; connection_id and model name identify the source; no new tables needed |
| **`dagster dev` local runnable** | Engineers must be able to run `dagster dev` locally and trigger materializations via the UI; required for testing during development | LOW | Needs `DAGSTER_HOME` env var (or defaults), a `workspace.yaml` or `pyproject.toml` `[tool.dagster]` pointing to `definitions.py`, and all resource configs provided via env vars |
| **MaterializeResult with row count metadata** | Standard Dagster practice for observability; the UI shows "row_count" on each materialization event; engineers need to verify records are landing | LOW | Return `MaterializeResult(metadata={"dagster/row_count": n, "connection_id": connection_id})`; built-in Dagster convention, surfaced in the asset UI |

### Differentiators (Competitive Advantage)

Features that elevate the Dagster pipeline beyond bare-minimum fetch-and-store.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Hourly schedule via `AutomationCondition.on_cron`** | Keeps Salesforce data fresh with no manual triggering; matches the `every hour` cadence of the existing TypeScript Nango syncs | LOW | `automation_condition=dg.AutomationCondition.on_cron("@hourly")` on each asset; no separate schedule definition needed |
| **Connection-aware asset parameterization** | A single asset definition can serve multiple Salesforce orgs (multiple Nango `connection_id` values) without code duplication | MEDIUM | Use Dagster partitions keyed by `connection_id`, OR pass `connection_id` as a config field; partitions are the idiomatic Dagster approach but add complexity; for v0.3, config-based is simpler |
| **Idempotent full refresh (DELETE + batch insert in one transaction)** | Prevents partial loads: if the Salesforce fetch fails mid-way, the previous data is preserved; no data loss on network errors | MEDIUM | Wrap DELETE + INSERT in a single SQLAlchemy transaction; commit only after all records are inserted; if any step raises, the transaction rolls back |
| **Structured logging via structlog in assets** | Consistent with existing data-hub observability patterns; log statements flow into the same log sink as webhook events | LOW | `get_logger(__name__)` from existing `src/observability/logging.py`; Dagster also captures `context.log.*` calls in the UI run log |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Dagster IO managers for PostgreSQL** | "Let Dagster's IO manager handle writes automatically" | IO managers assume full asset replacement on every materialization; don't support upsert or delete-insert semantics; not compatible with the existing `DataRepository` Protocol or the `data_records` table structure | Write custom asset ops that call `DataRepository.add()` directly; full control over the load strategy |
| **Incremental loading (cursor-based)** | "Don't re-fetch all records every run — too expensive for large orgs" | Adds significant complexity: must persist cursors, handle SOQL `WHERE LastModifiedDate >` clauses, manage state across runs; v0.3 goal is working correctness first | Implement full refresh now; add incremental as a v0.4 optimization once the full-refresh pipeline is proven in production |
| **Replacing the existing webhook pipeline** | "Since Dagster pulls data, we don't need Nango webhooks anymore" | The two pipelines are parallel: webhooks deliver near-real-time events, Dagster provides scheduled full refreshes; removing webhooks degrades latency | Keep both pipelines; Dagster is additive, not a replacement |
| **Nango SDK TypeScript in Python** | "Re-use the existing TypeScript sync code from nango-integrations/" | Different runtime; TypeScript syncs run on Nango's infrastructure, Python assets run in Dagster; cross-language reuse is not feasible | The TypeScript syncs define the SOQL field lists that Python can reference as documentation; implement equivalent SOQL queries in Python |
| **Dagster asset sensors for webhook events** | "Trigger Dagster when Nango sends a webhook" | Adds a bidirectional dependency between the webhook pipeline and Dagster; creates operational coupling that makes both harder to debug | Keep schedules simple (cron); if event-triggered materializations are needed, add a sensor in a future milestone |
| **Custom Dagster IO manager for Nango proxy** | "Model Nango as a Dagster IO manager so we can swap data sources" | IO managers are for persisting assets, not fetching from external APIs; using one for HTTP calls is an anti-pattern in Dagster | Use `ConfigurableResource` for the Nango client; IO managers are for writes |

---

## Feature Dependencies

```
[Dagster project structure]
    └──requires──> [pyproject.toml with [tool.dagster] section]
    └──required-by──> [all asset definitions]

[Nango proxy client (ConfigurableResource)]
    └──required-by──> [Opportunity asset]
    └──required-by──> [OpportunityHistory asset]
    └──required-by──> [Task asset]
    └──required-by──> [Event asset]

[Opportunity asset]
    └──requires──> [Nango proxy client]
    └──requires──> [DataRepository.add() — existing port]
    └──requires──> [PostgreSQL connection — existing infrastructure]
    └──optional──> [Hourly schedule]

[OpportunityHistory asset]
    └──requires──> [Nango proxy client]
    └──requires──> [DataRepository.add() — existing port]
    └──same-pattern-as──> [Opportunity asset]

[Task asset]
    └──requires──> [Nango proxy client]
    └──requires──> [DataRepository.add() — existing port]
    └──same-pattern-as──> [Opportunity asset]

[Event asset]
    └──requires──> [Nango proxy client]
    └──requires──> [DataRepository.add() — existing port]
    └──same-pattern-as──> [Opportunity asset]

[MaterializeResult metadata]
    └──enhances──> [all asset definitions]
    └──no-extra-dependencies──> [built into dagster]

[Hourly schedule]
    └──enhances──> [all asset definitions]
    └──requires──> [Dagster project structure]
```

### Dependency Notes

- **Nango proxy client must come before all assets:** Assets cannot make authenticated Salesforce calls without it; build and test the client in isolation first.
- **Dagster project structure is the first deliverable:** Without `definitions.py` and a working `dagster dev` boot, nothing else can be validated.
- **Existing `DataRepository` Protocol is load-bearing:** The four Salesforce assets depend on `DataRepository.add()` being available; this port is already implemented by the PostgreSQL adapter — no changes needed.
- **One asset pattern reused four times:** Opportunity, OpportunityHistory, Task, and Event follow the same: fetch via Nango proxy → paginate → bulk insert. Opportunity is the most complex (nested relationships); implement it first and replicate the pattern for the others.

---

## MVP Definition for v0.3

### Launch With (v0.3)

Minimum viable milestone — what's needed for a working Dagster Salesforce pipeline.

- [ ] **Dagster project scaffold** — `src/pipeline/definitions.py`, `src/pipeline/assets/salesforce.py`, `src/pipeline/resources/nango.py`; `dagster dev` boots without errors
- [ ] **Nango proxy ConfigurableResource** — wraps httpx; exposes `proxy_get(connection_id, endpoint, params)`; configured from env vars `NANGO_BASE_URL`, `NANGO_SECRET_KEY`
- [ ] **Opportunity asset** — full refresh; SOQL matches TypeScript sync field list (Id, Name, Amount, StageName, etc.); nested Account/Owner/ContactRoles handled
- [ ] **OpportunityHistory asset** — full refresh; SOQL matches TypeScript sync field list; ORDER BY preserved
- [ ] **Task asset** — full refresh; flat SOQL query
- [ ] **Event asset** — full refresh; flat SOQL query
- [ ] **Idempotent full refresh transaction** — DELETE + batch INSERT wrapped in single transaction per asset; rollback on failure
- [ ] **MaterializeResult with row count** — each asset returns row count metadata; visible in Dagster UI

### Add After Validation (v0.3.x)

- [ ] **Hourly schedule** — `AutomationCondition.on_cron("@hourly")` on each asset; add once assets are proven stable
- [ ] **Multi-connection partitioning** — partition assets by `connection_id` to support multiple Salesforce orgs; defer until second org is onboarded
- [ ] **Dagster Cloud deployment config** — `dagster_cloud.yaml`, `build.yaml`; needed for production but not for local validation

### Future Consideration (v0.4+)

Already explicitly out of scope per PROJECT.md:

- [ ] **Incremental / delta loads** — `WHERE LastModifiedDate > {cursor}` with persisted cursor state; add after full refresh is proven in production
- [ ] **Schema drift detection** — detect when Salesforce adds/removes fields; add automated alerting
- [ ] **Event consumers** — downstream pipeline subscribes to `DataAdded` events from Dagster materializations

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Dagster project scaffold | HIGH | LOW | P1 |
| Nango proxy ConfigurableResource | HIGH | MEDIUM | P1 |
| Opportunity asset (full refresh) | HIGH | MEDIUM | P1 |
| OpportunityHistory asset (full refresh) | HIGH | LOW | P1 |
| Task asset (full refresh) | HIGH | LOW | P1 |
| Event asset (full refresh) | HIGH | LOW | P1 |
| Idempotent full refresh transaction | HIGH | LOW | P1 |
| MaterializeResult row count metadata | MEDIUM | LOW | P1 |
| Hourly schedule | MEDIUM | LOW | P2 |
| Multi-connection partitioning | MEDIUM | MEDIUM | P2 |
| Dagster Cloud deployment config | LOW | LOW | P2 |
| Incremental loading (cursor) | HIGH | HIGH | P3 |
| Schema drift detection | MEDIUM | HIGH | P3 |
| Event consumers | LOW | HIGH | P3 |

**Priority key:**
- P1: Must have for v0.3 milestone completion
- P2: Should have, add after P1 features are stable
- P3: Explicitly deferred to v0.4 or later

---

## Implementation Complexity Assessment

### Low Complexity (hours, not days)

- **Dagster project scaffold** — standard layout; `definitions.py` with `Definitions(assets=[...], resources={...})`; `pyproject.toml` `[tool.dagster]` section
- **MaterializeResult metadata** — `return MaterializeResult(metadata={"dagster/row_count": n})`; no extra dependencies
- **Hourly schedule** — one-liner `automation_condition` parameter on each `@asset`
- **Task and Event assets** — flat SOQL queries; no nested relationships; copy the Opportunity pattern with simpler field lists

### Medium Complexity (1-3 days)

- **Nango proxy ConfigurableResource** — wrap httpx in a `ConfigurableResource`; handle Salesforce link-based pagination (`nextRecordsUrl`); write unit tests with mocked httpx responses
- **Opportunity asset** — most complex SOQL (nested Account, Owner, OpportunityContactRoles subquery); verify JSON serialization of nested objects into the `data` column; handle null `Account` and `OpportunityContactRoles`
- **Idempotent full-refresh transaction** — `DELETE WHERE connection_id = ? AND model = ?` + `INSERT` batch in a single SQLAlchemy `async with session.begin()` block

### High Complexity (not in v0.3)

- Incremental loading (cursor persistence, SOQL `WHERE` clauses, state management)
- Multi-connection partitioning

---

## Existing Infrastructure as Dependencies

These v0.2 features are load-bearing for v0.3. They must not be broken.

| Existing Feature | How v0.3 Depends On It |
|------------------|------------------------|
| `DataRepository.add()` Protocol method | Salesforce assets call this to persist raw JSON records; no changes to the port needed |
| `AddDataHandler` in kernel | Assets may route through this handler or call `DataRepository.add()` directly; handler enforces audit trail |
| PostgreSQL adapter (`asyncpg`) | Assets persist to the same `data_records` table that webhook events use; same connection pool |
| `settings` (pydantic-settings) | `NANGO_BASE_URL`, `NANGO_SECRET_KEY`, `DATABASE_URL` already sourced from ENV; Dagster resources read from the same config |
| `structlog` setup | Assets can call `get_logger(__name__)` from `src/observability/logging.py`; no new logging setup needed |
| `data_records` table schema | Assets write `model`, `connection_id`, `data` (JSON) — matching the existing schema exactly |
| Nango TypeScript syncs (SOQL field lists) | The field lists in `fetch-opportunities.ts`, `fetch-opportunity-history.ts`, etc. document exactly what fields to SELECT in Python SOQL queries; treat them as the canonical specification |

---

## SOQL Field Specifications (from Existing TypeScript Syncs)

Documented here so the Python assets match the TypeScript sync field lists exactly.

| Asset | Key Fields | Notes |
|-------|------------|-------|
| **Opportunity** | Id, Name, Amount, StageName, IsClosed, IsWon, CloseDate, CreatedDate, LastModifiedDate, ForecastCategoryName, Probability, Type, LeadSource, OwnerId + Account.Name, Account.Industry, Account.AnnualRevenue, Owner.Name, Owner.Email + subquery OpportunityContactRoles | Nested relationships require manual SOQL construction; Salesforce `buildQuery` utility does not support traversal |
| **OpportunityHistory** | Id, OpportunityId, StageName, Amount, CloseDate, Probability, CreatedDate, CreatedById | Flat; `ForecastCategoryName` NOT available on this object; ORDER BY OpportunityId, CreatedDate ASC |
| **Task** | (see fetch-tasks.ts) | Flat; Who/Owner denormalized; ActivityDate filter |
| **Event** | (see fetch-events.ts) | Flat; Who/Owner denormalized; StartDateTime filter |

---

## Sources

- [Dagster Software-Defined Assets Concepts](https://docs.dagster.io/concepts/assets/software-defined-assets) — HIGH confidence
- [Dagster External Resources Guide](https://docs.dagster.io/guides/build/external-resources) — HIGH confidence
- [Dagster Project Structure Overview](https://docs.dagster.io/guides/build/projects/project-structure/project-overview) — HIGH confidence
- [Dagster Asset Metadata and Tags](https://docs.dagster.io/guides/build/assets/metadata-and-tags) — HIGH confidence
- [Dagster Resources Best Practices](https://dagster.io/blog/a-practical-guide-to-dagster-resources) — HIGH confidence
- [Dagster Declarative Automation / Schedules](https://docs.dagster.io/guides/automate/schedules) — HIGH confidence
- [Nango Python SDK](https://nango.dev/docs/reference/sdks/python) — HIGH confidence (confirmed: SDK not yet available; must use REST API directly)
- [Nango Proxy REST API](https://nango.dev/docs/reference/api/proxy/post) — MEDIUM confidence (POST documented; GET pattern inferred from `Authorization`, `Provider-Config-Key`, `Connection-Id` headers)
- [Dagster Incremental Update Discussion](https://github.com/dagster-io/dagster/discussions/14733) — MEDIUM confidence (IO managers not suited for upsert; custom asset logic required)
- Existing `nango-integrations/salesforce/syncs/*.ts` — HIGH confidence (authoritative SOQL field specifications for this project)

---

*Feature research for: Dagster-based Salesforce pipeline — v0.3 milestone*
*Researched: 2026-03-20*
