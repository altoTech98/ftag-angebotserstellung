---
phase: 3
slug: cross-document-intelligence
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-10
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (already installed) |
| **Config file** | backend/tests/conftest.py + conftest_v2.py |
| **Quick run command** | `cd backend && python -m pytest tests/test_v2_crossdoc.py -x` |
| **Full suite command** | `cd backend && python -m pytest tests/ -x` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest tests/test_v2_crossdoc.py -x`
- **After every plan wave:** Run `cd backend && python -m pytest tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 0 | DOKA-07, DOKA-08 | unit | `cd backend && python -m pytest tests/test_v2_crossdoc.py -x` | ❌ W0 | ⬜ pending |
| 03-01-02 | 01 | 1 | DOKA-07 | unit | `cd backend && python -m pytest tests/test_v2_crossdoc.py::TestCrossDocMatcher -x` | ❌ W0 | ⬜ pending |
| 03-01-03 | 01 | 1 | DOKA-07 | unit | `cd backend && python -m pytest tests/test_v2_crossdoc.py::TestEnrichment -x` | ❌ W0 | ⬜ pending |
| 03-01-04 | 01 | 1 | DOKA-08 | unit | `cd backend && python -m pytest tests/test_v2_crossdoc.py::TestConflictDetector -x` | ❌ W0 | ⬜ pending |
| 03-01-05 | 01 | 2 | DOKA-07, DOKA-08 | integration | `cd backend && python -m pytest tests/test_v2_crossdoc.py::TestPipelineIntegration -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_v2_crossdoc.py` — stubs for DOKA-07, DOKA-08 (all test classes)
- [ ] Extend `backend/tests/conftest_v2.py` — add fixtures for multi-document position sets

*Wave 0 creates test stubs before implementation begins.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Cross-document enrichment visible in final output | DOKA-07 | UI rendering | Upload 2+ docs, verify enrichment report shows source attribution |
| Conflict flags visible in response | DOKA-08 | UI rendering | Upload docs with conflicting specs, verify conflicts displayed with both values |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
