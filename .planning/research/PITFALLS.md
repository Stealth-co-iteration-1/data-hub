# Pitfalls Research

**Domain:** Dagster Salesforce pipeline — adding pull-based ingestion to existing Python FastAPI service via Nango proxy
**Researched:** 2026-03-20
**Confidence:** HIGH for Dagster/Salesforce pitfalls (official docs + community issues verified); MEDIUM for Nango proxy specifics (official docs verified, Python client patterns from community)

> This file supersedes the v0.2.0 pitfalls document for the v0.3 milestone: Dagster-based Salesforce
> ingestion. Pitfalls from prior milestones that remain structurally relevant are carried forward at
> the bottom. New content focuses exclusively on the Dagster + Nango + Salesforce integration domain.

---

## Critical Pitfalls

### Pitfall 1: Dagster SQLite Storage Breaks Under Concurrent Runs

**What goes wrong:**
Dagster's default local storage backend is SQLite — for run storage, event log, and schedule storage. When `dagster dev` starts and materializes multiple assets concurrently (which happens by default), SQLite's file-locking causes stochastic failures: `database is locked` errors in the event log writer, corrupted run state, or silent hangs waiting for a lock that never releases. The Dagster daemon and the web server both write to the same SQLite files simultaneously. This is documented in the Dagster community as a known SQLite limitation: "SQLite event database is locked" appears in community discussions about Dagster instances with any parallelism.

**Why it happens:**
`dagster dev` initializes a local instance under `$DAGSTER_HOME` (defaulting to `~/.dagster`) with SQLite storage. The developer runs a job or materializes all four Salesforce assets at once — Opportunity, OpportunityHistory, Task, Event. Each asset runs in a separate process. Multiple processes writing to the same SQLite event log file triggers the lock contention.

**How to avoid:**
Configure Dagster's internal storage to use PostgreSQL (the same PostgreSQL instance already running for the data-hub service is appropriate). Create a `dagster.yaml` under `$DAGSTER_HOME` or in the project root:

```yaml
storage:
  postgres:
    postgres_db:
      username: { env: DAGSTER_POSTGRES_USER }
      password: { env: DAGSTER_POSTGRES_PASSWORD }
      hostname: { env: DAGSTER_POSTGRES_HOST }
      db_name: { env: DAGSTER_POSTGRES_DB }
      port: 5432
```

Add `dagster-postgres` to project dependencies. This eliminates all SQLite locking issues and mirrors the production storage backend from day one.

**Warning signs:**
- `database is locked` appears in Dagster logs during concurrent materializations
- Dagster daemon silently stops processing schedules after a lock error
- `dagster instance migrate` is required after every Dagster upgrade and the migration fails with a SQLite lock error
- Runs show `STARTED` in the UI but never transition to `SUCCESS` or `FAILURE`

**Phase to address:**
Dagster local dev setup phase. Do not proceed to asset authoring until Dagster internal storage is confirmed on PostgreSQL. The acceptance criterion is: materialize all four Salesforce assets simultaneously with no storage lock errors.

---

### Pitfall 2: Nango Proxy Missing Required Headers Cause Opaque 400/401 Errors

**What goes wrong:**
The Nango proxy requires three specific headers on every request: `Authorization: Bearer <NANGO_SECRET_KEY>`, `Connection-Id: <connection_id>`, and `Provider-Config-Key: <integration_id>`. Missing any one of these returns a 400 or 401 from Nango's proxy layer — not from Salesforce — with a generic error message that doesn't identify which header is missing. The Salesforce `connection_id` in this project is per-Staq-customer: there is one Nango connection per Salesforce org connected. Hardcoding a single `connection_id` works in local dev but breaks in production where multiple customer orgs are connected.

**Why it happens:**
Developers build the Nango client against a single known connection for local testing. The `connection_id` is treated as a static configuration value. When the asset is eventually run for a different customer org, the wrong `connection_id` is sent and Nango returns 401. The asset fails, but the error message points to an auth failure rather than a misconfigured header.

**How to avoid:**
Make `connection_id` a Dagster asset parameter or resource configuration — never a hardcoded string. The Nango proxy client resource should accept `connection_id` as a required configuration parameter sourced from environment variables or run config. For the v0.3 milestone (single org), use `EnvVar("NANGO_CONNECTION_ID")` as the source. Never embed a literal connection ID in asset code.

Build a thin `NangoProxyClient` resource class that validates all three required headers are present at instantiation time, raising a clear `ConfigurationError` if any are missing — before the first request is attempted.

**Warning signs:**
- `connection_id` appears as a string literal in asset code rather than being read from environment or config
- Nango returns HTTP 400 or 401 but the error body does not mention Salesforce — it's a Nango-layer rejection
- The Nango client is constructed outside a Dagster resource (e.g., at module import time) meaning headers are resolved at load time, not at run time
- No test exists that validates the client raises a clear error when `NANGO_CONNECTION_ID` is missing

**Phase to address:**
Nango proxy client phase. The resource must be constructed with all headers validated before any Salesforce asset is written.

---

### Pitfall 3: Salesforce SOQL OFFSET Limit of 2000 Silently Truncates Full Refresh

**What goes wrong:**
SOQL does not support `OFFSET` values greater than 2000. A naive full-refresh implementation that uses `OFFSET` to paginate will silently stop at 2000 records — it doesn't raise an error, it simply returns an empty result set as if there are no more records. An Opportunity pipeline for a company with 5,000 closed deals will ingest only the first 2,000 on every full refresh. The data looks complete because no error is raised.

**Why it happens:**
Developers familiar with SQL databases assume offset-based pagination is the correct approach. The Salesforce REST API's `query` endpoint returns a `nextRecordsUrl` field in the response body when more records exist. This link-based pagination mechanism is the correct approach and bypasses the OFFSET limit entirely. The existing Nango TypeScript sync in `salesforce/utils.ts` already implements this correctly using `link_path_in_response_body: 'nextRecordsUrl'` — but re-implementing the Python client from scratch without this pattern reintroduces the bug.

**How to avoid:**
The Python Nango proxy client must implement link-based pagination following the `nextRecordsUrl` field. After the initial query response, check for the presence of `nextRecordsUrl` in the JSON body. If present, issue a subsequent request to that URL (relative to the Salesforce instance base URL) until no `nextRecordsUrl` is returned. Never use `OFFSET` in SOQL. The pattern:

```python
url = query_endpoint(soql)
while url:
    response = nango_client.get(url)
    records.extend(response["records"])
    url = response.get("nextRecordsUrl")  # None when done
```

Add a test using a mock that returns `nextRecordsUrl` on the first call and verifies the second call is made to the correct URL.

**Warning signs:**
- SOQL queries contain `OFFSET` keyword
- Full refresh returns exactly 2000 records — not a round number by coincidence
- No pagination loop in the Salesforce client code; single request per asset
- Lack of a test that verifies pagination across multiple pages

**Phase to address:**
Nango proxy client phase, before any asset implementation. Pagination must be validated as a unit before asset logic is written on top of it.

---

### Pitfall 4: Full Refresh Without Truncate Causes Duplicate Records on Re-Materialization

**What goes wrong:**
A full refresh asset that inserts all Salesforce records on every materialization will accumulate duplicates in PostgreSQL. Materializing the Opportunity asset three times triples the row count. Because the existing `data_records` table uses `event_id` (derived from payload hash) for idempotency, re-running the same payload is handled — but only if the hashing is deterministic and the full payload content is identical on every sync. Any field in the payload that changes between syncs (e.g., `LastModifiedDate`, `SystemModstamp`) produces a different hash, a different `event_id`, and a new row.

**Why it happens:**
Full refresh is intended to replace data, not append. The natural implementation inserts all records and relies on deduplication to handle re-runs. But the deduplication mechanism (payload hash) is content-sensitive. Salesforce records change over time — any modification produces a new hash, defeating deduplication.

**How to avoid:**
For full refresh assets, use a TRUNCATE-INSERT pattern within a single transaction: delete all rows for the given `model_name` and `connection_id`, then insert the fresh batch. This is idempotent regardless of whether individual records changed. Implement it as:

```python
# Inside a single transaction
DELETE FROM data_records WHERE model_name = :model AND connection_id = :conn
INSERT INTO data_records (...) VALUES (...)
```

Keep this within the existing hexagonal architecture: the `AddData` kernel command handles single-record inserts for the webhook path. The Dagster pipeline should call a new `BulkRefreshData` command (or use the repository directly if the Dagster adapter is kept separate from the webhook kernel path) that wraps the TRUNCATE-INSERT.

**Warning signs:**
- Row count in `data_records` grows on every asset materialization rather than staying stable
- No `DELETE` or `TRUNCATE` statement exists in the Dagster pipeline code before the insert loop
- The pipeline re-uses `AddData` command in a loop — this uses the ON CONFLICT DO NOTHING path, which does not handle content-changed records

**Phase to address:**
Full refresh asset implementation phase, for all four Salesforce assets simultaneously. The acceptance criterion is: running the same asset twice yields the same row count both times.

---

### Pitfall 5: Dagster Resource Configuration Differs Between Local Dev and Dagster Cloud

**What goes wrong:**
In local dev, Dagster reads environment variables from the shell (`.env` file, `export` commands). In Dagster Cloud (Serverless or Hybrid), environment variables must be configured through the Dagster+ UI or `dagster_cloud.yaml`. A configuration that works locally because `NANGO_SECRET_KEY` is in `.env` silently fails in production because the variable was never set in the cloud deployment. The asset run shows no error at scheduling time — only at execution time does the resource initialization fail when it cannot find the environment variable.

Additionally, the `dagster.yaml` used for local instance configuration is not used in Dagster Cloud — the cloud uses its own internal storage. Developers who configure local PostgreSQL storage in `dagster.yaml` and assume this carries to the cloud will find that it does not.

**Why it happens:**
Dagster OSS and Dagster Cloud have different configuration mechanisms for the same concern (instance config, environment variables). The `dagster.yaml` file configures local/OSS instances; `dagster_cloud.yaml` configures cloud code locations. Environment variables set locally are not automatically available in cloud deployments. This separation is intentional but underdocumented for teams migrating from local to cloud.

**How to avoid:**
From the start, structure all resource configurations using `EnvVar("...")` — not `os.getenv(...)` or hardcoded values. Dagster's `EnvVar` integration resolves correctly in both OSS and Dagster Cloud environments. Document every required environment variable in a `README` or `.env.example` alongside the Dagster project. Configure all variables in Dagster+ UI or agent config before the first cloud deployment. Use `DAGSTER_IS_DEV_CLI` (set to `"1"` by `dagster dev`) to enable dev-mode behaviors without separate config files.

**Warning signs:**
- `os.getenv("NANGO_SECRET_KEY")` appears in resource code instead of `EnvVar("NANGO_SECRET_KEY")`
- No `.env.example` file listing the required environment variables for the Dagster pipeline
- Cloud deployment fails with `KeyError` or `None`-type errors in resource initialization
- `dagster.yaml` contains the only place where PostgreSQL credentials are configured (not in the cloud environment variables)

**Phase to address:**
Dagster local dev setup phase. Every resource parameter that varies by environment must be `EnvVar`-backed before the first asset is written.

---

### Pitfall 6: Dagster Port Conflicts With Existing FastAPI Service

**What goes wrong:**
`dagster dev` starts a Dagster webserver on port 3000 by default. If the existing FastAPI service is also running locally on port 3000 (or if any other process is using that port), `dagster dev` silently fails to bind or starts but is unreachable. Additionally, the Dagster gRPC code location server starts on an ephemeral or configured port. If the project `workspace.yaml` explicitly specifies a port for the code location that conflicts with another service, the code location shows as unreachable in the Dagster UI with an unhelpful `gRPC UNAVAILABLE` error.

Mounting the Dagster UI inside the existing FastAPI application (`app.mount("/dagster", default_app())`) is not supported — there is a known GitHub issue (dagster-io/dagster#12797) where assets fail to load and static routes break when Dagster is mounted at a non-root path. The correct deployment model is to run Dagster and FastAPI as separate processes on different ports.

**Why it happens:**
Developers assume they can run everything in one process for simplicity. The Dagster UI is a full React application with its own routing, static asset serving, and GraphQL endpoint — it expects to be served at the root path. Mounting at a sub-path breaks the frontend routing.

**How to avoid:**
Run Dagster and FastAPI as completely separate processes. In `docker-compose.yml`, add dedicated services for the Dagster webserver (port 3001 or another free port) and the Dagster daemon. Do not attempt to mount Dagster inside the FastAPI application. Use `dagster dev --port 3001` if the default port is occupied. In the project `workspace.yaml`, do not specify explicit ports for the code location unless necessary — let Dagster assign ephemeral ports automatically.

**Warning signs:**
- `address already in use` error when starting `dagster dev`
- `gRPC Error code: UNAVAILABLE` in Dagster UI for the code location immediately after startup
- Attempt to use `app.mount("/dagster", ...)` in `app.py`
- The Dagster webserver port is hardcoded to 3000, the same as the FastAPI dev server

**Phase to address:**
Dagster local dev setup phase. Verify port assignment and separate process model before asset authoring.

---

### Pitfall 7: Salesforce API Rate Limit Exhaustion During Full Refresh

**What goes wrong:**
Salesforce REST API rate limits are per-org and per-day: typically 100,000 API requests per 24-hour period for most editions. A full refresh of four objects (Opportunity, OpportunityHistory, Task, Event) where each object has thousands of records and requires multiple paginated API calls can consume a substantial portion of that daily quota. Running the pipeline on a schedule (e.g., hourly) amplifies the consumption: 24 runs/day × 4 objects × N pages per object. If the org limit is reached, subsequent API calls return HTTP 403 with `REQUEST_LIMIT_EXCEEDED`. The pipeline fails but the error message from Salesforce is clear — the danger is scheduling too aggressively before measuring actual consumption.

**Why it happens:**
Full refresh is inherently expensive compared to incremental. Without measuring actual API call consumption for a given org's data volume, teams schedule based on data freshness requirements without knowing the cost. The pipeline is built first, scheduling is configured later, and the rate limit is only discovered in production.

**How to avoid:**
During development, count the actual number of API calls consumed for a single full refresh across all four objects. Log the count. Set the schedule frequency only after confirming the daily budget allows for the desired runs with sufficient headroom (aim for < 50% of the daily limit). Use the Nango proxy's built-in retry capability (`Retry-On: 403,429` header) with exponential backoff to handle transient throttling. Add a Dagster alert (asset check or sensor) that detects `REQUEST_LIMIT_EXCEEDED` responses and pauses the schedule automatically.

**Warning signs:**
- No logging of the number of API calls made per pipeline run
- Schedule frequency is set before measuring actual API call consumption
- Nango proxy requests have no retry or backoff configuration
- HTTP 403 from Salesforce with body containing `REQUEST_LIMIT_EXCEEDED`

**Phase to address:**
Salesforce asset implementation phase. API call counting and schedule frequency determination must happen before the pipeline is put on a production schedule.

---

### Pitfall 8: Dagster Internal Database Instance Migrate Required After Version Upgrades

**What goes wrong:**
Dagster frequently changes its internal database schema between minor releases. After upgrading the `dagster` package (e.g., from 1.8 to 1.9), the existing Dagster instance — whether SQLite or PostgreSQL — may be on a stale schema revision. The upgrade does not automatically migrate the instance; the user must run `dagster instance migrate` manually. If this step is skipped, Dagster silently misbehaves: runs may not appear in the UI, schedule state is lost, or the daemon fails to start. The failure mode depends on what schema changes were made — it is not always a hard crash.

**Why it happens:**
`pip install --upgrade dagster` updates the code but not the instance schema. The migration step is documented but easy to miss, especially when dependency upgrades happen as part of a broader `uv lock --upgrade` or `pip install -U` operation.

**How to avoid:**
After every Dagster version upgrade (including patch versions), run `dagster instance migrate` against the configured `$DAGSTER_HOME`. Add this as a step in the project's upgrade runbook. If using Docker, add `dagster instance migrate` as part of the container startup command (it is idempotent — safe to run even if no migration is needed).

**Warning signs:**
- `dagster dev` starts but no runs appear in the UI after the first materialization
- `dagster schedule list` shows schedules as stopped even though they were previously running
- Error messages mentioning schema revision mismatch or missing columns in Dagster's internal tables
- The Dagster version in `pyproject.toml` changed but `dagster instance migrate` was not run

**Phase to address:**
Dagster local dev setup phase. Document the upgrade procedure. The setup phase is not complete until the migration step is part of the documented runbook.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| SQLite for Dagster internal storage | Zero config, works out of box | Locks and corruption under concurrent asset runs | Never — migrate to PostgreSQL from the start |
| Hardcoded `connection_id` in Nango client | Simpler local dev | Breaks for every customer org in production | Never — always source from config/env |
| Full refresh without TRUNCATE-INSERT | Simpler insert logic | Duplicate records accumulate over time | Never once real production data exists |
| `os.getenv()` instead of `EnvVar()` for Dagster resources | Familiar Python pattern | Environment variables not visible in Dagster UI, fails silently in cloud | Never in Dagster resource code |
| Offset-based SOQL pagination | Familiar SQL pagination | Silently truncates at 2000 records | Never — Salesforce does not support OFFSET > 2000 |
| Mounting Dagster inside FastAPI | Single process for dev | Assets fail to load, static routes break | Never — run as separate processes |
| Skipping `dagster instance migrate` after upgrades | Faster upgrade process | Silent misbehavior — lost run history, broken schedules | Never in any persistent environment |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Nango proxy | Forgetting `Provider-Config-Key` or `Connection-Id` header | Build a `NangoProxyClient` resource that enforces all three required headers at construction time |
| Nango proxy | Treating the proxy as a pass-through URL instead of a header-authenticated gateway | The proxy rewrites `Authorization` for the downstream API — do not send Salesforce credentials directly |
| Nango proxy | Using the Nango Node SDK patterns in Python | Nango has no official Python SDK; use `httpx` with custom headers matching the proxy API spec |
| Salesforce REST API | Using OFFSET pagination | Follow `nextRecordsUrl` from the response body; OFFSET is capped at 2000 |
| Salesforce REST API | Constructing the instance URL from config | The Nango proxy provides the correct base URL automatically — use relative paths (`/services/data/v60.0/query`) |
| Dagster + PostgreSQL | Using the app's PostgreSQL database for Dagster internal storage | Use a separate database or schema for Dagster internal tables to prevent Dagster schema management from conflicting with Alembic migrations |
| Dagster + FastAPI | Trying to mount Dagster UI inside FastAPI | Run as separate processes on different ports; do not use `app.mount()` |
| Dagster resources | Using `os.getenv()` in resource bodies | Use `dagster.EnvVar("VAR_NAME")` so Dagster can resolve and display config in the UI |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Full refresh without batching inserts | Single-transaction insert of 10k+ records causes PostgreSQL lock timeout | Batch inserts in chunks of 500-1000 records within the TRUNCATE-INSERT transaction | > 5,000 records per object |
| Loading entire Salesforce response into memory before inserting | OOM in the Dagster process for large orgs | Stream pages from Salesforce and insert each page before fetching the next | > 50,000 records per object |
| No Dagster run concurrency limit | Four assets running simultaneously each open a database connection; connection pool exhausted | Set `max_concurrent_runs` in `dagster.yaml`; configure assets to share a resource pool | > 3 concurrent asset materializations |
| Salesforce full refresh on a per-hour schedule | API call quota exhausted by midday | Measure calls per run; start with daily or 6-hour schedules; increase only after measuring | When daily quota < (runs/day × calls/run) |
| Dagster event log bloat | Dagster's internal storage grows unboundedly with each run; queries slow | Configure event log retention via `dagster.yaml`; use PostgreSQL storage with cleanup schedule | After hundreds of pipeline runs |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| `NANGO_SECRET_KEY` hardcoded in Dagster resource | Credential exposed in source code and Dagster UI | Use `EnvVar("NANGO_SECRET_KEY")` exclusively; never commit the value |
| `connection_id` hardcoded per customer in pipeline code | Different customers' data can be inadvertently swapped | Source `connection_id` from run config or environment; never hardcode per-customer identifiers |
| Dagster webserver accessible without auth on public network | Anyone can trigger pipeline runs | Use Dagster+'s built-in auth or restrict the Dagster port to private network / VPN only |
| PostgreSQL credentials visible in Dagster `dagster.yaml` | Credentials committed to source control | Use `{ env: VAR_NAME }` substitution syntax in `dagster.yaml` for all credential values |
| No validation of Salesforce record count against expected range | Truncated full refresh (e.g., API error after 1000 records) replaces good data with partial data | Validate record count is above a minimum threshold before committing the TRUNCATE-INSERT transaction |

---

## UX Pitfalls

This milestone is a backend pipeline with no end-user UI. Relevant "UX" here means developer/operator experience.

| Pitfall | Operator Impact | Better Approach |
|---------|----------------|-----------------|
| No asset metadata on materialization | Operators cannot see how many records were synced per run | Use `dagster.Output(value=..., metadata={"record_count": n})` to log counts to the Dagster UI |
| Dagster schedules start in RUNNING state locally | Local dev triggers production-frequency jobs accidentally | Check `os.getenv("DAGSTER_IS_DEV_CLI") == "1"` and set schedules to stopped in dev; running in production |
| Asset failures show generic Python tracebacks | Operator cannot distinguish Salesforce auth failure from data error | Catch `NangoAuthError`, `SalesforceRateLimitError`, etc. and re-raise with structured context |
| No asset checks for data completeness | Pipeline shows green even if Salesforce returned 0 records (silent auth failure) | Add an `@asset_check` that fails if `record_count == 0` for any of the four objects |

---

## "Looks Done But Isn't" Checklist

- [ ] **Dagster storage:** `dagster.yaml` configures PostgreSQL storage — not SQLite. Verified by materializing all four assets simultaneously with no lock errors.
- [ ] **Nango headers:** All three required Nango proxy headers (`Authorization`, `Connection-Id`, `Provider-Config-Key`) are present on every request. No hardcoded `connection_id` literals.
- [ ] **Full pagination:** Pipeline fetches all pages via `nextRecordsUrl` loop. Verified against an org with > 2000 records of at least one object. No `OFFSET` in any SOQL query.
- [ ] **TRUNCATE-INSERT:** Re-running an asset twice yields the same row count both times. Verified by comparing `COUNT(*)` before and after a second materialization.
- [ ] **EnvVar usage:** All Dagster resource configurations use `EnvVar(...)` — not `os.getenv(...)`. Confirmed by searching for `os.getenv` in Dagster-specific code files.
- [ ] **Separate process model:** Dagster and FastAPI run on different ports as separate processes. No `app.mount()` of Dagster in `app.py`.
- [ ] **Instance migrate step documented:** The project runbook includes `dagster instance migrate` after every `dagster` package upgrade. Present in project documentation.
- [ ] **Record count metadata:** Every asset materialization logs record count via `Output(metadata={"record_count": n})`. Visible in the Dagster UI materialize history.
- [ ] **Dev schedule behavior:** Schedules are stopped by default in local dev (`DAGSTER_IS_DEV_CLI=1`) and running in production. Verified by checking `dagster schedule list` in both environments.
- [ ] **Separate Dagster database:** Dagster internal tables live in a separate PostgreSQL database or schema from `data_records` and `audit_log`. Alembic migrations do not interfere with Dagster's own schema.

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| SQLite lock corrupts Dagster event log | MEDIUM | Delete `$DAGSTER_HOME` to reset the local instance; all run history is lost; data in PostgreSQL is unaffected |
| Duplicate records from missing TRUNCATE-INSERT | MEDIUM | Run `DELETE FROM data_records WHERE model_name = :model AND connection_id = :conn` to clear the table; re-materialize |
| Wrong `connection_id` synced wrong customer's data | HIGH | Identify which runs used the wrong ID; delete those rows from `data_records`; fix the config; re-materialize |
| Salesforce API quota exhausted | LOW | Wait for the 24-hour reset; reduce schedule frequency before re-enabling; add quota monitoring |
| Dagster instance schema out of date after upgrade | LOW | Run `dagster instance migrate`; run history may be incomplete but pipeline execution resumes normally |
| `nextRecordsUrl` pagination bug silently truncated data | MEDIUM | Identify the last correct full refresh; delete affected rows; fix pagination; re-materialize |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Dagster SQLite concurrency locks | Dagster local dev setup | Materialize all four assets simultaneously; zero lock errors in logs |
| Nango proxy missing headers | Nango proxy client | Unit test validates all three headers present; test for missing header raises `ConfigurationError` |
| SOQL OFFSET truncation | Nango proxy client (pagination) | Test with mocked `nextRecordsUrl` verifies second page is fetched |
| Full refresh duplicate records | Salesforce asset implementation | Run same asset twice; COUNT(*) before and after second run is equal |
| Dev/cloud env var config | Dagster local dev setup | All resources use `EnvVar`; grep for `os.getenv` in Dagster code returns no results |
| Port conflict with FastAPI | Dagster local dev setup | Both services start simultaneously; no port binding error |
| Salesforce API rate limits | Salesforce asset implementation | Log API call count per run; schedule frequency set based on measured consumption |
| Dagster instance migrate | Dagster local dev setup | Upgrade runbook documented; `dagster instance migrate` in Docker startup command |

---

## Carried-Forward Pitfalls (from v0.2.0 Research)

The following pitfalls from prior milestones remain relevant for this milestone:

**PostgreSQL connection pool:** The Dagster pipeline shares the PostgreSQL instance with the FastAPI service. Connection pool exhaustion from concurrent Dagster runs can starve FastAPI request processing. Use a separate PostgreSQL database or configure Dagster with its own connection pool budget. See prior PITFALLS.md for connection pool configuration details.

**Transaction boundaries:** The TRUNCATE-INSERT pattern for full refresh must execute in a single atomic transaction. If the insert fails partway through, the TRUNCATE should roll back — leaving the old data intact rather than leaving the table empty. Use `async with conn.begin()` wrapping both the DELETE and INSERT operations.

**Kernel purity:** If the Dagster pipeline calls into the kernel (e.g., reusing `AddData` command), the kernel must not import Dagster. Dagster is a driving adapter. The kernel must remain free of all external dependencies. Verify `src/kernel/` has no `dagster` imports.

**Alembic migrations:** Any new PostgreSQL tables required by the Dagster pipeline (if adding new tables, not using existing `data_records`) must go through Alembic migrations, not be created ad hoc in the pipeline code. See prior PITFALLS.md for migration pitfall details.

---

## Sources

- [Dagster — SQLite vs PostgreSQL for internal storage (community discussion)](https://github.com/dagster-io/dagster/discussions/8552)
- [Dagster — Event database is locked (community discussion)](https://discuss.dagster.io/t/16769182)
- [Dagster — Mounting Dagster App to existing FastAPI App does not work (GitHub Issue #12797)](https://github.com/dagster-io/dagster/issues/12797)
- [Dagster — Transitioning from development to production](https://docs.dagster.io/guides/operate/dev-to-prod)
- [Dagster — Using environment variables and secrets](https://docs.dagster.io/guides/operate/configuration/using-environment-variables-and-secrets)
- [Dagster — workspace.yaml reference](https://docs.dagster.io/deployment/code-locations/workspace-yaml)
- [Dagster — dagster_cloud.yaml reference](https://docs.dagster.io/deployment/code-locations/dagster-cloud-yaml)
- [Dagster — Running out of memory with large datasets (discussion #4669)](https://github.com/dagster-io/dagster/discussions/4669)
- [Dagster — Assets that can be updated incrementally or fully refreshed (issue #13618)](https://github.com/dagster-io/dagster/issues/13618)
- [Nango proxy — GET requests API reference](https://nango.dev/docs/reference/api/proxy/get)
- [Nango — Salesforce integration page](https://nango.dev/integrations/all/salesforce)
- [Salesforce — SOQL and SOSL limits (OFFSET maximum 2000)](https://developer.salesforce.com/docs/atlas.en-us.salesforce_app_limits_cheatsheet.meta/salesforce_app_limits_cheatsheet/salesforce_app_limits_platform_soslsoql.htm)
- [Salesforce — API request limits and allocations](https://developer.salesforce.com/docs/atlas.en-us.salesforce_app_limits_cheatsheet.meta/salesforce_app_limits_cheatsheet/salesforce_app_limits_platform_api.htm)
- [Salesforce — Workaround for OFFSET 2000 limit](https://help.salesforce.com/s/articleView?id=000387840&language=en_US&type=1)
- [Dagster — Data pipelines key challenges (community analysis)](https://sairamkrish.medium.com/dagster-list-of-pain-points-e528ea139777)

---
*Pitfalls research for: Dagster-based Salesforce data pipeline on existing Python FastAPI service with Nango proxy authentication*
*Researched: 2026-03-20*
