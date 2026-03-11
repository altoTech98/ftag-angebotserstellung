---
phase: 13
slug: analysis-wizard-results-view
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-11
---

# Phase 13 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Vitest 4.0.18 |
| **Config file** | `frontend/vitest.config.ts` |
| **Quick run command** | `cd frontend && npx vitest run --reporter=verbose` |
| **Full suite command** | `cd frontend && npx vitest run` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd frontend && npx vitest run --reporter=verbose`
- **After every plan wave:** Run `cd frontend && npx vitest run`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 13-00-01 | 00 | 0 | all | stub | `cd frontend && npx vitest run src/__tests__/analysis/ --reporter=verbose` | Plan 00 creates | pending |
| 13-01-02 | 01 | 1 | ANLZ-02, ANLZ-03 | unit | `cd frontend && npx vitest run src/__tests__/analysis/step-catalog.test.tsx src/__tests__/analysis/step-config.test.tsx -x` | Plan 01 updates | pending |
| 13-02-01 | 02 | 2 | ANLZ-04 | unit | `cd frontend && npx vitest run src/__tests__/analysis/step-progress.test.tsx -x` | Plan 02 updates | pending |
| 13-02-02 | 02 | 2 | ANLZ-05, RSLT-01, RSLT-04 | unit | `cd frontend && npx vitest run src/__tests__/analysis/step-results.test.tsx -x` | Plan 02 updates | pending |
| 13-03-01 | 03 | 3 | RSLT-02 | unit | `cd frontend && npx vitest run src/__tests__/analysis/result-detail.test.tsx -x` | Plan 03 updates | pending |
| 13-03-02 | 03 | 3 | RSLT-03 | unit | `cd frontend && npx vitest run src/__tests__/analysis/comparison-card.test.tsx -x` | Plan 03 updates | pending |
| 13-03-03 | 03 | 3 | ANLZ-05 | unit | `cd frontend && npx vitest run src/__tests__/analysis/wizard-init.test.tsx -x` | Plan 03 updates | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [x] `frontend/src/__tests__/analysis/step-catalog.test.tsx` — stubs for ANLZ-02 (Plan 13-00)
- [x] `frontend/src/__tests__/analysis/step-config.test.tsx` — stubs for ANLZ-03 (Plan 13-00)
- [x] `frontend/src/__tests__/analysis/step-progress.test.tsx` — stubs for ANLZ-04 (Plan 13-00)
- [x] `frontend/src/__tests__/analysis/step-results.test.tsx` — stubs for ANLZ-05, RSLT-01, RSLT-04 (Plan 13-00)
- [x] `frontend/src/__tests__/analysis/result-detail.test.tsx` — stubs for RSLT-02 (Plan 13-00)
- [x] `frontend/src/__tests__/analysis/comparison-card.test.tsx` — stubs for RSLT-03 (Plan 13-00)
- [x] `frontend/src/__tests__/analysis/wizard-init.test.tsx` — stubs for analysisId -> step 5 loading (Plan 13-00)

NOTE: Test stubs live in `src/__tests__/analysis/` (project convention), not alongside components.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| SSE real-time progress updates display correctly | ANLZ-04 | Requires live backend SSE stream | Start analysis, verify progress bar advances through stages |
| Excel download produces correct 4-sheet format | RSLT-04 | Requires Python backend Excel generation | Run analysis, download Excel, verify 4 sheets with correct data |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify with behavioral test commands
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (Plan 13-00)
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending execution
