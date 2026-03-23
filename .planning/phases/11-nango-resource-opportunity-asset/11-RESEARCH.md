# Phase 11: Nango Resource & Opportunity Asset - Research

**Researched:** 2026-03-23
**Domain:** Dagster ConfigurableResource + Nango Records API + PostgreSQL persistence
**Confidence:** HIGH

## Summary

This phase implements the first real Dagster asset that validates the end-to-end pattern: NangoResource fetches pre-synced Opportunity records from Nango's Records API, and persists them to PostgreSQL with full refresh idempotency. The pattern established here will be replicated for all subsequent Salesforce assets in Phase 12.

The core technical challenges are: (1) implementing NangoResource as a ConfigurableResource with proper lifecycle management following the existing PostgresResource pattern, (2) handling cursor-based pagination from Nango's Records API, and (3) achieving idempotent full refresh using DELETE+INSERT within a transaction.

**Primary recommendation:** Use `httpx` for HTTP client (already in dev dependencies, supports both sync/async), follow the existing `yield_for_execution` pattern from PostgresResource, and use `psycopg2.extras.execute_values` for efficient batch inserts.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions

**NangoResource Design:**
- Single env var configuration: `NANGO_SECRET_KEY` only (base URL defaults to https://api.nango.dev)
- Raw HTTP calls using requests/httpx - no nango Python SDK dependency
- Connection ID passed as method parameter: `nango.get_records(model='Opportunity', connection_id='xxx')`
- Connection ID sourced from `NANGO_CONNECTION_ID` environment variable at runtime
- Raise exceptions on API errors - let Dagster handle retry/failure naturally
- NangoResource handles pagination internally - `get_records()` returns all records by following cursor

**Table Schema:**
- Raw JSONB storage: single `data` column with full Nango record
- Dagster-managed DDL: asset creates table with `CREATE TABLE IF NOT EXISTS` at materialization
- Tables live in `public` schema (same as data-hub tables, separate from 'dagster' metadata schema)
- Columns: `salesforce_id` + `connection_id` (composite PK), `data` (JSONB), `synced_at` (timestamp)
- Multi-tenant ready from the start

**Idempotency Strategy:**
- DELETE + INSERT in transaction: `DELETE WHERE connection_id=X`, then INSERT all records
- Atomic operation handles removed records correctly
- Batch inserts using executemany() or VALUES list for performance

**Record Fetching:**
- Model name hardcoded per asset: Opportunity asset fetches model='Opportunity'
- Store raw JSON exactly as Nango returns - no transformation or validation
- Validation deferred to query time

### Claude's Discretion

- HTTP library choice (requests vs httpx) - **Recommendation: httpx**
- Exact pagination cursor handling - **See Nango API section below**
- Batch size for inserts - **Recommendation: 100 (execute_values default page_size)**
- Error message formatting

### Deferred Ideas (OUT OF SCOPE)

- Multi-connection partitioning (SCHED-02) - schema supports it, scheduling deferred to v0.4
- Incremental loading (ADV-01) - full refresh first, cursor-based loading later
- nango Python SDK - may revisit if raw HTTP becomes unwieldy

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| NANGO-01 | NangoResource ConfigurableResource wrapping existing NangoClient | yield_for_execution pattern, EnvVar configuration, httpx client |
| NANGO-02 | Fetch records via Nango Records API (GET /records) | Cursor-based pagination, Bearer auth, required headers |
| ASSET-01 | Opportunity asset with full refresh to `salesforce_opportunities` table | DELETE+INSERT idempotency, execute_values batch inserts, JSONB schema |
| OBS-01 | MaterializeResult with row count metadata on each asset | `dagster/row_count` metadata key for Dagster UI visibility |

</phase_requirements>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| dagster | 1.12.20 | Asset orchestration | Already installed from Phase 10 |
| httpx | >=0.28.1 | HTTP client for Nango API | Already in dev deps, supports sync/async, modern API |
| psycopg2-binary | >=2.9.9 | PostgreSQL driver | Already installed, used by PostgresResource |
| psycopg2.extras | (bundled) | execute_values for batch inserts | 10x faster than executemany |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| json (stdlib) | - | JSON serialization for JSONB | Converting records to JSON strings |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| httpx | requests | requests is simpler but httpx already in deps, supports HTTP/2 |
| execute_values | executemany | executemany is 10-100x slower for bulk inserts |
| Raw SQL | SQLAlchemy | SQLAlchemy adds complexity; psycopg2 direct is simpler for this use case |

**Installation:**
No new dependencies needed - httpx already in dev dependencies, psycopg2-binary already in main dependencies.

To move httpx to main dependencies (optional but recommended):
```bash
# In pyproject.toml, move httpx from [dependency-groups].dev to [project].dependencies
```

## Architecture Patterns

### Recommended Project Structure

```
dagster_pipelines/
├── definitions.py           # Dagster Definitions with assets + resources
├── assets/
│   ├── __init__.py
│   ├── ping_database.py     # Remove after Phase 11 complete
│   └── salesforce/
│       ├── __init__.py
│       └── opportunity.py   # Opportunity asset
└── resources/
    ├── __init__.py
    ├── postgres.py          # Existing PostgresResource
    └── nango.py             # NEW: NangoResource
```

### Pattern 1: ConfigurableResource with yield_for_execution

**What:** Resource lifecycle management using context manager pattern
**When to use:** Resources requiring setup/teardown (HTTP clients, DB connections)
**Example:**
```python
# Source: https://docs.dagster.io/guides/build/external-resources/managing-resource-state
import dagster as dg
import httpx
from contextlib import contextmanager
from pydantic import PrivateAttr

class NangoResource(dg.ConfigurableResource):
    secret_key: str
    base_url: str = "https://api.nango.dev"
    _client: httpx.Client = PrivateAttr()

    @contextmanager
    def yield_for_execution(self, context: dg.InitResourceContext):
        with httpx.Client(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.secret_key}"}
        ) as client:
            self._client = client
            yield self
```

### Pattern 2: Cursor-Based Pagination

**What:** Iterate through all pages of Nango records using `next_cursor`
**When to use:** Fetching complete record sets from Nango
**Example:**
```python
# Source: https://nango.dev/docs/reference/api/sync/records-list
def get_records(self, model: str, connection_id: str) -> list[dict]:
    """Fetch all records for a model, handling pagination."""
    records = []
    cursor = None

    while True:
        params = {"model": model, "limit": 100}
        if cursor:
            params["cursor"] = cursor

        response = self._client.get(
            "/records",
            params=params,
            headers={
                "Connection-Id": connection_id,
                "Provider-Config-Key": "salesforce"  # Integration ID
            }
        )
        response.raise_for_status()
        data = response.json()

        records.extend(data.get("records", []))

        cursor = data.get("next_cursor")
        if not cursor:
            break

    return records
```

### Pattern 3: Idempotent Full Refresh

**What:** DELETE existing + INSERT new records in single transaction
**When to use:** Full refresh assets where records may be removed upstream
**Example:**
```python
# Source: CONTEXT.md decision + psycopg2 docs
def persist_records(
    conn,
    table: str,
    connection_id: str,
    records: list[dict]
) -> int:
    """Idempotent upsert: delete old, insert new, return count."""
    from psycopg2.extras import execute_values
    import json

    with conn.cursor() as cur:
        # Delete existing records for this connection
        cur.execute(
            f"DELETE FROM {table} WHERE connection_id = %s",
            (connection_id,)
        )

        # Prepare values: (salesforce_id, connection_id, data_jsonb)
        values = [
            (record["id"], connection_id, json.dumps(record))
            for record in records
        ]

        # Batch insert
        execute_values(
            cur,
            f"INSERT INTO {table} (salesforce_id, connection_id, data, synced_at) VALUES %s",
            values,
            template="(%s, %s, %s, NOW())"
        )

        conn.commit()
        return len(records)
```

### Pattern 4: Asset with MaterializeResult Metadata

**What:** Return row count in standardized metadata for Dagster UI
**When to use:** Every asset that persists data
**Example:**
```python
# Source: https://docs.dagster.io/guides/build/assets/metadata-and-tags/table-metadata
@dg.asset
def salesforce_opportunities(
    nango: NangoResource,
    postgres_db: PostgresResource
) -> dg.MaterializeResult:
    """Fetch Opportunity records from Nango and persist to PostgreSQL."""
    connection_id = os.getenv("NANGO_CONNECTION_ID")

    # Fetch from Nango
    records = nango.get_records(model="Opportunity", connection_id=connection_id)

    # Persist to PostgreSQL
    row_count = persist_records(
        postgres_db._connection,
        "salesforce_opportunities",
        connection_id,
        records
    )

    return dg.MaterializeResult(
        metadata={
            "dagster/row_count": row_count,
            "connection_id": connection_id,
        }
    )
```

### Anti-Patterns to Avoid

- **Hand-rolling pagination logic repeatedly:** Extract `get_records()` into NangoResource, don't repeat cursor logic in each asset
- **Using executemany for bulk inserts:** Use `execute_values` instead - 10-100x faster
- **Storing connection in resource config:** Connection ID varies per execution, pass as parameter
- **Committing outside transaction:** DELETE and INSERT must be atomic

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP retries | Custom retry loops | httpx built-in retry or raise_for_status | httpx handles connection pooling, timeouts properly |
| JSON serialization | Manual string building | json.dumps() | Handles escaping, Unicode, nested objects |
| Batch inserts | Loop with single INSERT | psycopg2.extras.execute_values | 10-100x performance difference |
| Table DDL | Complex migration system | CREATE TABLE IF NOT EXISTS | Simple, idempotent, Dagster-managed |

**Key insight:** The Nango Records API already provides clean, paginated data. The Python side should be minimal glue code, not a framework.

## Common Pitfalls

### Pitfall 1: Missing Provider-Config-Key Header
**What goes wrong:** Nango API returns 400 Bad Request
**Why it happens:** Provider-Config-Key header is required but easy to forget
**How to avoid:** Include in base headers: `"Provider-Config-Key": "salesforce"`
**Warning signs:** 400 error mentioning "provider" or "integration"

### Pitfall 2: Not Handling Empty Record Sets
**What goes wrong:** Asset fails when Nango returns empty records array
**Why it happens:** No records synced yet, or connection not configured
**How to avoid:** Check for empty list before DELETE+INSERT, return 0 row count
**Warning signs:** Division by zero, empty loop iterations, silent no-ops

### Pitfall 3: Forgetting Transaction Commit
**What goes wrong:** Records appear in debug but disappear on next query
**Why it happens:** psycopg2 connections are not in autocommit mode by default
**How to avoid:** Explicit `conn.commit()` after INSERT
**Warning signs:** Row count correct in asset log but table empty

### Pitfall 4: Salesforce ID as Integer
**What goes wrong:** Data truncation or type errors
**Why it happens:** Salesforce IDs look numeric but are 18-char alphanumeric strings
**How to avoid:** Use `TEXT` type for salesforce_id column, not INTEGER
**Warning signs:** "value too long" errors, data corruption

### Pitfall 5: Cursor vs Modified_after Confusion
**What goes wrong:** Duplicate or missed records during pagination
**Why it happens:** `cursor` and `modified_after` serve different purposes
**How to avoid:** For full refresh, use `cursor` only. `modified_after` is for incremental syncs (deferred to v0.4)
**Warning signs:** Inconsistent row counts between runs

## Code Examples

### NangoResource Implementation

```python
# Source: CONTEXT.md decisions + Dagster docs pattern
"""Nango Records API resource for Dagster assets."""
import dagster as dg
import httpx
from contextlib import contextmanager
from pydantic import PrivateAttr


class NangoResource(dg.ConfigurableResource):
    """Nango Records API client as a Dagster ConfigurableResource.

    Configuration:
        secret_key: Nango secret key from environment (NANGO_SECRET_KEY)
        base_url: API base URL, defaults to https://api.nango.dev
    """
    secret_key: str
    base_url: str = "https://api.nango.dev"

    _client: httpx.Client = PrivateAttr()

    @contextmanager
    def yield_for_execution(self, context: dg.InitResourceContext):
        """Initialize HTTP client for asset execution."""
        with httpx.Client(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.secret_key}"},
            timeout=30.0
        ) as client:
            self._client = client
            yield self

    def get_records(
        self,
        model: str,
        connection_id: str,
        provider_config_key: str = "salesforce"
    ) -> list[dict]:
        """Fetch all records for a model, handling pagination.

        Args:
            model: Nango model name (e.g., 'Opportunity')
            connection_id: Nango connection identifier
            provider_config_key: Integration ID (default: salesforce)

        Returns:
            List of record dicts with _nango_metadata
        """
        records: list[dict] = []
        cursor: str | None = None

        while True:
            params: dict = {"model": model, "limit": 100}
            if cursor:
                params["cursor"] = cursor

            response = self._client.get(
                "/records",
                params=params,
                headers={
                    "Connection-Id": connection_id,
                    "Provider-Config-Key": provider_config_key,
                }
            )
            response.raise_for_status()
            data = response.json()

            records.extend(data.get("records", []))

            cursor = data.get("next_cursor")
            if not cursor:
                break

        return records
```

### Opportunity Asset Implementation

```python
# Source: CONTEXT.md decisions + Dagster MaterializeResult docs
"""Salesforce Opportunity asset with full refresh."""
import os
import json
import dagster as dg
from psycopg2.extras import execute_values

from dagster_pipelines.resources.nango import NangoResource
from dagster_pipelines.resources.postgres import PostgresResource


# Table DDL - executed on first materialization
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS salesforce_opportunities (
    salesforce_id TEXT NOT NULL,
    connection_id TEXT NOT NULL,
    data JSONB NOT NULL,
    synced_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (salesforce_id, connection_id)
);
"""


@dg.asset
def salesforce_opportunities(
    nango: NangoResource,
    postgres_db: PostgresResource
) -> dg.MaterializeResult:
    """Fetch Opportunity records from Nango and persist to PostgreSQL.

    Full refresh strategy: DELETE existing records for connection_id,
    then INSERT all records from Nango.
    """
    connection_id = os.environ["NANGO_CONNECTION_ID"]
    conn = postgres_db._connection

    # Ensure table exists
    with conn.cursor() as cur:
        cur.execute(CREATE_TABLE_SQL)

    # Fetch from Nango
    records = nango.get_records(model="Opportunity", connection_id=connection_id)

    # Full refresh: DELETE + INSERT in transaction
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM salesforce_opportunities WHERE connection_id = %s",
            (connection_id,)
        )

        if records:
            values = [
                (record["id"], connection_id, json.dumps(record))
                for record in records
            ]
            execute_values(
                cur,
                """INSERT INTO salesforce_opportunities
                   (salesforce_id, connection_id, data, synced_at) VALUES %s""",
                values,
                template="(%s, %s, %s, NOW())"
            )

    conn.commit()

    return dg.MaterializeResult(
        metadata={
            "dagster/row_count": len(records),
            "connection_id": connection_id,
        }
    )
```

### Updated Definitions

```python
# Source: Existing definitions.py pattern
"""Dagster definitions entry point."""
import dagster as dg
from dagster_pipelines.assets.salesforce.opportunity import salesforce_opportunities
from dagster_pipelines.resources.postgres import PostgresResource
from dagster_pipelines.resources.nango import NangoResource

defs = dg.Definitions(
    assets=[salesforce_opportunities],
    resources={
        "postgres_db": PostgresResource(
            connection_uri=dg.EnvVar("DAGSTER_DATABASE_URL"),
        ),
        "nango": NangoResource(
            secret_key=dg.EnvVar("NANGO_SECRET_KEY"),
        ),
    },
)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| requests library | httpx | 2023+ | Better async support, HTTP/2, connection pooling |
| executemany | execute_values | psycopg2 2.7+ | 10-100x faster bulk inserts |
| Nango Python SDK | Raw HTTP | Current decision | Fewer dependencies, simpler control |
| TRUNCATE for refresh | DELETE + INSERT | Current decision | Transaction-safe, handles partial failures |

**Deprecated/outdated:**
- `delta` parameter in Nango Records API: Use `modified_after` instead (if needed for incremental)
- Dagster `@op` + `@job` pattern: Use `@asset` for software-defined assets

## Open Questions

1. **httpx in main vs dev dependencies**
   - What we know: httpx is currently in dev dependencies only
   - What's unclear: Whether it should be moved to main dependencies for production
   - Recommendation: Move to main dependencies since NangoResource needs it in production

2. **Provider-Config-Key value**
   - What we know: Must be "salesforce" for Salesforce integrations
   - What's unclear: Whether this should be configurable per-asset
   - Recommendation: Default to "salesforce", could parameterize later if needed

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.3 + pytest-asyncio |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/unit -x` |
| Full suite command | `pytest tests/` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| NANGO-01 | NangoResource creates httpx client with auth header | unit | `pytest tests/unit/test_nango_resource.py::test_resource_config -x` | Wave 0 |
| NANGO-02 | get_records fetches with pagination | unit | `pytest tests/unit/test_nango_resource.py::test_pagination -x` | Wave 0 |
| ASSET-01 | Opportunity asset persists to table | integration | `pytest tests/integration/test_opportunity_asset.py::test_full_refresh -x` | Wave 0 |
| OBS-01 | MaterializeResult has row_count | unit | `pytest tests/unit/test_opportunity_asset.py::test_metadata -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/unit -x --tb=short`
- **Per wave merge:** `pytest tests/`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/unit/test_nango_resource.py` - covers NANGO-01, NANGO-02
- [ ] `tests/unit/test_opportunity_asset.py` - covers OBS-01
- [ ] `tests/integration/test_opportunity_asset.py` - covers ASSET-01
- [ ] Mock fixtures for Nango API responses

## Sources

### Primary (HIGH confidence)

- [Nango Records API Documentation](https://nango.dev/docs/reference/api/sync/records-list) - GET /records endpoint, pagination, headers
- [Dagster ConfigurableResource](https://docs.dagster.io/guides/build/external-resources/defining-resources) - Resource patterns
- [Dagster yield_for_execution](https://docs.dagster.io/guides/build/external-resources/managing-resource-state) - Lifecycle management
- [Dagster MaterializeResult](https://docs.dagster.io/guides/build/assets/metadata-and-tags/table-metadata) - Row count metadata
- [psycopg2.extras.execute_values](https://www.psycopg.org/docs/extras.html) - Batch insert function

### Secondary (MEDIUM confidence)

- [httpx vs requests comparison](https://www.proxy-cheap.com/blog/httpx-vs-requests) - Performance benchmarks
- [execute_values performance](https://naysan.ca/2020/05/09/pandas-to-postgresql-using-psycopg2-bulk-insert-performance-benchmark/) - Bulk insert benchmarks

### Tertiary (LOW confidence)

- None - all critical patterns verified with official documentation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all libraries already in project, versions verified
- Architecture: HIGH - patterns follow existing PostgresResource, verified with Dagster docs
- Pitfalls: HIGH - derived from official API docs and common PostgreSQL patterns

**Research date:** 2026-03-23
**Valid until:** 2026-04-23 (30 days - stable libraries and APIs)
