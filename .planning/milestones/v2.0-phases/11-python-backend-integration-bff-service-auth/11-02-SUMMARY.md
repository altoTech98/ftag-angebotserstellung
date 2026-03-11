---
phase: 11-python-backend-integration-bff-service-auth
plan: 02
subsystem: bff-proxy
tags: [bff, proxy, sse, hmac, next-api-routes, polling-fallback]

# Dependency graph
requires:
  - phase: 11-01
    provides: "service_auth.py (X-Service-Key validation), sse_token_validator.py (HMAC verification)"
provides:
  - "BFF catch-all proxy forwarding /api/backend/* to Python with service key and user context"
  - "SSE token endpoint issuing HMAC-SHA256 signed tokens"
  - "SSE client with EventSource connection and polling fallback"
  - "Health check endpoint reporting Python backend availability"
  - "PYTHON_BACKEND_URL, PYTHON_SERVICE_KEY, SSE_TOKEN_SECRET, NEXT_PUBLIC_PYTHON_SSE_URL env vars"
affects: [12-file-upload, 13-analysis-pipeline]

# Tech tracking
tech-stack:
  added: []
  patterns: [bff-proxy, sse-token-issuance, sse-polling-fallback, abort-controller-timeout]

key-files:
  created:
    - frontend/src/app/api/backend/[...path]/route.ts
    - frontend/src/app/api/backend/sse-token/route.ts
    - frontend/src/app/api/backend/health/route.ts
    - frontend/src/lib/sse-client.ts
    - frontend/src/__tests__/proxy/bff-proxy.test.ts
    - frontend/src/__tests__/proxy/sse-token.test.ts
    - frontend/src/__tests__/proxy/sse-client.test.ts
  modified:
    - frontend/.env.local

key-decisions:
  - "BFF proxy reads PYTHON_SERVICE_KEY from server-side env only (no NEXT_PUBLIC_ prefix) to prevent browser exposure"
  - "SSE token uses base64url(payload).base64url(HMAC-SHA256 signature) format matching Python validator"
  - "Analysis endpoints get 5-minute timeout (300s), all others get 30s default"
  - "SSE client retries 3 times with linear backoff (1s, 2s, 3s) then falls back to polling every 3s"

patterns-established:
  - "BFF proxy: Next.js API route forwards to Python with X-Service-Key + X-User-* headers"
  - "SSE token issuance: server-side HMAC signing with crypto.createHmac"
  - "SSE with polling fallback: EventSource -> retry -> poll pattern"

requirements-completed: [AUTH-06, INFRA-03]

# Metrics
duration: 4min
completed: 2026-03-11
---

# Phase 11 Plan 02: Next.js BFF Proxy & SSE Client Summary

**BFF catch-all proxy with service auth headers, HMAC-signed SSE token issuance, and SSE client with polling fallback**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-11T02:29:47Z
- **Completed:** 2026-03-11T02:34:05Z
- **Tasks:** 2
- **Files created:** 7
- **Files modified:** 1

## Accomplishments
- BFF catch-all proxy forwards /api/backend/* requests to Python with X-Service-Key and X-User-Id/Role/Email headers
- Unauthenticated requests return 401 (session required via Better Auth)
- Python error responses pass through unchanged (status code + JSON body)
- Analysis endpoints get 5-minute timeout, all others get 30-second timeout
- SSE token endpoint issues HMAC-SHA256 signed tokens with 10-minute expiry
- SSE client connects to Python directly for streaming, retries 3 times, falls back to polling
- Health check endpoint reports Python backend connection status
- PYTHON_SERVICE_KEY never exposed to browser (no NEXT_PUBLIC_ prefix)
- 22 tests passing (10 proxy + 3 SSE token + 9 SSE client)

## Task Commits

Each task was committed atomically:

1. **Task 1: BFF proxy, SSE token route, health check with tests** - `dac191d` (feat - TDD)
2. **Task 2: SSE client with polling fallback** - `bf8f1a7` (feat - TDD)

## Files Created/Modified
- `frontend/src/app/api/backend/[...path]/route.ts` - BFF catch-all proxy with timeout and error handling
- `frontend/src/app/api/backend/sse-token/route.ts` - HMAC-SHA256 signed SSE token issuance
- `frontend/src/app/api/backend/health/route.ts` - Python backend health check
- `frontend/src/lib/sse-client.ts` - SSE connection with retry and polling fallback
- `frontend/src/__tests__/proxy/bff-proxy.test.ts` - 10 tests for BFF proxy behavior
- `frontend/src/__tests__/proxy/sse-token.test.ts` - 3 tests for SSE token issuance
- `frontend/src/__tests__/proxy/sse-client.test.ts` - 9 tests for SSE client lifecycle
- `frontend/.env.local` - Added PYTHON_BACKEND_URL, PYTHON_SERVICE_KEY, SSE_TOKEN_SECRET, NEXT_PUBLIC_PYTHON_SSE_URL

## Decisions Made
- BFF proxy reads PYTHON_SERVICE_KEY from server-side env only (no NEXT_PUBLIC_ prefix)
- SSE token format: base64url(JSON payload).base64url(HMAC-SHA256 signature) -- matches Python validator
- Analysis endpoints (/api/analyze*) get 300s timeout; all others get 30s
- SSE client retries 3 times with linear backoff then falls back to HTTP polling every 3s

## Deviations from Plan

None - plan executed exactly as written.

## Next Phase Readiness
- BFF proxy layer complete -- all browser-to-Python requests go through Next.js API routes
- SSE client ready for analysis pipeline integration (Phase 13)
- File upload endpoints can use the same proxy pattern (Phase 12)

## Self-Check: PASSED

All 8 files verified on disk. Both task commits (dac191d, bf8f1a7) verified in git log.

---
*Phase: 11-python-backend-integration-bff-service-auth*
*Completed: 2026-03-11*
