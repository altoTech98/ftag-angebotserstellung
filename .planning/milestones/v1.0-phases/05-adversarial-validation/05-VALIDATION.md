---
phase: 5
slug: adversarial-validation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-10
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio |
| **Config file** | backend/tests/ (existing conftest.py + conftest_v2.py) |
| **Quick run command** | `cd backend && .venv/Scripts/python.exe -m pytest tests/test_v2_adversarial.py -x` |
| **Full suite command** | `cd backend && .venv/Scripts/python.exe -m pytest tests/ -x` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && .venv/Scripts/python.exe -m pytest tests/test_v2_adversarial.py -x`
- **After every plan wave:** Run `cd backend && .venv/Scripts/python.exe -m pytest tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 0 | MATC-05, MATC-06, MATC-07, MATC-08 | unit | `pytest tests/test_v2_adversarial.py -x` | ❌ W0 | ⬜ pending |
| 05-01-02 | 01 | 1 | MATC-05, MATC-07, MATC-08 | unit | `pytest tests/test_v2_adversarial.py::TestAdversarialDebate -x` | ❌ W0 | ⬜ pending |
| 05-01-03 | 01 | 1 | MATC-06 | unit | `pytest tests/test_v2_adversarial.py::TestTripleCheck -x` | ❌ W0 | ⬜ pending |
| 05-02-01 | 02 | 2 | MATC-05, MATC-06, MATC-07, MATC-08 | integration | `pytest tests/test_v2_adversarial.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_v2_adversarial.py` — test stubs for MATC-05, MATC-06, MATC-07, MATC-08
- [ ] Mock fixtures for MatchResult -> AdversarialResult pipeline (reuse `_make_match_result` from test_v2_matching.py)
- [ ] Mock Opus responses for FOR/AGAINST/resolution structured outputs

*Existing infrastructure (pytest, conftest.py, conftest_v2.py) covers framework needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| German CoT readability | MATC-07 | Subjective language quality | Review sample adversarial output for German fluency and reasoning clarity |
| AGAINST prompt calibration | MATC-05 | Requires real tender data | Run against 3+ real tenders, verify <50% triple-check trigger rate |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
