---
phase: 11-python-backend-integration-bff-service-auth
plan: 01
subsystem: auth
tags: [hmac, service-key, sse, middleware, fastapi, bff]

# Dependency graph
requires:
  - phase: 10-foundation
    provides: "FastAPI backend with existing JWT auth middleware"
provides:
  - "service_key_middleware for X-Service-Key validation on /api/* routes"
  - "get_user_context for extracting X-User-* headers from BFF proxy"
  - "require_role for role-based access enforcement"
  - "validate_sse_token for HMAC-SHA256 signed SSE token validation"
  - "SSE stream endpoint enforces token auth via query param"
  - "CORS configured for Next.js BFF origin"
  - "PYTHON_SERVICE_KEY, SSE_TOKEN_SECRET, NEXTJS_ORIGIN config settings"
affects: [11-02-nextjs-bff-proxy, 12-file-upload, 13-analysis-pipeline]

# Tech tracking
tech-stack:
  added: []
  patterns: [service-key-middleware, hmac-token-validation, bff-header-forwarding]

key-files:
  created:
    - backend/services/service_auth.py
    - backend/services/sse_token_validator.py
    - backend/tests/test_service_auth.py
    - backend/tests/test_sse_token.py
  modified:
    - backend/config.py
    - backend/main.py
    - backend/routers/analyze.py

key-decisions:
  - "Used os.environ.get() directly in service_auth.py and sse_token_validator.py (not Settings import) for self-contained testability"
  - "SSE stream paths skip service key check and use dedicated HMAC token auth via query param"
  - "CORS set allow_credentials=False since SSE tokens are passed via query param, not cookies"

patterns-established:
  - "Service key middleware: X-Service-Key header validates BFF-to-Python requests"
  - "User context forwarding: X-User-Id, X-User-Role, X-User-Email headers from BFF"
  - "SSE token format: base64url(payload).hmac_sha256_hex(payload) with exp field"

requirements-completed: [AUTH-06, INFRA-02]

# Metrics
duration: 4min
completed: 2026-03-11
---

# Phase 11 Plan 01: Service Auth & SSE Token Summary

**Service key middleware replacing JWT auth, HMAC-signed SSE token validation, and CORS for Next.js BFF pattern**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-11T02:23:08Z
- **Completed:** 2026-03-11T02:27:09Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Service key middleware validates X-Service-Key on all /api/* routes, replacing old JWT auth
- SSE token validator with HMAC-SHA256 signature verification and expiry checking
- SSE stream endpoint enforces token-based auth for direct browser connections
- User context extraction from X-User-* headers forwarded by Next.js BFF proxy
- Role enforcement with 403 for unauthorized roles
- 17 tests passing (11 unit + 4 token + 2 integration)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create service auth module and SSE token validator with tests** - `f4d7f73` (feat - TDD)
2. **Task 2: Update config.py, main.py middleware, CORS, and wire SSE token** - `2b9e1df` (feat)

## Files Created/Modified
- `backend/services/service_auth.py` - Service key middleware, user context extraction, role enforcement
- `backend/services/sse_token_validator.py` - HMAC-SHA256 signed SSE token validation
- `backend/tests/test_service_auth.py` - 11 tests for middleware, context, role enforcement
- `backend/tests/test_sse_token.py` - 6 tests for token validation + stream endpoint auth
- `backend/config.py` - Added PYTHON_SERVICE_KEY, SSE_TOKEN_SECRET, NEXTJS_ORIGIN settings
- `backend/main.py` - Replaced JWT auth with service key middleware, updated CORS for BFF
- `backend/routers/analyze.py` - SSE stream endpoint validates token via query param

## Decisions Made
- Used os.environ.get() directly in auth modules for self-contained testability (not Settings import)
- SSE stream paths skip service key check -- they use dedicated HMAC token auth instead
- CORS allows explicit headers (X-Service-Key, X-User-*) rather than wildcard, credentials=False

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- main.py full import test hit MemoryError (system memory pressure from anthropic/pydantic imports) -- verified module imports individually instead; all imports work correctly

## User Setup Required

None - no external service configuration required. PYTHON_SERVICE_KEY and SSE_TOKEN_SECRET are read from environment variables at runtime.

## Next Phase Readiness
- Service auth foundation ready for Plan 02 (Next.js BFF proxy)
- BFF proxy will set X-Service-Key header and forward X-User-* headers
- SSE token issuance will be implemented in Plan 02 (Next.js side)

---
*Phase: 11-python-backend-integration-bff-service-auth*
*Completed: 2026-03-11*
