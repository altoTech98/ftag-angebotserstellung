# Phase 11: Python Backend Integration (BFF + Service Auth) - Context

**Gathered:** 2026-03-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Next.js can securely proxy all requests to the Python/FastAPI backend via a BFF pattern, with service-level authentication and user context forwarding. SSE streaming from Python reaches the browser directly (with CORS), with a polling fallback. This phase delivers the code-level integration — actual server deployment (Docker, reverse proxy, SSL) is out of scope.

</domain>

<decisions>
## Implementation Decisions

### Token Bridging Strategy
- Service API key model: Next.js sends a shared secret (PYTHON_SERVICE_KEY env var) on every proxied request
- Python trusts Next.js as the auth gateway — no JWT login flow in Python
- User context passed as headers: X-User-Id, X-User-Role, X-User-Email
- Python enforces role checks on its own endpoints (defense in depth) using X-User-Role
- Python's existing JWT auth middleware and user management are replaced entirely with service auth — Python only accepts requests from Next.js (or dev tools with the service key)

### BFF Proxy Design
- Catch-all proxy route: /api/backend/[...path]/route.ts forwards to Python's /api/* endpoints
- URL mapping: /api/backend/analyze → Python /api/analyze (strip /api/backend prefix, forward to PYTHON_BACKEND_URL/api/*)
- Error handling: pass through Python's HTTP status codes and JSON error bodies as-is
- Timeouts: 30 seconds default, 5 minutes for analysis endpoints (configurable)
- Proxy adds service key + user context headers before forwarding

### SSE Streaming Approach
- SSE goes direct: browser connects to Python's SSE endpoint (e.g., https://api.ftag.ch/api/analyze/stream/{job_id}) — NOT proxied through Next.js
- SSE auth: short-lived SSE token issued by Next.js (GET /api/backend/sse-token), passed as ?token=xxx query param to Python
- Python validates the SSE token before allowing the stream
- CORS configured on Python to allow the Next.js origin
- Polling fallback: if SSE connection fails after 3 retries, frontend auto-switches to polling /api/backend/analyze/status/{job_id} every 3 seconds

### Deployment Topology
- Python deployed on self-hosted VPS, accessible via subdomain (e.g., api.ftag.ch)
- Phase 11 scope is code only + env vars — no Dockerfile, reverse proxy, or SSL config
- PYTHON_BACKEND_URL env var configures the Python backend URL (production: https://api.ftag.ch, dev: http://localhost:8000)
- Local dev: two separate processes (npm run dev + uvicorn), PYTHON_BACKEND_URL=http://localhost:8000 in .env.local

### Claude's Discretion
- Exact SSE token format and expiry (short-lived, e.g., 5-10 minutes)
- CORS header details on Python side
- Proxy implementation library choice (fetch, undici, etc.)
- Request/response header filtering (which headers to forward/strip)
- Health check endpoint design for monitoring Python availability from Next.js

</decisions>

<specifics>
## Specific Ideas

- Python backend's existing auth system (JWT login, user DB, auth middleware) gets fully replaced with service key auth — this is a simplification, not an addition
- The BFF catch-all pattern keeps the codebase minimal: one proxy handler instead of per-endpoint files
- SSE direct connection avoids Vercel's edge function streaming limitations entirely

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/src/app/proxy.ts`: Existing middleware for session cookie checking — proxy handler can reuse session extraction logic
- `frontend/src/lib/auth.ts`: Better Auth config with session management — provides user ID, role, email for headers
- `backend/routers/analyze.py`: SSE endpoint at /api/analyze/stream/{job_id} — already returns text/event-stream
- `backend/services/auth_service.py`: Current JWT auth — will be replaced but shows the pattern to follow for service key validation
- `backend/config.py`: Settings class — extend with PYTHON_SERVICE_KEY, CORS origins

### Established Patterns
- Python backend uses FastAPI middleware for auth — new service key auth follows same middleware pattern
- Better Auth uses cookie-based sessions (not localStorage JWT) — BFF reads session via server-side auth.api.getSession()
- Python endpoints return structured JSON errors with status codes — BFF passes these through unchanged

### Integration Points
- Next.js API route: /api/backend/[...path]/route.ts — new catch-all proxy handler
- Python middleware: replace auth_middleware in main.py with service key validation
- Python CORS: update main.py CORS config to allow Next.js origin for SSE
- Frontend: future phases will call /api/backend/* instead of Python directly
- SSE: frontend connects to PYTHON_BACKEND_URL directly for streaming events

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 11-python-backend-integration-bff-service-auth*
*Context gathered: 2026-03-11*
