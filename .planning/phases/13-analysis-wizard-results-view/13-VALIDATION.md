---
phase: 13
slug: analysis-wizard-results-view
status: draft
nyquist_compliant: false
wave_0_complete: false
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
| 13-01-01 | 01 | 0 | ANLZ-02 | unit | `cd frontend && npx vitest run src/components/analysis/step-catalog.test.tsx -x` | ❌ W0 | ⬜ pending |
| 13-01-02 | 01 | 0 | ANLZ-03 | unit | `cd frontend && npx vitest run src/components/analysis/step-config.test.tsx -x` | ❌ W0 | ⬜ pending |
| 13-01-03 | 01 | 0 | ANLZ-04 | unit | `cd frontend && npx vitest run src/components/analysis/step-progress.test.tsx -x` | ❌ W0 | ⬜ pending |
| 13-01-04 | 01 | 0 | ANLZ-05, RSLT-01, RSLT-04 | unit | `cd frontend && npx vitest run src/components/analysis/step-results.test.tsx -x` | ❌ W0 | ⬜ pending |
| 13-01-05 | 01 | 0 | RSLT-02 | unit | `cd frontend && npx vitest run src/components/analysis/result-detail.test.tsx -x` | ❌ W0 | ⬜ pending |
| 13-01-06 | 01 | 0 | RSLT-03 | unit | `cd frontend && npx vitest run src/components/analysis/comparison-card.test.tsx -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `frontend/src/components/analysis/step-catalog.test.tsx` — stubs for ANLZ-02
- [ ] `frontend/src/components/analysis/step-config.test.tsx` — stubs for ANLZ-03
- [ ] `frontend/src/components/analysis/step-progress.test.tsx` — stubs for ANLZ-04
- [ ] `frontend/src/components/analysis/step-results.test.tsx` — stubs for ANLZ-05, RSLT-01, RSLT-04
- [ ] `frontend/src/components/analysis/result-detail.test.tsx` — stubs for RSLT-02
- [ ] `frontend/src/components/analysis/comparison-card.test.tsx` — stubs for RSLT-03

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| SSE real-time progress updates display correctly | ANLZ-04 | Requires live backend SSE stream | Start analysis, verify progress bar advances through stages |
| Excel download produces correct 4-sheet format | RSLT-04 | Requires Python backend Excel generation | Run analysis, download Excel, verify 4 sheets with correct data |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
