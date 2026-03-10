---
phase: 9
slug: frontend-v2-offer-feedback-wiring
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-10
---

# Phase 9 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend), manual (frontend — no jest/vitest configured) |
| **Config file** | backend/tests/ directory with conftest.py |
| **Quick run command** | `cd backend && python -m pytest tests/test_v2_excel_output.py tests/test_offer.py -x` |
| **Full suite command** | `cd backend && python -m pytest tests/ -x` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest tests/test_v2_excel_output.py tests/test_offer.py -x`
- **After every plan wave:** Run `cd backend && python -m pytest tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 09-01-01 | 01 | 1 | EXEL-01, EXEL-02, EXEL-03, EXEL-04, EXEL-05, EXEL-06 | unit | `cd backend && python -m pytest tests/test_v2_excel_output.py -x` | ✅ | ⬜ pending |
| 09-01-02 | 01 | 1 | APII-04, APII-05 | integration | `cd backend && python -m pytest tests/test_v2_offer_endpoint.py -x` | ❌ W0 | ⬜ pending |
| 09-01-03 | 01 | 1 | MATC-09 | integration | `cd backend && python -m pytest tests/test_v2_matching.py -x` | ✅ | ⬜ pending |
| 09-01-04 | 01 | 1 | GAPA-05 | unit | `cd backend && python -m pytest tests/test_v2_gaps.py -x` | ✅ | ⬜ pending |
| 09-01-05 | 01 | 1 | — | manual | Browser test: v2 analysis → offer download → correction | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_v2_offer_endpoint.py` — stubs for APII-04, APII-05 (v2 offer generate + download)

*Frontend has no test framework — UI wiring verified manually.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| V2 analysis → offer download flow | APII-04, APII-05 | Frontend UI wiring, no jest/vitest | 1. Upload folder via UI 2. Run v2 analysis 3. Click "Generate Offer" 4. Verify 4-sheet Excel downloads |
| CorrectionModal v2 feedback | MATC-09 | Frontend UI component | 1. After analysis, open correction modal 2. Submit correction 3. Verify POST to /api/v2/feedback with v2 schema |
| V2 response key consumption | — | Frontend JS wiring | 1. After v2 analysis, inspect browser console 2. Verify positionen, match_results, adversarial_results, gap_results parsed |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
