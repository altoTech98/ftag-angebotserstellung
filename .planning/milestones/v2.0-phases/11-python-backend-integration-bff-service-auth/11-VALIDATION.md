---
phase: 11
slug: python-backend-integration-bff-service-auth
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-11
---

# Phase 11 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework (frontend)** | vitest 4.0.18 + jsdom |
| **Framework (backend)** | pytest 7.4.4 + pytest-asyncio |
| **Config file (frontend)** | frontend/vitest.config.ts |
| **Config file (backend)** | backend/tests/conftest.py |
| **Quick run (frontend)** | `cd frontend && npx vitest run --reporter=verbose` |
| **Quick run (backend)** | `cd backend && python -m pytest tests/ -x -q` |
| **Full suite command** | `cd frontend && npx vitest run && cd ../backend && python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run quick run commands for affected area (frontend or backend)
- **After every plan wave:** Run full suite command
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 11-01-01 | 01 | 0 | AUTH-06 | unit | `cd frontend && npx vitest run src/__tests__/proxy.test.ts` | ❌ W0 | ⬜ pending |
| 11-01-02 | 01 | 0 | AUTH-06, INFRA-02 | unit | `cd backend && python -m pytest tests/test_service_auth.py -x` | ❌ W0 | ⬜ pending |
| 11-01-03 | 01 | 0 | INFRA-03 | unit | `cd backend && python -m pytest tests/test_sse_token.py -x` | ❌ W0 | ⬜ pending |
| 11-01-04 | 01 | 0 | INFRA-03 | unit | `cd frontend && npx vitest run src/__tests__/sse-client.test.ts` | ❌ W0 | ⬜ pending |
| 11-xx-xx | 01 | 1 | INFRA-02 | integration | `cd backend && python -m pytest tests/test_service_auth.py -x` | ❌ W0 | ⬜ pending |
| 11-xx-xx | 01 | 1 | INFRA-03 | integration | `cd frontend && npx vitest run src/__tests__/proxy.test.ts` | ❌ W0 | ⬜ pending |
| 11-xx-xx | 02 | 2 | INFRA-03 | unit | `cd frontend && npx vitest run src/__tests__/sse-client.test.ts` | ❌ W0 | ⬜ pending |
| 11-xx-xx | 02 | 2 | AUTH-06 | integration | `cd frontend && npx vitest run src/__tests__/proxy.test.ts` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `frontend/src/__tests__/proxy.test.ts` — stubs for AUTH-06, INFRA-03 (mock fetch, verify headers)
- [ ] `backend/tests/test_service_auth.py` — stubs for AUTH-06, INFRA-02 (test middleware accepts/rejects)
- [ ] `backend/tests/test_sse_token.py` — stubs for INFRA-03 (token creation, validation, expiry)
- [ ] `frontend/src/__tests__/sse-client.test.ts` — stubs for INFRA-03 (SSE + polling fallback)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| SSE real-time events visible in browser | INFRA-03 | Requires running browser + Python backend | 1. Start both servers 2. Trigger analysis 3. Verify progress events appear in UI |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
