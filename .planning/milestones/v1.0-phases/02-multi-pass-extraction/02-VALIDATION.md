---
phase: 2
slug: multi-pass-extraction
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-10
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.4.4 + pytest-asyncio 0.23.3 |
| **Config file** | `backend/tests/conftest.py` (imports conftest_v2.py fixtures) |
| **Quick run command** | `cd backend && python -m pytest tests/test_v2_extraction.py -x -v` |
| **Full suite command** | `cd backend && python -m pytest tests/ -x -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest tests/test_v2_extraction.py tests/test_v2_upload.py -x -v`
- **After every plan wave:** Run `cd backend && python -m pytest tests/ -x -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 0 | DOKA-04 | integration | `pytest tests/test_v2_upload.py -x` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 0 | DOKA-05 | unit + integration | `pytest tests/test_v2_extraction.py -x` | ❌ W0 | ⬜ pending |
| 02-01-03 | 01 | 0 | DOKA-06 | unit | `pytest tests/test_v2_extraction.py::test_all_fields_extracted -x` | ❌ W0 | ⬜ pending |
| 02-01-04 | 01 | 0 | APII-01 | integration | `pytest tests/test_v2_upload.py::test_multi_file_upload -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_v2_extraction.py` — stubs for DOKA-05, DOKA-06 (pass1, pass2 mock, pass3 mock, dedup, pipeline orchestration)
- [ ] `tests/test_v2_upload.py` — stubs for DOKA-04, APII-01 (multi-file upload, tender_id session, file ordering)
- [ ] `tests/test_v2_dedup.py` — stubs for deduplication logic (merge, conflict resolution, provenance tracking)
- [ ] `tests/conftest_v2.py` additions — multi-file fixtures, sample tender with mixed formats

*If none: "Existing infrastructure covers all phase requirements."*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| AI extraction quality | DOKA-05 | Claude output varies | Upload real tender, verify extracted fields match document |
| Cross-reference pass accuracy | DOKA-05 | Requires real multi-doc context | Upload 3+ files, verify pass 3 finds cross-doc references |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
