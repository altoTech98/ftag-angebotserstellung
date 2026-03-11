---
phase: 15
slug: admin-dashboard-polish
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-11
---

# Phase 15 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Vitest 4.0.18 + jsdom |
| **Config file** | frontend/vitest.config.ts |
| **Quick run command** | `cd frontend && npx vitest run --reporter=verbose` |
| **Full suite command** | `cd frontend && npx vitest run --reporter=verbose` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd frontend && npx vitest run --reporter=verbose`
- **After every plan wave:** Run `cd frontend && npx vitest run --reporter=verbose`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 15-01-01 | 01 | 0 | ADMIN-01 | unit | `cd frontend && npx vitest run src/__tests__/admin/user-management.test.ts -x` | ❌ W0 | ⬜ pending |
| 15-01-02 | 01 | 0 | ADMIN-02 | unit | `cd frontend && npx vitest run src/__tests__/admin/audit-log.test.ts -x` | ❌ W0 | ⬜ pending |
| 15-01-03 | 01 | 0 | ADMIN-03 | unit | `cd frontend && npx vitest run src/__tests__/admin/system-settings.test.ts -x` | ❌ W0 | ⬜ pending |
| 15-01-04 | 01 | 0 | ADMIN-04 | unit | `cd frontend && npx vitest run src/__tests__/admin/api-key.test.ts -x` | ❌ W0 | ⬜ pending |
| 15-02-01 | 02 | 0 | DASH-01 | unit | `cd frontend && npx vitest run src/__tests__/dashboard/stat-cards.test.tsx -x` | ❌ W0 | ⬜ pending |
| 15-02-02 | 02 | 0 | DASH-02 | unit | `cd frontend && npx vitest run src/__tests__/dashboard/activity-feed.test.tsx -x` | ❌ W0 | ⬜ pending |
| 15-02-03 | 02 | 0 | DASH-03 | unit | `cd frontend && npx vitest run src/__tests__/dashboard/statistics.test.tsx -x` | ❌ W0 | ⬜ pending |
| 15-02-04 | 02 | 0 | DASH-04 | unit | `cd frontend && npx vitest run src/__tests__/dashboard/quick-action.test.tsx -x` | ❌ W0 | ⬜ pending |
| 15-03-01 | 03 | 0 | UI-05 | unit | `cd frontend && npx vitest run src/__tests__/ui/keyboard-shortcuts.test.ts -x` | ❌ W0 | ⬜ pending |
| 15-03-02 | 03 | 0 | UI-06 | unit | `cd frontend && npx vitest run src/__tests__/ui/skeleton-loader.test.tsx -x` | ❌ W0 | ⬜ pending |
| 15-03-03 | 03 | 0 | INFRA-05 | unit | `cd frontend && npx vitest run src/__tests__/infra/email.test.ts -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `src/__tests__/admin/user-management.test.ts` — stubs for ADMIN-01
- [ ] `src/__tests__/admin/audit-log.test.ts` — stubs for ADMIN-02
- [ ] `src/__tests__/admin/system-settings.test.ts` — stubs for ADMIN-03
- [ ] `src/__tests__/admin/api-key.test.ts` — stubs for ADMIN-04
- [ ] `src/__tests__/dashboard/stat-cards.test.tsx` — stubs for DASH-01
- [ ] `src/__tests__/dashboard/activity-feed.test.tsx` — stubs for DASH-02
- [ ] `src/__tests__/dashboard/statistics.test.tsx` — stubs for DASH-03
- [ ] `src/__tests__/dashboard/quick-action.test.tsx` — stubs for DASH-04
- [ ] `src/__tests__/ui/keyboard-shortcuts.test.ts` — stubs for UI-05
- [ ] `src/__tests__/ui/skeleton-loader.test.tsx` — stubs for UI-06
- [ ] `src/__tests__/infra/email.test.ts` — stubs for INFRA-05

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Email delivery arrives in inbox | INFRA-05 | External service | Send test email via admin UI, verify in inbox |
| Keyboard shortcut UX feels responsive | UI-05 | Subjective UX | Press N, verify wizard opens within 200ms |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
