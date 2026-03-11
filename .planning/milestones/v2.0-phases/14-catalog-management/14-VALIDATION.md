---
phase: 14
slug: catalog-management
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-11
---

# Phase 14 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Vitest 4.0.18 + Testing Library React 16.3.2 |
| **Config file** | `frontend/vitest.config.ts` |
| **Quick run command** | `cd frontend && npx vitest run src/__tests__/catalog/ -x` |
| **Full suite command** | `cd frontend && npx vitest run` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd frontend && npx vitest run src/__tests__/catalog/ -x`
- **After every plan wave:** Run `cd frontend && npx vitest run`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 14-01-01 | 01 | 0 | KAT-01 | unit | `cd frontend && npx vitest run src/__tests__/catalog/catalog-upload.test.tsx -x` | ❌ W0 | ⬜ pending |
| 14-01-02 | 01 | 0 | KAT-02 | unit | `cd frontend && npx vitest run src/__tests__/catalog/catalog-browse.test.tsx -x` | ❌ W0 | ⬜ pending |
| 14-01-03 | 01 | 0 | KAT-03 | unit | `cd frontend && npx vitest run src/__tests__/catalog/catalog-versions.test.tsx -x` | ❌ W0 | ⬜ pending |
| 14-01-04 | 01 | 0 | KAT-04 | unit | `cd frontend && npx vitest run src/__tests__/catalog/product-edit.test.tsx -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `frontend/src/__tests__/catalog/catalog-upload.test.tsx` — stubs for KAT-01 (upload + validation)
- [ ] `frontend/src/__tests__/catalog/catalog-browse.test.tsx` — stubs for KAT-02 (browse + search + filter)
- [ ] `frontend/src/__tests__/catalog/catalog-versions.test.tsx` — stubs for KAT-03 (version history, compare, rollback)
- [ ] `frontend/src/__tests__/catalog/product-edit.test.tsx` — stubs for KAT-04 (add, edit, delete products)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Drag-and-drop upload UX | KAT-01 | Browser drag events hard to simulate | Upload .xlsx via drag, verify progress + validation results render |
| Version diff visual comparison | KAT-03 | Visual layout verification | Compare two versions, verify diff highlights show correctly |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
