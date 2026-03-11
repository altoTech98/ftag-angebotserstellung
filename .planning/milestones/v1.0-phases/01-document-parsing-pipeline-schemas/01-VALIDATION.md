---
phase: 1
slug: document-parsing-pipeline-schemas
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-10
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.4.4 + pytest-asyncio 0.23.3 |
| **Config file** | `backend/pytest.ini` |
| **Quick run command** | `cd backend && python -m pytest tests/test_v2_*.py -x -q` |
| **Full suite command** | `cd backend && python -m pytest tests/ -v --tb=short` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest tests/test_v2_*.py -x -q`
- **After every plan wave:** Run `cd backend && python -m pytest tests/ -v --tb=short`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 0 | ALL | unit | `cd backend && python -m pytest tests/test_v2_schemas.py -x` | ❌ W0 | ⬜ pending |
| 01-01-02 | 01 | 1 | DOKA-01 | unit | `cd backend && python -m pytest tests/test_v2_pdf_parser.py -x` | ❌ W0 | ⬜ pending |
| 01-01-03 | 01 | 1 | DOKA-02 | unit | `cd backend && python -m pytest tests/test_v2_docx_parser.py -x` | ❌ W0 | ⬜ pending |
| 01-01-04 | 01 | 1 | DOKA-03 | unit | `cd backend && python -m pytest tests/test_v2_xlsx_parser.py -x` | ❌ W0 | ⬜ pending |
| 01-01-05 | 01 | 1 | ALL | unit | `cd backend && python -m pytest tests/test_v2_schemas.py::test_anthropic_compatibility -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_v2_schemas.py` — stubs for schema validity, import, anthropic compatibility
- [ ] `backend/tests/test_v2_pdf_parser.py` — stubs for DOKA-01 (PDF table preservation, OCR fallback, corrupt file handling)
- [ ] `backend/tests/test_v2_docx_parser.py` — stubs for DOKA-02 (paragraph extraction, table extraction, formatting context)
- [ ] `backend/tests/test_v2_xlsx_parser.py` — stubs for DOKA-03 (header auto-detect, merged cells, fuzzy column matching)
- [ ] `backend/tests/conftest_v2.py` — shared fixtures for v2 tests (sample PDF/DOCX/XLSX bytes, mock ParseResult)
- [ ] `backend/v2/__init__.py` — v2 package initialization

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| PDF table visual alignment | DOKA-01 | Visual quality assessment | Upload sample PDF with tables, verify markdown output preserves column alignment |
| XLSX with real customer formats | DOKA-03 | Requires real tender data | Test with actual FTAG Machbarkeit files from project root |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
