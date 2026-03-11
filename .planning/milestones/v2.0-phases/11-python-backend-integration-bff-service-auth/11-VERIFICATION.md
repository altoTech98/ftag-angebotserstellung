---
phase: 11-python-backend-integration-bff-service-auth
verified: 2026-03-11T04:00:00Z
status: passed
score: 16/16 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 13/16
  gaps_closed:
    - "SSE token issued by Next.js is validated successfully by Python (encoding mismatch fixed)"
    - "SSE stream endpoint accepts valid tokens end-to-end (unblocked by encoding fix)"
    - "Cross-system token compatibility is tested automatically (new tests added)"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "End-to-end SSE streaming with real servers"
    expected: "EventSource in browser connects to Python SSE endpoint, receives progress events in real time"
    why_human: "SSE streaming behavior (keepalives, client close, real-time progress) cannot be verified programmatically without running both servers"
  - test: "Polling fallback activation after SSE failure"
    expected: "After 3 failed EventSource connections, sse-client.ts switches to polling /api/backend/analyze/status/{jobId} every 3 seconds"
    why_human: "Retry timing and fallback behavior require a running browser environment with EventSource simulation"
---

# Phase 11: Python Backend Integration – BFF & Service Auth Verification Report

**Phase Goal:** Replace legacy JWT auth with service-key authentication between Next.js BFF and Python backend, add SSE token validation for direct browser streaming, create BFF proxy layer with health check, and configure CORS for Next.js origin.
**Verified:** 2026-03-11T04:00:00Z
**Status:** PASSED
**Re-verification:** Yes — after gap closure (Plan 03 fixed SSE token encoding mismatch)

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Python rejects requests without a valid X-Service-Key header with 401 | VERIFIED | `service_auth.py` lines 72-76; 11 unit tests in `test_service_auth.py` |
| 2 | Python accepts requests with the correct X-Service-Key | VERIFIED | `service_key_middleware` passes to `call_next` on key match |
| 3 | Python extracts user context (id, role, email) from X-User-* headers | VERIFIED | `get_user_context()` in `service_auth.py` lines 81-92 |
| 4 | Python role enforcement returns 403 for unauthorized roles | VERIFIED | `require_role()` in `service_auth.py` lines 95-108 |
| 5 | Health and whitelist endpoints accessible without service key | VERIFIED | `AUTH_WHITELIST` in `service_auth.py` line 21; covers /health, /docs, /openapi.json, /redoc, /info, /, /api/health |
| 6 | SSE stream endpoint rejects requests without a valid SSE token with 401 | VERIFIED | `analyze.py` lines 53-57; `test_sse_stream_rejects_missing_token` and `test_sse_stream_rejects_invalid_token` pass |
| 7 | SSE stream endpoint accepts requests with a valid SSE token | VERIFIED | Token format is now compatible end-to-end: Next.js emits `base64url(payload).hex(HMAC-SHA256)`; Python `hexdigest()` matches; `test_validate_nextjs_format_token` proves interoperability |
| 8 | Browser requests to /api/backend/* are proxied to Python with service key and user context headers | VERIFIED | `route.ts` lines 37-42 set X-Service-Key, X-User-Id, X-User-Role, X-User-Email; 10 proxy tests pass |
| 9 | Unauthenticated proxy requests return 401 (session required) | VERIFIED | `route.ts` lines 16-22; `test_proxy_returns_401_without_session` passes |
| 10 | Python HTTP status codes and JSON error bodies pass through unchanged | VERIFIED | `route.ts` lines 74-79 stream response body with original status; proxy test covers 422 pass-through |
| 11 | Analysis endpoints get 5-minute timeout, all others get 30-second timeout | VERIFIED | `LONG_TIMEOUT_MS = 300_000`, `DEFAULT_TIMEOUT_MS = 30_000`; `LONG_TIMEOUT_PATHS` covers /api/analyze and /api/analyze/project |
| 12 | SSE token endpoint returns a signed HMAC token with user identity in hex format | VERIFIED | `sse-token/route.ts` line 33 uses `.digest('hex')`; format test confirms signature matches `/^[0-9a-f]{64}$/` |
| 13 | SSE client connects directly to Python for streaming, falls back to polling after 3 retries | VERIFIED | `sse-client.ts`: MAX_SSE_RETRIES=3, `startPolling()` activated after retries exhausted; 9 SSE client tests pass |
| 14 | Health check endpoint reports Python backend availability | VERIFIED | `health/route.ts` fetches Python /health with 5s timeout; returns `{status: "connected"}` or `{status: "disconnected", http: 503}` |
| 15 | PYTHON_SERVICE_KEY is never exposed to the browser (no NEXT_PUBLIC_ prefix) | VERIFIED | `process.env.PYTHON_SERVICE_KEY` used in server-only Route Handlers; grep returns 0 matches for `NEXT_PUBLIC_PYTHON_SERVICE_KEY` in frontend/src/ |
| 16 | SSE token validator accepts valid tokens and rejects expired/tampered/base64url-format | VERIFIED | 6 unit tests pass including `test_validate_nextjs_format_token` (cross-system) and `test_validate_rejects_base64url_signature` (regression) |

**Score:** 16/16 truths verified

---

## Required Artifacts

### Plan 01 — Python Backend

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/services/service_auth.py` | Service key middleware + user context + role enforcement | VERIFIED | 109 lines; exports `service_key_middleware`, `get_user_context`, `require_role` |
| `backend/services/sse_token_validator.py` | HMAC-signed SSE token validation (hex) | VERIFIED | 78 lines; uses `.hexdigest()` at line 61; expects `base64url(payload).hex(sig)` format |
| `backend/config.py` | PYTHON_SERVICE_KEY, SSE_TOKEN_SECRET, NEXTJS_ORIGIN settings | VERIFIED | All three settings present |
| `backend/main.py` | Service key middleware registered, CORS for Next.js | VERIFIED | `service_key_middleware` registered as `@app.middleware("http")`; CORS configured with explicit allowed headers |
| `backend/routers/analyze.py` | SSE stream endpoint validates token via `validate_sse_token()` | VERIFIED | Line 30: import; line 55: `payload = validate_sse_token(token)`; 401 on None |
| `backend/tests/test_service_auth.py` | 11 tests for service key, user context, role enforcement | VERIFIED | 11 tests with substantive coverage |
| `backend/tests/test_sse_token.py` | Tests including cross-system compatibility test | VERIFIED | `test_validate_nextjs_format_token` (line 113) and `test_validate_rejects_base64url_signature` (line 153) present |

### Plan 02 — Next.js BFF

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/src/app/api/backend/[...path]/route.ts` | BFF catch-all proxy | VERIFIED | 115 lines; exports GET, POST, PUT, DELETE, PATCH; service key + user context headers wired |
| `frontend/src/app/api/backend/sse-token/route.ts` | SSE token issuer using HMAC-SHA256 hex | VERIFIED | 42 lines; line 31-33: `createHmac('sha256', secret).update(payloadStr).digest('hex')`; no base64urlEncode helper remains |
| `frontend/src/app/api/backend/health/route.ts` | Python health check proxy | VERIFIED | 28 lines; substantive implementation with 5s timeout |
| `frontend/src/lib/sse-client.ts` | SSE connection with polling fallback | VERIFIED | 107 lines; exports `connectToAnalysis`, `AnalysisEvent`; retry + polling logic substantive |
| `frontend/.env.local` | PYTHON_BACKEND_URL, PYTHON_SERVICE_KEY, SSE_TOKEN_SECRET, NEXT_PUBLIC_PYTHON_SSE_URL | VERIFIED | All 4 vars present; PYTHON_SERVICE_KEY has no NEXT_PUBLIC_ prefix |
| `frontend/src/__tests__/proxy/bff-proxy.test.ts` | 10 tests for BFF proxy | VERIFIED | 10 substantive tests |
| `frontend/src/__tests__/proxy/sse-token.test.ts` | 3 tests including hex format check | VERIFIED | Line 69: `expect(parts[1]).toMatch(/^[0-9a-f]{64}$/)` confirms hex format |
| `frontend/src/__tests__/proxy/sse-client.test.ts` | 9 tests for SSE client lifecycle | VERIFIED | 9 substantive tests |

### Plan 03 — Gap Closure (Encoding Fix)

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/src/app/api/backend/sse-token/route.ts` | Hex-encoded HMAC signature (not base64url) | VERIFIED | Commit `18b1538`: removed `base64urlEncode` helper, `.digest('hex')` at line 33 |
| `frontend/src/__tests__/proxy/sse-token.test.ts` | Test verifying 64-character hex signature | VERIFIED | Commit `18b1538`: `/^[0-9a-f]{64}$/` regex check at line 69 |
| `backend/tests/test_sse_token.py` | Cross-system compatibility test + regression test | VERIFIED | Commit `3d3ab24`: both functions added (78 lines) |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `backend/main.py` | `backend/services/service_auth.py` | middleware registration | WIRED | `service_key_middleware` imported and registered as `@app.middleware("http")` |
| `backend/config.py` | `backend/services/service_auth.py` | PYTHON_SERVICE_KEY env var | WIRED | `service_auth.py` reads `os.environ.get("PYTHON_SERVICE_KEY", "")` directly |
| `backend/services/sse_token_validator.py` | `backend/config.py` | SSE_TOKEN_SECRET env var | WIRED | Line 40: reads `os.environ.get("SSE_TOKEN_SECRET", ...)` with PYTHON_SERVICE_KEY fallback |
| `backend/routers/analyze.py` | `backend/services/sse_token_validator.py` | validate_sse_token() call | WIRED | Line 30: import; line 55: `payload = validate_sse_token(token)` |
| `frontend/src/app/api/backend/[...path]/route.ts` | `backend/services/service_auth.py` | X-Service-Key header | WIRED | Line 38: `'X-Service-Key': PYTHON_SERVICE_KEY` on every proxied request |
| `frontend/src/app/api/backend/[...path]/route.ts` | `frontend/src/lib/auth.ts` | auth.api.getSession() | WIRED | Line 16: `auth.api.getSession({ headers: await headers() })` |
| `frontend/src/app/api/backend/sse-token/route.ts` | `backend/services/sse_token_validator.py` | HMAC-SHA256 hex token format | WIRED | Both sides use hex signature encoding; `test_validate_nextjs_format_token` proves interoperability |
| `frontend/src/lib/sse-client.ts` | `frontend/src/app/api/backend/sse-token/route.ts` | fetch /api/backend/sse-token | WIRED | Line 30: `fetch('/api/backend/sse-token')` before opening EventSource |
| `frontend/src/lib/sse-client.ts` | `backend/routers/analyze.py` | EventSource with token query param | WIRED | URL format correct (`?token=${token}`); token format now accepted by Python validator |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| AUTH-06 | 11-01, 11-02, 11-03 | JWT-Token-Bridging zwischen Next.js und Python-Backend | SATISFIED | Service key auth fully replaces JWT for BFF-to-Python requests. SSE token bridging complete: Next.js issues `base64url(payload).hex(HMAC-SHA256)` tokens; Python validates with `hexdigest()`; encoding compatible as proven by `test_validate_nextjs_format_token`. |
| INFRA-02 | 11-01 | Python/FastAPI auf Railway deployen mit Service-Auth | SATISFIED | Service key middleware, CORS for Next.js BFF, and all Python-side auth infrastructure complete. `service_key_middleware` registered in `main.py`; CORS configured with Next.js origin. |
| INFRA-03 | 11-02, 11-03 | BFF-Pattern: Next.js API Routes proxyen zu Python-Backend | SATISFIED | BFF catch-all proxy functional for all REST requests. SSE streaming path unblocked: token format fixed, `sse-client.ts` fetches token from `/api/backend/sse-token` and opens EventSource with token query param. Polling fallback available after 3 SSE retries. |

**Orphaned requirements check:** No additional Phase 11 requirements found in REQUIREMENTS.md beyond AUTH-06, INFRA-02, INFRA-03. No orphaned requirements.

---

## Anti-Patterns Found

No blocker or warning anti-patterns remain. The previous blocker (base64url signature encoding) was resolved by commit `18b1538`. The `base64urlEncode` helper was cleanly removed with no dead code remaining.

| File | Previous Pattern | Severity | Resolution |
|------|-----------------|----------|------------|
| `frontend/src/app/api/backend/sse-token/route.ts` | Base64url signature encoding | CLOSED | Commit `18b1538` replaced with `.digest('hex')` |
| `backend/tests/test_sse_token.py` | Tests did not cover cross-system token format | CLOSED | Commit `3d3ab24` added `test_validate_nextjs_format_token` |
| `frontend/src/__tests__/proxy/sse-token.test.ts` | Format test only checked `parts.length === 2` | CLOSED | Commit `18b1538` added hex regex assertion |

---

## Human Verification Required

### 1. End-to-End SSE Streaming Flow

**Test:** Start Python backend with `PYTHON_SERVICE_KEY=dev-service-key-change-in-production` and Next.js frontend. Trigger an analysis job through the UI and observe the browser network tab.

**Expected:** EventSource connects to `http://localhost:8000/api/analyze/stream/{job_id}?token=...`, Python returns `text/event-stream` events, browser receives real-time progress updates without falling back to polling.

**Why human:** SSE keepalives, client disconnection handling, and real-time event delivery cannot be verified programmatically without running both servers.

### 2. Polling Fallback Activation

**Test:** Force SSE to fail (block EventSource or use an unreachable SSE URL) and observe that the SSE client switches to polling after 3 retries with linear backoff.

**Expected:** After 3 failed EventSource connections (backoff 1s, 2s, 3s), `connectToAnalysis` activates `startPolling()` calling `/api/backend/analyze/status/{jobId}` every 3 seconds.

**Why human:** Retry timing and fallback activation require a running browser environment with the ability to simulate EventSource failure.

---

## Re-Verification Summary

All 3 gaps from the initial verification are closed. The root cause was a single encoding decision made independently in two plans: Next.js used `base64urlEncode(hmac.digest())` while Python used `.hexdigest()`. Plan 03 fixed this with surgical changes to 3 files, verified by 2 commits in git history:

- `sse-token/route.ts` (commit `18b1538`): Removed `base64urlEncode` helper entirely. Changed HMAC output to `.digest('hex')`. Token format is now `base64url(JSON_payload).hex(HMAC-SHA256)`.
- `sse-token.test.ts` (commit `18b1538`): Format test upgraded to assert signature is exactly 64 hex characters via `/^[0-9a-f]{64}$/`.
- `test_sse_token.py` (commit `3d3ab24`): Added `test_validate_nextjs_format_token` which replicates the Next.js token creation logic step-by-step and validates with `validate_sse_token()`. Added `test_validate_rejects_base64url_signature` as a regression guard.

No regressions were found in any of the 13 previously-passing must-haves.

---

_Verified: 2026-03-11T04:00:00Z_
_Verifier: Claude (gsd-verifier)_
_Re-verification after gap closure via Plan 03_
