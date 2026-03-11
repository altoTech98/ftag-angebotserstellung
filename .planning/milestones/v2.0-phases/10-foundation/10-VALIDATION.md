---
phase: 10
slug: foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-11
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Vitest |
| **Config file** | `vitest.config.ts` — Wave 0 installs |
| **Quick run command** | `npx vitest run --reporter=verbose` |
| **Full suite command** | `npx vitest run` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `npx vitest run --reporter=verbose`
- **After every plan wave:** Run `npx vitest run`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 10-01-01 | 01 | 1 | INFRA-01 | smoke | `npx vitest run src/__tests__/infra/database.test.ts` | ❌ W0 | ⬜ pending |
| 10-01-02 | 01 | 1 | AUTH-01 | integration | `npx vitest run src/__tests__/auth/login.test.ts -t "login"` | ❌ W0 | ⬜ pending |
| 10-01-03 | 01 | 1 | AUTH-02 | integration | `npx vitest run src/__tests__/auth/password-reset.test.ts` | ❌ W0 | ⬜ pending |
| 10-01-04 | 01 | 1 | AUTH-03 | unit | `npx vitest run src/__tests__/hooks/session-timeout.test.ts` | ❌ W0 | ⬜ pending |
| 10-01-05 | 01 | 1 | AUTH-04 | unit | `npx vitest run src/__tests__/auth/permissions.test.ts` | ❌ W0 | ⬜ pending |
| 10-01-06 | 01 | 1 | AUTH-05 | integration | `npx vitest run src/__tests__/auth/route-protection.test.ts` | ❌ W0 | ⬜ pending |
| 10-02-01 | 02 | 2 | UI-01 | smoke | `npx vitest run src/__tests__/ui/theme.test.ts` | ❌ W0 | ⬜ pending |
| 10-02-02 | 02 | 2 | UI-02 | manual | Manual — visual check at 3 breakpoints | N/A | ⬜ pending |
| 10-02-03 | 02 | 2 | UI-03 | manual | Manual — visual check sidebar red active | N/A | ⬜ pending |
| 10-02-04 | 02 | 2 | UI-04 | unit | `npx vitest run src/__tests__/ui/breadcrumbs.test.ts` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `vitest.config.ts` — test framework configuration
- [ ] `npm install -D vitest @testing-library/react @testing-library/jest-dom jsdom` — framework install
- [ ] `src/__tests__/auth/login.test.ts` — stubs for AUTH-01
- [ ] `src/__tests__/auth/password-reset.test.ts` — stubs for AUTH-02
- [ ] `src/__tests__/hooks/session-timeout.test.ts` — stubs for AUTH-03
- [ ] `src/__tests__/auth/permissions.test.ts` — stubs for AUTH-04
- [ ] `src/__tests__/auth/route-protection.test.ts` — stubs for AUTH-05
- [ ] `src/__tests__/ui/theme.test.ts` — stubs for UI-01
- [ ] `src/__tests__/ui/breadcrumbs.test.ts` — stubs for UI-04
- [ ] `src/__tests__/infra/database.test.ts` — stubs for INFRA-01

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Responsive layout renders at desktop/tablet/mobile | UI-02 | Visual layout check across breakpoints | Resize browser to 1440px, 768px, 375px; verify layout adapts correctly |
| Sidebar with red active item styling | UI-03 | Visual check of active state color | Navigate between pages; verify active sidebar item shows FTAG red highlight |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
