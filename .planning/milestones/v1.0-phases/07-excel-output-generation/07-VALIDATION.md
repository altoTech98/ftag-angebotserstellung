---
phase: 7
slug: excel-output-generation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-10
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.4.4 + pytest-asyncio 0.23.3 |
| **Config file** | backend/tests/ directory with conftest.py + conftest_v2.py |
| **Quick run command** | `cd backend && python -m pytest tests/test_v2_excel_output.py -x -v` |
| **Full suite command** | `cd backend && python -m pytest tests/ -x -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest tests/test_v2_excel_output.py -x -v`
- **After every plan wave:** Run `cd backend && python -m pytest tests/ -x -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 07-01-01 | 01 | 0 | EXEL-01..06 | unit | `python -m pytest tests/test_v2_excel_output.py -x` | Wave 0 | pending |
| 07-01-02 | 01 | 1 | EXEL-01 | unit | `python -m pytest tests/test_v2_excel_output.py::test_uebersicht_sheet -x` | Wave 0 | pending |
| 07-01-03 | 01 | 1 | EXEL-02 | unit | `python -m pytest tests/test_v2_excel_output.py::test_details_sheet -x` | Wave 0 | pending |
| 07-01-04 | 01 | 1 | EXEL-03 | unit | `python -m pytest tests/test_v2_excel_output.py::test_gap_analyse_sheet -x` | Wave 0 | pending |
| 07-01-05 | 01 | 1 | EXEL-04 | unit | `python -m pytest tests/test_v2_excel_output.py::test_executive_summary_sheet -x` | Wave 0 | pending |
| 07-01-06 | 01 | 1 | EXEL-05 | unit | `python -m pytest tests/test_v2_excel_output.py::test_color_coding -x` | Wave 0 | pending |
| 07-01-07 | 01 | 1 | EXEL-06 | unit | `python -m pytest tests/test_v2_excel_output.py::test_cell_comments -x` | Wave 0 | pending |
| 07-02-01 | 02 | 2 | APII-04 | integration | `python -m pytest tests/test_v2_excel_output.py::test_generate_endpoint -x` | Wave 0 | pending |
| 07-02-02 | 02 | 2 | APII-05 | integration | `python -m pytest tests/test_v2_excel_output.py::test_download_endpoint -x` | Wave 0 | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_v2_excel_output.py` — stubs for EXEL-01 through EXEL-06, APII-04, APII-05
- [ ] Test fixtures in `backend/tests/conftest_v2.py` — sample MatchResult, AdversarialResult, GapReport objects
- [ ] Mock for Claude API call in Executive Summary tests (avoid real API calls)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Visual color-coding appearance | EXEL-05 | openpyxl color fills verified programmatically but visual appearance needs human check | Open generated xlsx, verify green/yellow/red cells visually |
| Excel print layout | EXEL-01..04 | Print formatting is subjective | Print preview each sheet, check readability |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
