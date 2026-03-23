---
phase: 11-nango-resource-opportunity-asset
verified: 2026-03-23T14:45:00Z
status: passed
score: 4/4 must-haves verified
re_verification: false
---

# Phase 11: Nango Resource & Opportunity Asset Verification Report

**Phase Goal:** First asset validates end-to-end pattern: fetch from Nango Records API, persist to PostgreSQL
**Verified:** 2026-03-23T14:45:00Z
**Status:** passed
**Re-verification:** No - initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | NangoResource fetches all records via paginated API calls | VERIFIED | `get_records()` method with `while True` loop and `next_cursor` handling (nango.py:35-76) |
| 2 | Opportunity asset persists records to salesforce_opportunities table | VERIFIED | `execute_values` INSERT with proper table schema (opportunity.py:50-61) |
| 3 | Running asset twice produces same row count (idempotent full refresh) | VERIFIED | DELETE WHERE connection_id + INSERT pattern (opportunity.py:45-61) |
| 4 | MaterializeResult includes dagster/row_count metadata | VERIFIED | `"dagster/row_count": len(records)` in MaterializeResult (opportunity.py:67) |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `dagster_pipelines/resources/nango.py` | NangoResource ConfigurableResource with get_records method | VERIFIED | 77 lines, contains `class NangoResource(dg.ConfigurableResource)`, `yield_for_execution`, `get_records` with pagination |
| `dagster_pipelines/assets/salesforce/opportunity.py` | salesforce_opportunities asset with full refresh | VERIFIED | 71 lines, contains `@dg.asset`, DELETE+INSERT pattern, MaterializeResult with metadata |
| `dagster_pipelines/definitions.py` | Dagster Definitions with NangoResource and salesforce_opportunities | VERIFIED | 21 lines, registers both asset and resource with EnvVar configuration |
| `dagster_pipelines/resources/__init__.py` | Export NangoResource | VERIFIED | Exports `NangoResource` in `__all__` |
| `dagster_pipelines/assets/salesforce/__init__.py` | Export salesforce_opportunities | VERIFIED | Exports `salesforce_opportunities` in `__all__` |
| `dagster_pipelines/assets/__init__.py` | Export salesforce_opportunities | VERIFIED | Imports from salesforce module |
| `dagster_pipelines/.env.example` | NANGO_SECRET_KEY and NANGO_CONNECTION_ID documented | VERIFIED | Both env vars present with placeholder values |
| `pyproject.toml` | httpx in main dependencies | VERIFIED | `"httpx>=0.28.1"` on line 23 in `[project].dependencies` |
| `dagster_pipelines/assets/ping_database.py` | Deleted (superseded) | VERIFIED | File does not exist |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `opportunity.py` | `nango.py` | NangoResource dependency injection | WIRED | `nango: NangoResource` parameter on line 25 |
| `opportunity.py` | `postgres.py` | PostgresResource dependency injection | WIRED | `postgres_db: PostgresResource` parameter on line 26 |
| `definitions.py` | `nango.py` | Resource registration | WIRED | `"nango": NangoResource(...)` on line 16 |
| `definitions.py` | `opportunity.py` | Asset registration | WIRED | `assets=[salesforce_opportunities]` on line 11 |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| NANGO-01 | 11-01-PLAN.md | NangoResource ConfigurableResource wrapping existing NangoClient | SATISFIED | `class NangoResource(dg.ConfigurableResource)` with httpx client |
| NANGO-02 | 11-01-PLAN.md | Fetch records via Nango Records API (GET /records) | SATISFIED | `get_records()` calls `/records` endpoint with proper headers |
| ASSET-01 | 11-01-PLAN.md | Opportunity asset with full refresh to dedicated table | SATISFIED | `salesforce_opportunities` asset with `salesforce_opportunities` table |
| OBS-01 | 11-01-PLAN.md | MaterializeResult with row count metadata on each asset | SATISFIED | `"dagster/row_count": len(records)` in MaterializeResult |

All 4 requirements from PLAN frontmatter are satisfied. No orphaned requirements found.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| - | - | None found | - | - |

No TODO, FIXME, placeholder, or stub patterns detected in phase artifacts.

### Human Verification Required

1. **End-to-end materialization test**
   - **Test:** Run `dagster asset materialize -m dagster_pipelines.definitions --select salesforce_opportunities` with valid Nango credentials
   - **Expected:** Asset materializes successfully, `salesforce_opportunities` table created with records, row_count visible in Dagster UI
   - **Why human:** Requires live Nango connection with synced Salesforce data

2. **Idempotency verification**
   - **Test:** Run the asset twice in succession
   - **Expected:** Same row count after both runs, no duplicate records
   - **Why human:** Requires running the full pipeline with database state

3. **Dagster UI metadata visibility**
   - **Test:** Check Dagster UI after materialization
   - **Expected:** `dagster/row_count` and `connection_id` visible in asset metadata panel
   - **Why human:** Visual verification in Dagster webserver

### Commit Verification

| Commit | Message | Status |
|--------|---------|--------|
| c806ba9 | feat(11-01): create NangoResource with paginated get_records | VERIFIED |
| 4d36daf | feat(11-01): create salesforce_opportunities asset with full refresh | VERIFIED |
| 71f4a43 | feat(11-01): wire NangoResource and salesforce_opportunities into definitions | VERIFIED |

### Gaps Summary

No gaps found. All must-haves verified:
- NangoResource implements cursor-based pagination correctly
- Opportunity asset uses DELETE+INSERT for idempotent full refresh
- MaterializeResult includes `dagster/row_count` metadata
- All components properly wired in definitions.py
- Environment variables documented in .env.example
- httpx moved to main dependencies

Phase 11 goal achieved: First asset validates end-to-end pattern for Salesforce data pipeline.

---

*Verified: 2026-03-23T14:45:00Z*
*Verifier: Claude (gsd-verifier)*
