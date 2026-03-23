---
created: 2026-03-23T17:35:11.617Z
title: Document database schema architecture
area: docs
files:
  - .planning/PROJECT.md
  - dagster.yaml
---

## Problem

The database schema architecture decision is not documented in PROJECT.md despite being a key architectural choice made in Phase 10:

- **dagster schema**: Dagster internals (run storage, event log, schedule storage) - configured via `dagster.yaml` with `search_path=dagster`
- **public schema**: Asset data tables (`salesforce_opportunities`, `salesforce_opportunity_history`, `salesforce_tasks`, `salesforce_events`)

This separation was chosen to avoid Alembic migration conflicts with Dagster's internal tables, but this rationale and the architecture itself are not captured in project documentation.

## Solution

Update PROJECT.md to include:
1. Database schema architecture in the "Architecture" or "Context" section
2. Rationale for schema separation (Alembic conflict avoidance)
3. Which tables live where
