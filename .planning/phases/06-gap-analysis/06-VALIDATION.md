---
phase: 06
slug: gap-analysis
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-10
---

# Phase 06 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | None (run from backend/ directory) |
| **Quick run command** | `cd backend && python -m pytest tests/test_v2_gaps.py -x -v` |
| **Full suite command** | `cd backend && python -m pytest tests/ -x -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest tests/test_v2_gaps.py -x -v`
- **After every plan wave:** Run `cd backend && python -m pytest tests/ -x -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 1 | GAPA-01 | unit | `cd backend && python -m pytest tests/test_v2_gaps.py::TestGapAnalysis -x` | ❌ W0 | ⬜ pending |
| 06-01-02 | 01 | 1 | GAPA-02 | unit | `cd backend && python -m pytest tests/test_v2_gaps.py::TestGapDimensions -x` | ❌ W0 | ⬜ pending |
| 06-01-03 | 01 | 1 | GAPA-03 | unit | `cd backend && python -m pytest tests/test_v2_gaps.py::TestSeverityEscalation -x` | ❌ W0 | ⬜ pending |
| 06-01-04 | 01 | 1 | GAPA-04 | unit | `cd backend && python -m pytest tests/test_v2_gaps.py::TestSuggestions -x` | ❌ W0 | ⬜ pending |
| 06-01-05 | 01 | 1 | GAPA-05 | unit | `cd backend && python -m pytest tests/test_v2_gaps.py::TestAlternativeSearch -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_v2_gaps.py` — stubs for GAPA-01 through GAPA-05
- [ ] Framework install: None needed (pytest already installed)

*Existing infrastructure covers framework requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Alternative product relevance | GAPA-05 | Semantic quality of AI suggestions | Review 3+ gap reports for relevant alternatives |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
