---
phase: 12
slug: file-handling-project-management
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-11
---

# Phase 12 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | vitest (frontend), pytest 7.x (backend) |
| **Config file** | `frontend/vitest.config.ts`, `backend/pytest.ini` |
| **Quick run command** | `cd frontend && npx vitest run --reporter=verbose` |
| **Full suite command** | `cd frontend && npx vitest run && cd ../backend && python -m pytest tests/` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd frontend && npx vitest run --reporter=verbose`
- **After every plan wave:** Run full suite command
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 12-01-01 | 01 | 1 | INFRA-04 | unit | `cd frontend && npx vitest run` | ❌ W0 | ⬜ pending |
| 12-01-02 | 01 | 1 | ANLZ-01 | unit+integration | `cd frontend && npx vitest run` | ❌ W0 | ⬜ pending |
| 12-02-01 | 02 | 1 | PROJ-01 | unit | `cd frontend && npx vitest run` | ❌ W0 | ⬜ pending |
| 12-02-02 | 02 | 1 | PROJ-02, PROJ-03 | unit | `cd frontend && npx vitest run` | ❌ W0 | ⬜ pending |
| 12-03-01 | 03 | 2 | PROJ-04 | unit | `cd frontend && npx vitest run` | ❌ W0 | ⬜ pending |
| 12-03-02 | 03 | 2 | PROJ-02 | integration | `cd frontend && npx vitest run` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Test stubs for Vercel Blob upload (mock `@vercel/blob` client)
- [ ] Test stubs for Prisma Project/File/Analysis CRUD (mock Prisma client)
- [ ] Shared fixtures for authenticated user context

*If none: "Existing infrastructure covers all phase requirements."*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Drag-and-drop file upload UX | ANLZ-01 | Browser DnD events require manual interaction | Upload PDF via drag-and-drop, verify file appears in project |
| Large file upload (>4.5 MB) | INFRA-04 | Requires real Vercel Blob endpoint | Upload 5+ MB file, verify stored in Vercel Blob |
| Project sharing notification | PROJ-04 | Requires multi-user session | Share project, log in as other user, verify visibility |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
