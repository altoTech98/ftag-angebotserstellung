---
phase: 16
slug: fix-analysis-python-bridge
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-11
---

# Phase 16 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Vitest |
| **Config file** | `frontend/vitest.config.ts` |
| **Quick run command** | `cd frontend && npx vitest run src/__tests__/analysis/ -x` |
| **Full suite command** | `cd frontend && npx vitest run` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd frontend && npx vitest run src/__tests__/analysis/ -x`
- **After every plan wave:** Run `cd frontend && npx vitest run`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 16-01-01 | 01 | 0 | ANLZ-04 | stub | `cd frontend && npx vitest run src/__tests__/analysis/file-bridge.test.ts -x` | No -- Wave 0 | ⬜ pending |
| 16-01-02 | 01 | 0 | ANLZ-04 | stub | `cd frontend && npx vitest run src/__tests__/analysis/step-progress.test.tsx -x` | Yes (needs update) | ⬜ pending |
| 16-02-01 | 02 | 1 | ANLZ-04-a | unit (mock fetch) | `cd frontend && npx vitest run src/__tests__/analysis/file-bridge.test.ts -x` | No -- Wave 0 | ⬜ pending |
| 16-02-02 | 02 | 1 | ANLZ-04-b | unit | `cd frontend && npx vitest run src/__tests__/analysis/step-progress.test.tsx -x` | Yes (needs update) | ⬜ pending |
| 16-02-03 | 02 | 1 | ANLZ-04-c | unit (mock fetch) | `cd frontend && npx vitest run src/__tests__/analysis/file-bridge.test.ts -x` | No -- Wave 0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `frontend/src/__tests__/analysis/file-bridge.test.ts` — stubs for ANLZ-04-a (endpoint/header fix), ANLZ-04-c (project_id passthrough)
- [ ] Update `frontend/src/__tests__/analysis/step-progress.test.tsx` — verify cancel does not call backend

*Existing Vitest infrastructure covers framework needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Analysis wizard runs E2E from file upload through Python to results | ANLZ-04 | Requires running Python backend + Next.js + real file upload | Upload a test PDF, run analysis wizard, verify results appear |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
