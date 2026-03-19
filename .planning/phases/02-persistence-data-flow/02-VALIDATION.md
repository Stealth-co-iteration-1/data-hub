---
phase: 2
slug: persistence-data-flow
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-18
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3+ with pytest-asyncio 0.24+ |
| **Config file** | pyproject.toml (existing from Phase 1) |
| **Quick run command** | `uv run pytest tests/integration -x -q` |
| **Full suite command** | `uv run pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/integration -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | PERS-01, PERS-02 | integration | `uv run pytest tests/integration/test_sqlite_repository.py -v` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | PERS-01 | integration | `uv run pytest tests/integration/test_sqlite_repository.py::test_acid_guarantees -v` | ❌ W0 | ⬜ pending |
| 02-02-01 | 02 | 1 | PERS-03 | integration | `uv run pytest tests/integration/test_audit_log.py -v` | ❌ W0 | ⬜ pending |
| 02-02-02 | 02 | 1 | PERS-04 | integration | `uv run pytest tests/integration/test_idempotency.py -v` | ❌ W0 | ⬜ pending |
| 02-03-01 | 03 | 2 | VERF-01 | integration | `uv run pytest tests/integration/test_verification.py -v` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/integration/conftest.py` — async fixtures for SQLite test database
- [ ] `tests/integration/test_sqlite_repository.py` — stubs for PERS-01, PERS-02
- [ ] `tests/integration/test_audit_log.py` — stubs for PERS-03
- [ ] `tests/integration/test_idempotency.py` — stubs for PERS-04
- [ ] `tests/integration/test_verification.py` — stubs for VERF-01

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Data survives service restart | PERS-01 | Requires process restart | 1. Add data via handler 2. Stop process 3. Restart and query — data must exist |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
