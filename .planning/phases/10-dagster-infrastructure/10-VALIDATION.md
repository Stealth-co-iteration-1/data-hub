---
phase: 10
slug: dagster-infrastructure
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-23
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (existing) + dagster test utilities |
| **Config file** | pyproject.toml (existing pytest config) |
| **Quick run command** | `dagster dev --help` (validates install) |
| **Full suite command** | `dagster dev` (validates full boot) |
| **Estimated runtime** | ~5 seconds (help), ~15 seconds (boot) |

---

## Sampling Rate

- **After every task commit:** Run `dagster --version` to confirm install
- **After every plan wave:** Run `dagster dev` and verify webserver starts
- **Before `/gsd:verify-work`:** Full boot with `ping_database` asset materialization
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 10-01-01 | 01 | 1 | DAGSTER-01 | integration | `test -f dagster/definitions.py` | ✅ | ⬜ pending |
| 10-01-02 | 01 | 1 | DAGSTER-01 | integration | `test -f workspace.yaml` | ✅ | ⬜ pending |
| 10-01-03 | 01 | 1 | DAGSTER-02 | integration | `test -f dagster.yaml` | ✅ | ⬜ pending |
| 10-01-04 | 01 | 1 | DAGSTER-02 | integration | `grep -q "postgres" dagster.yaml` | ✅ | ⬜ pending |
| 10-01-05 | 01 | 1 | DAGSTER-03 | manual | `dagster dev` + verify UI loads | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `dagster/` directory created with `__init__.py`
- [ ] `dagster/assets/__init__.py` stub
- [ ] `dagster/resources/__init__.py` stub
- [ ] Dagster packages added to pyproject.toml

*Existing pytest infrastructure covers unit test needs; dagster-specific validation is integration-level (boot tests).*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Webserver UI loads at localhost:3000 | DAGSTER-03 | Browser verification needed | Run `dagster dev`, open http://localhost:3000, verify UI renders |
| ping_database asset materializes | DAGSTER-03 | Requires running PostgreSQL | In Dagster UI, click Materialize on ping_database asset |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
