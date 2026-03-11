---
phase: 4
slug: product-matching-engine
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-10
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.4.4 + pytest-asyncio 0.23.3 |
| **Config file** | Backend uses pytest discovery from `backend/tests/` |
| **Quick run command** | `cd backend && python -m pytest tests/test_v2_matching.py -x` |
| **Full suite command** | `cd backend && python -m pytest tests/ -x --timeout=60` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest tests/test_v2_matching.py -x`
- **After every plan wave:** Run `cd backend && python -m pytest tests/ -x --timeout=60`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 0 | MATC-01 | unit | `cd backend && python -m pytest tests/test_v2_matching.py::test_tfidf_returns_candidates -x` | ❌ W0 | ⬜ pending |
| 04-01-02 | 01 | 0 | MATC-02 | unit | `cd backend && python -m pytest tests/test_v2_matching.py::test_dimension_scores_all_present -x` | ❌ W0 | ⬜ pending |
| 04-01-03 | 01 | 0 | MATC-03 | unit | `cd backend && python -m pytest tests/test_v2_matching.py::test_confidence_calculation -x` | ❌ W0 | ⬜ pending |
| 04-01-04 | 01 | 0 | MATC-04 | unit | `cd backend && python -m pytest tests/test_v2_matching.py::test_threshold_95_confirmed -x` | ❌ W0 | ⬜ pending |
| 04-01-05 | 01 | 0 | MATC-09 | unit | `cd backend && python -m pytest tests/test_v2_matching.py::test_feedback_injection -x` | ❌ W0 | ⬜ pending |
| 04-01-06 | 01 | 0 | APII-06 | integration | `cd backend && python -m pytest tests/test_v2_matching.py::test_feedback_endpoint -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_v2_matching.py` — stubs for MATC-01 through MATC-04, MATC-09, APII-06
- [ ] Fixtures: sample ExtractedDoorPosition objects (reuse from conftest_v2.py), mock catalog DataFrame, mock Anthropic client
- [ ] No new framework install needed — pytest + pytest-asyncio already in requirements.txt

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| AI match quality on real FTAG catalog | MATC-01 | Requires real Claude API + real catalog data | Upload test tender doc, verify matches are sensible |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
