---
phase: 08
slug: quality-observability-end-to-end
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-10
---

# Phase 08 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing) |
| **Config file** | backend/pytest.ini or pyproject.toml (existing) |
| **Quick run command** | `python -m pytest backend/tests/test_plausibility.py backend/tests/test_pipeline_logging.py -x` |
| **Full suite command** | `python -m pytest backend/tests/ -x --timeout=60` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest backend/tests/test_plausibility.py backend/tests/test_pipeline_logging.py -x`
- **After every plan wave:** Run `python -m pytest backend/tests/ -x --timeout=60`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 08-01-01 | 01 | 1 | QUAL-01 | unit | `python -m pytest backend/tests/test_plausibility.py -x` | ❌ W0 | ⬜ pending |
| 08-01-02 | 01 | 1 | QUAL-02 | unit | `python -m pytest backend/tests/test_pipeline_logging.py -x` | ❌ W0 | ⬜ pending |
| 08-01-03 | 01 | 1 | QUAL-04 | unit | `python -m pytest backend/tests/test_error_handling.py -x` | ❌ W0 | ⬜ pending |
| 08-02-01 | 02 | 2 | APII-02, APII-03 | integration | `python -m pytest backend/tests/test_analyze_v2_endpoint.py -x` | ❌ W0 | ⬜ pending |
| 08-02-02 | 02 | 2 | QUAL-03 | integration | `python -m pytest backend/tests/test_sse_progress.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_plausibility.py` — stubs for QUAL-01
- [ ] `backend/tests/test_pipeline_logging.py` — stubs for QUAL-02
- [ ] `backend/tests/test_error_handling.py` — stubs for QUAL-04
- [ ] `backend/tests/test_analyze_v2_endpoint.py` — stubs for APII-02, APII-03
- [ ] `backend/tests/test_sse_progress.py` — stubs for QUAL-03

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live SSE progress renders in browser | QUAL-03 | Requires real browser + SSE connection | Upload doc, start analysis, observe progress bar updates in real-time |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
