# Stack Research

**Domain:** Dagster-based pull ingestion pipeline — Salesforce via Nango proxy (data-hub v0.3)
**Researched:** 2026-03-20
**Confidence:** HIGH

## Context

This is a SUBSEQUENT MILESTONE research file. The following stack is already validated and locked — do not re-research or re-add:

- Python 3.12+, FastAPI, SQLAlchemy 2.0 async, asyncpg, structlog, prometheus_client, Pydantic, Alembic
- PostgreSQL and SQLite adapters via hexagonal architecture
- Webhook ingestion with HMAC verification
- Schema validation with structured error reporting
- httpx is already in `[dependency-groups] dev` as a test utility

This document covers ONLY what must be added for v0.3: Dagster orchestration, Nango proxy client, Salesforce SOQL HTTP calls.

All additions below are **additive**. Nothing in the existing stack changes.

---

## New Stack Additions

### Core Orchestration

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `dagster` | `>=1.12.20` | Asset orchestration runtime and scheduler | Current stable release (1.12.20 as of 2026-03-19). Dagster's software-defined assets model is the correct abstraction for a pull-based ingestion pipeline — each Salesforce object becomes an asset with lineage, metadata, and retry semantics built-in. The only credible alternative (Prefect, Airflow) provides no meaningful advantage for this scale and introduces higher operational overhead. |
| `dagster-webserver` | `>=1.12.20` | Local dev UI — asset graph, run history, logs | Required to run `dg dev`. Provides the local Dagster UI at `localhost:3000`. Listed as a dev dependency by Dagster's own project scaffolder. Deploy to Dagster Cloud does not require it in production images, only during local development. |

**pyproject.toml changes:**

```toml
dependencies = [
    # ... existing deps unchanged ...
    "dagster>=1.12.20",          # NEW: orchestration runtime
]

[dependency-groups]
dev = [
    "httpx>=0.28.1",             # already present
    "dagster-webserver>=1.12.20", # NEW: local dev UI
    "pytest>=8.3",               # already present
    "pytest-asyncio>=0.24",      # already present
    "pytest-cov>=6.0",           # already present
    "ruff>=0.9",                 # already present
    "pyright>=1.1",              # already present
]
```

**Install:**

```bash
uv add dagster
uv add --dev dagster-webserver
```

### HTTP Client for Nango Proxy

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `httpx` | `>=0.28.1` | Synchronous HTTP client for Nango proxy calls | httpx is already a dev dependency. Promote it to a production dependency for the Nango `ConfigurableResource`. Dagster's execution model is synchronous by default — assets run in threads, not an event loop. Using httpx's sync `Client` is the correct, straightforward pattern. Async `AsyncClient` inside a Dagster asset requires explicit event loop management (`asyncio.run()` or `anyio.from_thread.run_sync()`) and provides no throughput benefit for serial SOQL pagination. httpx sync client is simpler and correct for this use case. |

**pyproject.toml change:**

```toml
dependencies = [
    # Move httpx from dev to production:
    "httpx>=0.28.1",   # NEW: promoted from dev-only; Nango proxy HTTP calls
]
```

**Remove from `[dependency-groups] dev`** — it moves to main `dependencies`.

---

## No Additional Packages Required

The Nango proxy integration does NOT require a Nango Python SDK. Nango's official Python SDK page shows "Coming soon — use the REST API in the meantime." The proxy is called directly via httpx with three headers (see Integration Points). No `nango` package needed.

The Salesforce integration does NOT require `dagster-salesforce` or `simple-salesforce`. Those packages authenticate directly to Salesforce — incompatible with the Nango proxy authentication model where Nango holds the OAuth tokens and injects credentials on behalf of the connection. Custom SOQL queries via the Nango proxy URL are straightforward with httpx.

PostgreSQL persistence reuses the existing `PostgreSQLDataRepository` (already validated in v0.2.0). No new ORM or persistence library is needed.

---

## Supporting Libraries (Unchanged)

| Area | Current Library | Status for v0.3 |
|------|----------------|----------------|
| ORM / persistence | SQLAlchemy 2.0 async + asyncpg | Unchanged — existing `PostgreSQLDataRepository` used as-is |
| Migrations | Alembic 1.18.4 | Unchanged — no new tables for v0.3 (raw JSON goes into existing `data_records`) |
| Config | pydantic-settings 2.13.1 | Unchanged — add `NANGO_SECRET_KEY`, `NANGO_CONNECTION_ID`, `NANGO_PROVIDER_CONFIG_KEY` env vars to existing `Settings` model |
| Logging | structlog 25.5.0 | Unchanged — Dagster assets log via `context.log`; structlog remains for the FastAPI transport |
| Testing | pytest + pytest-asyncio | Unchanged — Dagster provides `materialize()` and `build_asset_context()` helpers; no new test framework needed |

---

## Integration Points

### 1. Dagster `Definitions` entry point

Dagster loads from a `definitions.py` file at the root of the Dagster package. The project should co-locate this within `src/` as a separate package from the existing FastAPI app:

```
src/
  data_hub/         # existing FastAPI app (unchanged)
  pipeline/         # new Dagster package
    __init__.py
    definitions.py  # Dagster entry point: Definitions(assets=[...], resources={...})
    assets/
      salesforce.py # @asset functions for Opportunity, OpportunityHistory, Task, Event
    resources/
      nango.py      # NangoResource(ConfigurableResource)
```

`definitions.py` structure:

```python
import dagster as dg
from .assets.salesforce import (
    salesforce_opportunities,
    salesforce_opportunity_history,
    salesforce_tasks,
    salesforce_events,
)
from .resources.nango import NangoResource

defs = dg.Definitions(
    assets=[
        salesforce_opportunities,
        salesforce_opportunity_history,
        salesforce_tasks,
        salesforce_events,
    ],
    resources={
        "nango": NangoResource(
            secret_key=dg.EnvVar("NANGO_SECRET_KEY"),
            connection_id=dg.EnvVar("NANGO_CONNECTION_ID"),
            provider_config_key=dg.EnvVar("NANGO_PROVIDER_CONFIG_KEY"),
        )
    },
)
```

### 2. Nango proxy `ConfigurableResource`

The Nango proxy is a pass-through HTTP layer. Every request hits `https://api.nango.dev/proxy/{path}` with three required headers:

| Header | Value | Source |
|--------|-------|--------|
| `Authorization` | `Bearer {NANGO_SECRET_KEY}` | Nango environment secret |
| `Connection-Id` | `{connection_id}` | The Salesforce connection established in Nango |
| `Provider-Config-Key` | `{provider_config_key}` | The integration unique key in Nango |

The resource wraps an httpx sync `Client` using `yield_for_execution` for connection pooling across asset materializations within a run:

```python
from pydantic import PrivateAttr
import dagster as dg
import httpx

class NangoResource(dg.ConfigurableResource):
    secret_key: str
    connection_id: str
    provider_config_key: str

    _client: httpx.Client = PrivateAttr()

    @contextmanager
    def yield_for_execution(self, context):
        headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Connection-Id": self.connection_id,
            "Provider-Config-Key": self.provider_config_key,
        }
        with httpx.Client(
            base_url="https://api.nango.dev",
            headers=headers,
            timeout=30.0,
        ) as client:
            self._client = client
            yield self

    def query_soql(self, soql: str) -> list[dict]:
        # Salesforce REST API: /services/data/vXX.X/query?q=SOQL
        path = "/proxy/services/data/v62.0/query"
        records = []
        url: str | None = path
        while url:
            resp = self._client.get(url, params={"q": soql} if url == path else None)
            resp.raise_for_status()
            body = resp.json()
            records.extend(body.get("records", []))
            next_url = body.get("nextRecordsUrl")
            url = f"/proxy{next_url}" if next_url else None
        return records
```

### 3. Asset pattern — full refresh to PostgreSQL

Each asset materializes by querying Salesforce via the Nango resource and persisting via the existing `PostgreSQLDataRepository` (or directly via `asyncpg` from a sync thread using `asyncio.run()`):

```python
@dg.asset(required_resource_keys={"nango"})
def salesforce_opportunities(context: dg.AssetExecutionContext) -> None:
    records = context.resources.nango.query_soql(
        "SELECT Id, Name, Amount, StageName, CloseDate FROM Opportunity"
    )
    # persist via existing AddData kernel command or direct repository call
    context.log.info(f"Fetched {len(records)} Opportunity records")
```

### 4. Running Dagster dev locally

```bash
# From project root with pyproject.toml
dg dev --module-name pipeline.definitions
# OR if definitions.py is auto-discovered:
dagster dev -f src/pipeline/definitions.py
```

Dagster UI opens at `http://localhost:3000`.

### 5. Dagster Cloud deployment

For Dagster Cloud (Dagster+), the project needs a `dagster_cloud.yaml` at the project root specifying the code location. No `dagster-cloud` agent package is required for serverless mode — it is handled by the Dagster Cloud infrastructure. For hybrid deployment, `dagster-cloud` agent is added to the host machine, not the project's `pyproject.toml`.

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| `dagster>=1.12.20` | Prefect 3.x | If the team is already standardized on Prefect. For a new pipeline with no prior orchestrator, Dagster's asset-first model is better suited to data lineage and observability. |
| `dagster>=1.12.20` | Apache Airflow 2.x | If deploying in an organization with existing Airflow infrastructure. Airflow has higher operational overhead for small teams and lacks native asset lineage. |
| httpx sync `Client` in `ConfigurableResource` | httpx `AsyncClient` with `asyncio.run()` | If making hundreds of concurrent API calls per asset. For serial SOQL pagination (5–10 API calls per asset), sync is simpler and correct. |
| Custom Nango proxy resource (httpx) | `dagster-salesforce` + `simple-salesforce` | If authenticating directly to Salesforce without Nango. These libraries own auth — they conflict with Nango's token injection model. |
| Raw JSON to existing `data_records` table | New raw staging tables per entity | If downstream consumers need typed columns. For v0.3, raw JSON in existing table is consistent with the webhook ingestion path already validated. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `dagster-salesforce` | Authenticates directly to Salesforce — requires `username/password/security_token` credentials. Incompatible with Nango proxy model where Nango holds OAuth tokens and injects Authorization. Adding both creates conflicting auth flows. | httpx `NangoResource` with proxy headers |
| `simple-salesforce` | Same problem as `dagster-salesforce` — direct auth to Salesforce, bypasses Nango entirely | httpx `NangoResource` |
| `nango` Python package | Does not exist. Nango's Python SDK page says "Coming soon — use the REST API". No installable package. | Direct httpx calls to `https://api.nango.dev/proxy/...` |
| `dagster-cloud` in `pyproject.toml` | The `dagster-cloud` package is the hybrid agent, not a project dependency. For serverless Dagster+, CI/CD pushes code and Dagster+ manages execution. Adding it to project deps introduces unnecessary weight. | `dagster_cloud.yaml` config file only |
| `asyncio.run()` inside assets | Creates a new event loop per call; breaks if called from an existing loop context. Dagster assets are synchronous by design. | httpx sync `Client` inside `ConfigurableResource` |
| `dagster-dg-cli` in `dependencies` (production) | CLI scaffolding tool only — not needed at runtime. Adds ~50MB to production container. | Keep in `[dependency-groups] dev` only |

---

## Version Compatibility

| Package | Version | Compatible With | Notes |
|---------|---------|-----------------|-------|
| `dagster` | `>=1.12.20` | Python 3.10–3.14 | 1.12.20 is latest as of 2026-03-19. Python 3.12 fully supported. All packages in the dagster ecosystem (dagster, dagster-webserver) must be on the same version — they are co-versioned. |
| `dagster-webserver` | `>=1.12.20` | dagster 1.12.20 | Must match dagster version exactly. Dev-only. |
| `httpx` | `>=0.28.1` | Python 3.8+, no conflict with any existing dep | 0.28.1 is current stable as of December 2024. httpx is already in the lock file as a dev dep; moving to production adds no new resolution. |
| `dagster` | `>=1.12.20` | SQLAlchemy 2.0 async + asyncpg | Dagster does not use SQLAlchemy internally for your project's database. The two coexist without conflict — Dagster uses its own sqlite-based run storage by default (separate DB from your data_records). |

---

## Stack Patterns by Variant

**If running local development:**

- Install: `uv add dagster && uv add --dev dagster-webserver`
- Run: `dagster dev -f src/pipeline/definitions.py`
- Nango environment variables: `NANGO_SECRET_KEY`, `NANGO_CONNECTION_ID`, `NANGO_PROVIDER_CONFIG_KEY`
- Database: existing `DATABASE_URL=postgresql+asyncpg://...` — reuses existing PostgreSQL container

**If deploying to Dagster Cloud (serverless):**

- Add `dagster_cloud.yaml` to project root pointing to code location
- CI/CD (GitHub Actions) uses Dagster's published action to deploy code
- No `dagster-cloud` package in pyproject.toml for serverless mode
- Production container only needs `dagster` (runtime), not `dagster-webserver`

**If adding unit tests for assets:**

- Use `dagster.materialize()` for full asset execution with real or mock resources
- Use `build_asset_context()` for isolated function-level tests
- Mock `NangoResource` by subclassing it and overriding `query_soql()` — avoids live API calls in CI

---

## Sources

- [dagster on PyPI](https://pypi.org/project/dagster/) — version 1.12.20 confirmed, Python 3.10–3.14 support, release date 2026-03-19 (HIGH confidence)
- [dagster-webserver on PyPI](https://pypi.org/project/dagster-webserver/) — version 1.12.20, co-versioned with dagster (HIGH confidence)
- [Dagster project structure docs](https://docs.dagster.io/guides/build/projects/project-structure/project-overview) — `definitions.py` entry point, `src/` layout, `defs/` convention (HIGH confidence)
- [Dagster external resources docs](https://docs.dagster.io/guides/build/external-resources) — `ConfigurableResource` pattern, `PrivateAttr`, `yield_for_execution` lifecycle (HIGH confidence)
- [Dagster managing resource state docs](https://docs.dagster.io/guides/build/external-resources/managing-resource-state) — `yield_for_execution` with context manager for HTTP client session pooling (HIGH confidence)
- [Dagster async blog post](https://dagster.io/blog/when-sync-isnt-enough) — sync-first execution model confirmed; async requires explicit `dagster-async-executor`; sync httpx recommended for I/O-bound serial calls (MEDIUM confidence)
- [Nango proxy GET API reference](https://nango.dev/docs/reference/api/proxy/get) — URL format `https://api.nango.dev/proxy/{anyPath}`, required headers `Connection-Id`, `Provider-Config-Key`, `Authorization: Bearer` (HIGH confidence)
- [Nango Python SDK page](https://nango.dev/docs/reference/sdks/python) — SDK status: "Coming soon — use the REST API". No installable Python package exists. (HIGH confidence)
- [httpx on PyPI](https://pypi.org/project/httpx/) — version 0.28.1, sync and async client support confirmed (HIGH confidence)
- [Dagster Cloud dagster_cloud.yaml reference](https://docs.dagster.io/deployment/code-locations/dagster-cloud-yaml) — deployment config structure, no `dagster-cloud` package needed for serverless (MEDIUM confidence)
- [Dagster unit testing assets docs](https://docs.dagster.io/guides/test/unit-testing-assets-and-ops) — `materialize()`, `build_asset_context()`, resource mocking patterns (HIGH confidence)

---
*Stack research for: data-hub v0.3 — Dagster Salesforce pipeline via Nango proxy*
*Researched: 2026-03-20*
