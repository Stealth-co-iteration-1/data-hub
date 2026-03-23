---
created: 2026-03-23T17:26:27.159Z
title: Replace psycopg2 with typed alternative
area: database
files:
  - resources/postgres.py:13
---

## Problem

The `psycopg2` library has incomplete type stubs, causing type checker warnings for imports like `execute_values` from `psycopg2.extras`. Currently using `# type: ignore[reportUnknownVariableType]` as a workaround.

This technical debt affects type safety and IDE support in the database resource layer.

## Solution

Options to consider:
1. **Migrate to psycopg3 (psycopg)** - Modern rewrite with native async support and complete type annotations
2. **Create custom type stubs** - Add local `.pyi` files for psycopg2.extras
3. **Use types-psycopg2** - Check if community stubs have improved coverage for `execute_values`

Recommended: Option 1 (psycopg3) as it's the maintained successor with proper typing built-in.
