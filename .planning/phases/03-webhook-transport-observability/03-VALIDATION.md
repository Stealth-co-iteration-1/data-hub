---
phase: 3
slug: webhook-transport-observability
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-18
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3+ with pytest-asyncio 0.24+ |
| **Config file** | pyproject.toml (existing from Phase 1) |
| **Quick run command** | `uv run pytest tests/integration/test_webhook*.py tests/integration/test_health*.py -x -q` |
| **Full suite command** | `uv run pytest tests/ -v` |
| **Estimated runtime** | ~8 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/integration/test_webhook*.py -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 8 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | TRAN-01 | integration | `uv run pytest tests/integration/test_webhook_endpoint.py -v` | ❌ W0 | ⬜ pending |
| 03-01-02 | 01 | 1 | TRAN-02 | integration | `uv run pytest tests/integration/test_webhook_endpoint.py::test_fast_ack -v` | ❌ W0 | ⬜ pending |
| 03-01-03 | 01 | 1 | TRAN-03 | integration | `uv run pytest tests/integration/test_signature.py -v` | ❌ W0 | ⬜ pending |
| 03-02-01 | 02 | 2 | OBSV-01 | integration | `uv run pytest tests/integration/test_logging.py -v` | ❌ W0 | ⬜ pending |
| 03-02-02 | 02 | 2 | OBSV-02 | integration | `uv run pytest tests/integration/test_logging.py::test_validation_failure_context -v` | ❌ W0 | ⬜ pending |
| 03-03-01 | 03 | 3 | TRAN-04 | integration | `uv run pytest tests/integration/test_health.py -v` | ❌ W0 | ⬜ pending |
| 03-03-02 | 03 | 3 | OBSV-03 | integration | `uv run pytest tests/integration/test_metrics.py -v` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/integration/conftest.py` — update with FastAPI TestClient fixtures
- [ ] `tests/integration/test_webhook_endpoint.py` — stubs for TRAN-01, TRAN-02
- [ ] `tests/integration/test_signature.py` — stubs for TRAN-03
- [ ] `tests/integration/test_logging.py` — stubs for OBSV-01, OBSV-02
- [ ] `tests/integration/test_health.py` — stubs for TRAN-04
- [ ] `tests/integration/test_metrics.py` — stubs for OBSV-03

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Webhook response time < 5s | TRAN-02 | Requires real network timing | 1. Send webhook via curl 2. Measure response time 3. Must be < 5 seconds |
| Health check < 1s | TRAN-04 | Performance under load | 1. Hit /health endpoint 2. Response must be < 1 second |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 8s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
