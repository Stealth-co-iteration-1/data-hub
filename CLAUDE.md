# Claude Code Guidelines for data-hub

## Project Overview

Dagster-based data pipeline for Salesforce ingestion via Nango Records API.

## Architecture: Resource as Bridge

**Critical:** `PostgresResource` is the ONLY bridge to the database. Assets must NEVER import or use psycopg2 directly.

### Allowed in `resources/postgres.py`:
- `import psycopg2`
- `from psycopg2.extensions import connection`
- `from psycopg2.extras import execute_values`
- Direct cursor operations

### NOT allowed in `assets/`:
- Any psycopg2 imports
- Direct cursor access
- Raw SQL execution outside resource methods

Assets interact with the database exclusively through `PostgresResource` public methods.

## Code Style

### Type Annotations
- Always use explicit type parameters for generic classes (e.g., `ConfigurableResource["ClassName"]`, `MaterializeResult[Any]`)
- Use `psycopg2.extensions.connection` for database connection types (only in resources)
- Add runtime checks when accessing optional attributes

### Resource Pattern
- Keep ALL database operations inside `PostgresResource`
- Assets call resource methods: `execute()`, `execute_values()`, `commit()`
- All resource methods must check `if self._connection is None` before use
- Never access `_connection` from outside the resource class

### Asset Pattern
- Each Salesforce asset follows the full refresh pattern: DDL → DELETE → INSERT → commit
- Use `MaterializeResult[Any]` as return type
- Include `dagster/row_count` and `connection_id` in metadata
- Call `postgres_db.execute()` instead of using cursors directly

### Imports in Assets
```python
# Correct - no psycopg2
import os
import json
from typing import Any

import dagster as dg

from resources.nango import NangoResource
from resources.postgres import PostgresResource
```

## Project Structure

```
data-hub/
├── definitions.py          # Dagster entry point
├── assets/salesforce/      # One file per Salesforce object (no psycopg2!)
├── resources/              # PostgresResource (psycopg2 bridge), NangoResource
├── nango-integrations/     # TypeScript Nango syncs (separate)
```

## Running Locally

```bash
source .env && dagster dev
```

## Do Not

- Import psycopg2 in assets — use PostgresResource methods instead
- Access private attributes (`_connection`) from outside the class
- Use `Any` without good reason — prefer specific types
- Skip type annotations on function signatures
- Execute raw SQL in assets — encapsulate in resource methods
