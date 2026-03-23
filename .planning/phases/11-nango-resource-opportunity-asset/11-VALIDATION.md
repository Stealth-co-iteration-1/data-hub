---
phase: 11
slug: nango-resource-opportunity-asset
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-23
---

# Phase 11 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/dagster/ -v --tb=short` |
| **Full suite command** | `uv run pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/dagster/ -v --tb=short`
- **After every plan wave:** Run `uv run pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 11-01-01 | 01 | 1 | NANGO-01 | unit | `python -c "from dagster_pipelines.resources.nango import NangoResource"` | ❌ W0 | pending |
| 11-01-02 | 01 | 1 | NANGO-02 | integration | Manual — requires live Nango credentials | N/A | pending |
| 11-01-03 | 01 | 1 | ASSET-01 | integration | `dagster asset materialize -m dagster_pipelines.definitions --select salesforce_opportunities` | ❌ W0 | pending |
| 11-01-04 | 01 | 1 | OBS-01 | manual | Check Dagster UI for row_count metadata | N/A | pending |

*Status: pending · green · red · flaky*

---

## Wave 0 Requirements

- [ ] `tests/dagster/` — test directory for Dagster-related tests
- [ ] `tests/dagster/test_nango_resource.py` — unit tests for NangoResource
- [ ] `tests/dagster/conftest.py` — fixtures for mocking Nango API responses

*If none: "Existing infrastructure covers all phase requirements."*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Records fetched from Nango | NANGO-02 | Requires live Nango connection with synced data | Set NANGO_SECRET_KEY and NANGO_CONNECTION_ID, run `dagster asset materialize` |
| Row count in Dagster UI | OBS-01 | Visual verification in webserver | Run `dagster dev`, materialize asset, check metadata panel |
| Idempotent refresh | ASSET-01 | End-to-end behavior | Run `dagster asset materialize` twice, verify row count matches |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
