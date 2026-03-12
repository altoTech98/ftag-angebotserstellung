---
phase: 19
slug: pdf-performance-fix
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-12
---

# Phase 19 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.4.4 |
| **Config file** | None detected — Wave 0 creates test stubs |
| **Quick run command** | `python -m pytest tests/test_document_parser.py -x -q` |
| **Full suite command** | `python -m pytest tests/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_document_parser.py -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 19-01-01 | 01 | 1 | PDF-01 | integration | `python -c "import fitz; print(fitz.__doc__[:20])"` | No — W0 | ⬜ pending |
| 19-01-02 | 01 | 1 | PDF-02 | unit | `python -m pytest tests/test_document_parser.py::test_table_extraction -x` | No — W0 | ⬜ pending |
| 19-01-03 | 01 | 1 | PDF-03 | unit | `python -m pytest tests/test_document_parser.py::test_max_chars_zero -x` | No — W0 | ⬜ pending |
| 19-01-04 | 01 | 1 | PDF-04 | manual | Check log output during PDF parsing | N/A | ⬜ pending |
| 19-01-05 | 01 | 1 | INT-02 | smoke | `python -c "from importlib.metadata import version; print(version('pydantic'))"` | No — W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_document_parser.py` — unit tests for `_parse_pdf_bytes` and `parse_pdf_specs_bytes` with PyMuPDF
- [ ] A small test PDF file in `tests/fixtures/` for automated testing
- [ ] Verify `pydantic>=2.7.0` is installed (not just pinned)

*If none: "Existing infrastructure covers all phase requirements."*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Per-page progress in logs | PDF-04 | Log output is visual; automated assertion brittle | Run analysis, check backend logs for per-page entries |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
