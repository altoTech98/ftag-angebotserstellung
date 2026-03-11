---
phase: 18
slug: fix-cross-phase-integration-gaps
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-11
---

# Phase 18 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Vitest (via frontend/package.json) |
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
| 18-01-01 | 01 | 1 | AUTH-05 | unit | `cd frontend && npx vitest run src/__tests__/auth/route-protection.test.ts` | ✅ (needs update) | ⬜ pending |
| 18-01-02 | 01 | 1 | DASH-04 | unit | `cd frontend && npx vitest run src/__tests__/dashboard/quick-action.test.tsx` | ✅ (needs update) | ⬜ pending |
| 18-01-03 | 01 | 1 | ANLZ-02 | integration | Manual verification (requires running backend) | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Update `src/__tests__/auth/route-protection.test.ts` — verify `/login` (not `/auth/login`) redirects
- [ ] Update `src/__tests__/dashboard/quick-action.test.tsx` — verify neue-analyse page renders project list
- [ ] No new test files needed — existing test files cover the areas being modified

*Existing infrastructure covers most phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| catalogId forwarded to Python in analyze request body | ANLZ-02 | Requires running backend + Python environment | 1. Start backend. 2. Select non-default catalog in wizard. 3. Start analysis. 4. Verify Python logs show catalog_id received. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
