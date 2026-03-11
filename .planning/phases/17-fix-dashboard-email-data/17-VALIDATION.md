---
phase: 17
slug: fix-dashboard-email-data
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-11
---

# Phase 17 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Vitest 3.x |
| **Config file** | `frontend/vitest.config.ts` |
| **Quick run command** | `cd frontend && npx vitest run src/__tests__/dashboard/statistics.test.tsx src/__tests__/email/analysis-complete.test.tsx -x` |
| **Full suite command** | `cd frontend && npx vitest run` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd frontend && npx vitest run src/__tests__/dashboard/statistics.test.tsx src/__tests__/email/analysis-complete.test.tsx -x`
- **After every plan wave:** Run `cd frontend && npx vitest run`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 17-01-01 | 01 | 0 | DASH-03 | unit | `cd frontend && npx vitest run src/__tests__/dashboard/statistics.test.tsx -x` | Stub only (it.todo) | ⬜ pending |
| 17-01-02 | 01 | 0 | INFRA-05 | unit | `cd frontend && npx vitest run src/__tests__/email/analysis-complete.test.tsx -x` | ❌ W0 | ⬜ pending |
| 17-01-03 | 01 | 1 | DASH-03 | unit | `cd frontend && npx vitest run src/__tests__/dashboard/statistics.test.tsx -x` | ✅ (from W0) | ⬜ pending |
| 17-01-04 | 01 | 1 | INFRA-05 | unit | `cd frontend && npx vitest run src/__tests__/email/analysis-complete.test.tsx -x` | ✅ (from W0) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `frontend/src/__tests__/dashboard/statistics.test.tsx` — implement tests for DASH-03 (currently stubs with it.todo)
- [ ] `frontend/src/__tests__/email/analysis-complete.test.tsx` — create tests for INFRA-05 email stats

*Wave 0 creates failing tests before implementation begins.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
