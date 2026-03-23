# Phase 10: Dagster Infrastructure - Research

**Researched:** 2026-03-23
**Domain:** Dagster orchestration infrastructure setup with PostgreSQL storage
**Confidence:** HIGH

## Summary

Phase 10 establishes the Dagster orchestration infrastructure that all subsequent v0.3 phases depend on. The phase is narrow in scope: project scaffold, PostgreSQL storage configuration, and a placeholder asset to verify the end-to-end setup. No Salesforce-related code is introduced. The three requirements (DAGSTER-01, DAGSTER-02, DAGSTER-03) form a dependency chain where the scaffold must exist before storage can be configured, and both must be correct before `dagster dev` can boot successfully.

The recommended implementation follows Dagster's official project structure patterns: a `dagster/` directory at project root containing `definitions.py` as the entry point, with `workspace.yaml` and `dagster.yaml` at project root. PostgreSQL storage replaces Dagster's default SQLite to prevent the well-documented concurrent materialization lock errors. The storage configuration uses a separate `dagster` schema in the existing database to avoid Alembic migration conflicts with the FastAPI application's tables.

**Primary recommendation:** Create minimal Dagster scaffold with PostgreSQL storage configured from day one. Validate with a `ping_database` placeholder asset that confirms both the webserver boots and the storage backend is functional.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Dagster code lives in `dagster/` at project root (not inside `src/`)
- Nested internal structure: `definitions.py` + `assets/` + `resources/`
- Clear process boundary from existing hexagonal architecture
- Dagster metadata stored in same database, separate schema (`dagster`)
- Schema created manually: `CREATE SCHEMA dagster;`
- Avoids Alembic conflicts with existing data-hub migrations
- Dagster env vars documented in `dagster/.env.example` (separate from root `.env.example`)
- Separate `DAGSTER_DATABASE_URL` env var (not shared with FastAPI's `DATABASE_URL`)
- All resource config uses `dg.EnvVar(...)` pattern (not `os.getenv`)
- Dagster webserver runs on port 3000 (Dagster default)
- FastAPI continues on port 8000
- Include `ping_database` asset to verify PostgresResource works end-to-end
- Add `dagster`, `dagster-postgres`, `dagster-webserver` to main `[project.dependencies]`
- Developers run `dagster dev` directly from project root

### Claude's Discretion
- Exact dagster.yaml configuration structure
- workspace.yaml format details
- PostgresResource implementation approach

### Deferred Ideas (OUT OF SCOPE)
None - discussion stayed within phase scope

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DAGSTER-01 | Dagster project scaffold with definitions.py and workspace.yaml | Standard Stack (dagster 1.12.20), Architecture Patterns (project structure), Code Examples (workspace.yaml, definitions.py) |
| DAGSTER-02 | dagster.yaml with PostgreSQL storage (not SQLite) | Standard Stack (dagster-postgres 0.28.20), Architecture Patterns (dagster.yaml structure), Don't Hand-Roll (storage backend), Common Pitfalls (SQLite lock corruption) |
| DAGSTER-03 | dagster dev boots locally without errors | Architecture Patterns (directory layout), Code Examples (ping_database asset), Validation Architecture |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| dagster | 1.12.20 | Orchestration runtime | Official framework; software-defined assets provide lineage, retry semantics, metadata out of the box |
| dagster-postgres | 0.28.20 | PostgreSQL storage backend | Replaces SQLite to prevent concurrent materialization lock errors; co-versioned with dagster |
| dagster-webserver | 1.12.20 | Local development UI | Serves the Dagster UI at localhost:3000; co-versioned with dagster |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| psycopg2-binary | 2.9.9 | Sync PostgreSQL driver | Already in pyproject.toml; used by Dagster resources for sync database operations |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| dagster-postgres storage | Default SQLite | SQLite corrupts under concurrent runs; never use for anything beyond single-developer experimentation |
| Separate dagster schema | Separate database | Extra infrastructure overhead; same-database-different-schema is simpler for local dev |

**Installation:**
```bash
uv add dagster==1.12.20 dagster-postgres==0.28.20 dagster-webserver==1.12.20
```

**Version verification:** Versions confirmed against PyPI on 2026-03-23. dagster and dagster-webserver are co-versioned; dagster-postgres follows its own versioning (0.28.x).

## Architecture Patterns

### Recommended Project Structure
```
data-hub/                          # Project root
├── dagster/                       # Dagster code (separate from src/)
│   ├── __init__.py
│   ├── definitions.py             # Definitions entry point
│   ├── assets/
│   │   ├── __init__.py
│   │   └── ping_database.py       # Placeholder asset for validation
│   └── resources/
│       ├── __init__.py
│       └── postgres.py            # PostgresResource ConfigurableResource
├── workspace.yaml                 # Points to dagster.definitions module
├── dagster.yaml                   # Instance config with PostgreSQL storage
├── src/                           # Existing FastAPI hexagonal code (unchanged)
└── pyproject.toml                 # Updated with dagster dependencies
```

### Pattern 1: Definitions Entry Point
**What:** Single `Definitions` object in `definitions.py` registers all assets and resources.
**When to use:** Always. This is Dagster's standard entry point pattern.
**Example:**
```python
# dagster/definitions.py
# Source: https://docs.dagster.io/guides/build/projects/project-structure/project-overview
import dagster as dg
from dagster.assets import ping_database
from dagster.resources.postgres import PostgresResource

defs = dg.Definitions(
    assets=[ping_database],
    resources={
        "postgres_db": PostgresResource(
            connection_uri=dg.EnvVar("DAGSTER_DATABASE_URL"),
        ),
    },
)
```

### Pattern 2: ConfigurableResource with EnvVar
**What:** Resource configuration uses `dg.EnvVar(...)` for environment-specific values. Never use `os.getenv()`.
**When to use:** All resource configuration that differs between environments.
**Example:**
```python
# dagster/resources/postgres.py
# Source: https://docs.dagster.io/guides/build/external-resources/configuring-resources
import dagster as dg
import psycopg2
from contextlib import contextmanager
from pydantic import PrivateAttr
from typing import Any

class PostgresResource(dg.ConfigurableResource):
    connection_uri: str
    _connection: Any = PrivateAttr(default=None)

    @contextmanager
    def yield_for_execution(self, context: dg.InitResourceContext):
        conn = psycopg2.connect(self.connection_uri)
        try:
            self._connection = conn
            yield self
        finally:
            conn.close()

    def execute(self, query: str) -> list[dict]:
        with self._connection.cursor() as cur:
            cur.execute(query)
            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]
```

### Pattern 3: PostgreSQL Storage with Schema Isolation
**What:** dagster.yaml configures PostgreSQL storage using the `params` option to set `search_path` to a dedicated schema.
**When to use:** When sharing a database with another application (FastAPI in this case).
**Example:**
```yaml
# dagster.yaml
# Source: https://docs.dagster.io/api/libraries/dagster-postgres + GitHub issue #15508
storage:
  postgres:
    postgres_db:
      hostname:
        env: DAGSTER_PG_HOST
      username:
        env: DAGSTER_PG_USER
      password:
        env: DAGSTER_PG_PASSWORD
      db_name:
        env: DAGSTER_PG_DB
      port: 5432
      params:
        options: -c search_path=dagster
```

### Anti-Patterns to Avoid
- **Embedding Dagster in FastAPI:** Never use `app.mount()` to embed Dagster webserver in FastAPI. They are separate processes. (Confirmed broken: GitHub issue #12797)
- **Using `os.getenv()` in resources:** Breaks Dagster Cloud deployment. Always use `dg.EnvVar(...)`.
- **Sharing `DATABASE_URL` with FastAPI:** Dagster needs a sync connection string; FastAPI uses async. Keep them separate.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Dagster metadata storage | Custom SQLAlchemy tables | dagster-postgres storage config | Handles run history, event logs, schedules; migrates automatically with `dagster instance migrate` |
| Connection pooling | Manual psycopg2 pool | `yield_for_execution` context manager | Dagster manages resource lifecycle per-run automatically |
| Project scaffolding | Manual directory structure | `dagster project scaffold` or copy standard pattern | Dagster CLI generates correct structure with proper imports |

**Key insight:** Dagster's storage backend is complex (run storage, event log storage, schedule storage). Configuring `dagster-postgres` handles all three with a single `storage.postgres` block.

## Common Pitfalls

### Pitfall 1: SQLite Storage Corruption Under Concurrent Runs
**What goes wrong:** Multiple assets materializing simultaneously cause SQLite lock errors ("database is locked").
**Why it happens:** SQLite has limited concurrent write support. Dagster's default SQLite storage fails under production-like workloads.
**How to avoid:** Configure PostgreSQL storage in dagster.yaml from day one. Never use SQLite for anything beyond single-developer experimentation.
**Warning signs:** Sporadic "database is locked" errors in dagster dev logs; lost run history.

### Pitfall 2: os.getenv() Instead of EnvVar
**What goes wrong:** Resources work locally but fail in Dagster Cloud deployment.
**Why it happens:** Dagster Cloud injects environment variables differently. `EnvVar` understands this; `os.getenv()` runs at import time before injection.
**How to avoid:** Grep for `os.getenv` in dagster code before every commit. Replace with `dg.EnvVar(...)`.
**Warning signs:** Environment variables are empty or wrong in cloud deployments despite being set in the UI.

### Pitfall 3: Missing `dagster instance migrate` After Upgrades
**What goes wrong:** Silent misbehavior: lost run history, broken schedules, no clear error message.
**Why it happens:** Dagster's storage schema changes between versions. The upgrade path requires explicit migration.
**How to avoid:** Add `dagster instance migrate` to upgrade runbook and Docker startup commands.
**Warning signs:** Dagster boots but runs or schedules are mysteriously missing.

### Pitfall 4: Schema Not Created Before First Run
**What goes wrong:** Dagster fails to start with "schema dagster does not exist" errors.
**Why it happens:** The `search_path=dagster` option assumes the schema exists. Dagster-postgres does not auto-create schemas.
**How to avoid:** Document and execute `CREATE SCHEMA dagster;` as a prerequisite step. Add to setup instructions.
**Warning signs:** Connection errors mentioning schema on first `dagster dev` run.

### Pitfall 5: Port Conflict with FastAPI
**What goes wrong:** `dagster dev` fails to bind to port 3000 or conflicts with another service.
**Why it happens:** Port 3000 is popular (React dev servers, other tools).
**How to avoid:** Document that Dagster uses port 3000. Use `--port` flag or `DAGSTER_WEBSERVER_PORT` env var if needed.
**Warning signs:** "Address already in use" error on startup.

## Code Examples

Verified patterns from official sources:

### workspace.yaml
```yaml
# Source: https://docs.dagster.io/guides/build/projects/workspaces/workspace-yaml
load_from:
  - python_module:
      module_name: dagster.definitions
```

### dagster.yaml with PostgreSQL Storage
```yaml
# Source: https://docs.dagster.io/api/libraries/dagster-postgres
# Schema workaround: https://github.com/dagster-io/dagster/issues/15508
storage:
  postgres:
    postgres_db:
      hostname:
        env: DAGSTER_PG_HOST
      username:
        env: DAGSTER_PG_USER
      password:
        env: DAGSTER_PG_PASSWORD
      db_name:
        env: DAGSTER_PG_DB
      port: 5432
      params:
        options: -c search_path=dagster
```

### definitions.py Entry Point
```python
# Source: https://docs.dagster.io/guides/build/projects/project-structure/project-overview
import dagster as dg
from dagster.assets.ping_database import ping_database
from dagster.resources.postgres import PostgresResource

defs = dg.Definitions(
    assets=[ping_database],
    resources={
        "postgres_db": PostgresResource(
            connection_uri=dg.EnvVar("DAGSTER_DATABASE_URL"),
        ),
    },
)
```

### Placeholder ping_database Asset
```python
# dagster/assets/ping_database.py
import dagster as dg
from dagster.resources.postgres import PostgresResource

@dg.asset
def ping_database(postgres_db: PostgresResource) -> dg.MaterializeResult:
    """Placeholder asset to verify PostgresResource works end-to-end.

    Removed after Phase 11 introduces real assets.
    """
    result = postgres_db.execute("SELECT 1 as ping")
    return dg.MaterializeResult(
        metadata={
            "ping_result": result[0]["ping"],
            "status": "connected",
        }
    )
```

### dagster/.env.example
```bash
# Dagster PostgreSQL Storage (separate from FastAPI DATABASE_URL)
DAGSTER_DATABASE_URL=postgresql://user:password@localhost:5432/datahub

# Individual components for dagster.yaml storage config
DAGSTER_PG_HOST=localhost
DAGSTER_PG_USER=user
DAGSTER_PG_PASSWORD=password
DAGSTER_PG_DB=datahub
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `@pipeline` + `@solid` | `@asset` | Dagster 1.0 (2022) | Software-defined assets are the recommended abstraction |
| `IOManager` for DB writes | Custom asset logic | Dagster 1.3+ | IOManagers are for data interchange, not persistence |
| `ModeDefinition` | `Definitions` + resources | Dagster 1.0 | Single entry point pattern is simpler |
| `workspace.yaml` with `python_file` | `python_module` preferred | 2024 | Module loading is more robust across environments |

**Deprecated/outdated:**
- `@pipeline`, `@solid`: Replaced by `@asset` and `@op`. Still work but not recommended.
- `ModeDefinition`: Replaced by resource configuration in `Definitions`.

## Open Questions

1. **Connection string format for psycopg2**
   - What we know: FastAPI uses `postgresql+asyncpg://` format
   - What's unclear: Does psycopg2 accept the same URL or need `postgresql://` (no driver suffix)?
   - Recommendation: Use `postgresql://` for DAGSTER_DATABASE_URL. psycopg2 does not use SQLAlchemy URL format.

2. **DAGSTER_HOME location**
   - What we know: If not set, Dagster uses a temp directory (lost on exit). If set, persists run history.
   - What's unclear: Should we set DAGSTER_HOME for local dev?
   - Recommendation: Leave unset for phase 10 (PostgreSQL storage handles persistence). Document for later phases if needed.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.3 with pytest-asyncio |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ --cov=src` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DAGSTER-01 | definitions.py loads and Definitions object is valid | smoke | `python -c "from dagster.definitions import defs; assert defs"` | Wave 0 |
| DAGSTER-02 | dagster.yaml configures PostgreSQL storage | manual | Inspect dagster.yaml, verify storage.postgres block present | N/A - config file |
| DAGSTER-03 | dagster dev boots without errors | smoke | `timeout 10 dagster dev` exits 0 or 124 (timeout = success) | Wave 0 |

### Sampling Rate
- **Per task commit:** `python -c "from dagster.definitions import defs"` (instant import check)
- **Per wave merge:** `dagster dev --help` + manual boot test
- **Phase gate:** Full `dagster dev` boot, materialize ping_database asset via UI

### Wave 0 Gaps
- [ ] `dagster/` directory structure - all files created in this phase
- [ ] `workspace.yaml` - created in this phase
- [ ] `dagster.yaml` - created in this phase
- [ ] PostgreSQL schema: `CREATE SCHEMA dagster;` - manual prerequisite

## Sources

### Primary (HIGH confidence)
- [dagster on PyPI](https://pypi.org/project/dagster/) - version 1.12.20 confirmed 2026-03-23
- [dagster-postgres on PyPI](https://pypi.org/project/dagster-postgres/) - version 0.28.20 confirmed 2026-03-23
- [dagster-webserver on PyPI](https://pypi.org/project/dagster-webserver/) - version 1.12.20 confirmed 2026-03-23
- [Dagster project structure docs](https://docs.dagster.io/guides/build/projects/project-structure/project-overview) - definitions.py entry point pattern
- [Dagster workspace.yaml reference](https://docs.dagster.io/guides/build/projects/workspaces/workspace-yaml) - python_module configuration
- [Dagster dagster.yaml reference](https://docs.dagster.io/deployment/oss/dagster-yaml) - instance configuration
- [dagster-postgres API docs](https://docs.dagster.io/api/libraries/dagster-postgres) - PostgreSQL storage configuration
- [Dagster environment variables guide](https://docs.dagster.io/guides/operate/configuration/using-environment-variables-and-secrets) - EnvVar pattern
- [Dagster external resources guide](https://docs.dagster.io/guides/build/external-resources/configuring-resources) - ConfigurableResource pattern
- [Dagster managing resource state](https://docs.dagster.io/guides/build/external-resources/managing-resource-state) - yield_for_execution pattern

### Secondary (MEDIUM confidence)
- [GitHub issue #15508](https://github.com/dagster-io/dagster/issues/15508) - schema configuration workaround via params.options
- [GitHub issue #12797](https://github.com/dagster-io/dagster/issues/12797) - confirms app.mount() of Dagster webserver is broken
- [Dagster running locally docs](https://docs.dagster.io/deployment/oss/deployment-options/running-dagster-locally) - dagster dev command behavior

### Tertiary (LOW confidence)
- [Dagster SQLite vs PostgreSQL discussion](https://github.com/dagster-io/dagster/discussions/8552) - community reports of SQLite lock issues

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All packages verified on PyPI with exact versions
- Architecture: HIGH - Patterns verified against official Dagster docs
- Pitfalls: HIGH - SQLite lock issue is well-documented; EnvVar pattern is explicit in docs

**Research date:** 2026-03-23
**Valid until:** 2026-04-23 (Dagster releases frequently but core patterns are stable)

---
*Research completed: 2026-03-23*
*Ready for planning: yes*
