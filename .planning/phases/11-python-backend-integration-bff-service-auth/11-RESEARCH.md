# Phase 11: Python Backend Integration (BFF + Service Auth) - Research

**Researched:** 2026-03-11
**Domain:** Next.js BFF proxy pattern, FastAPI service authentication, SSE streaming
**Confidence:** HIGH

## Summary

This phase connects the Next.js frontend to the existing Python/FastAPI backend using a Backend-for-Frontend (BFF) proxy pattern. The browser never calls Python directly for CRUD operations -- all requests route through a Next.js catch-all API route that adds service authentication headers. SSE streaming for analysis progress goes direct from browser to Python (bypassing Next.js) using short-lived SSE tokens.

The existing Python backend has a full JWT auth system (auth_service.py, auth router, auth middleware in main.py) that will be **replaced** with a simpler service key + user context header model. The existing Next.js frontend has Better Auth with cookie-based sessions, roles (viewer/analyst/manager/admin), and an admin plugin -- the BFF proxy reads these sessions server-side to extract user context.

**Primary recommendation:** Use a single Next.js catch-all Route Handler at `/api/backend/[...path]/route.ts` with native `fetch()` for proxying. Replace Python's JWT auth middleware with a service key check (`X-Service-Key` header) and user context extraction from `X-User-Id`, `X-User-Role`, `X-User-Email` headers. Issue short-lived HMAC-signed SSE tokens from a dedicated Next.js route.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Service API key model: Next.js sends a shared secret (PYTHON_SERVICE_KEY env var) on every proxied request
- Python trusts Next.js as the auth gateway -- no JWT login flow in Python
- User context passed as headers: X-User-Id, X-User-Role, X-User-Email
- Python enforces role checks on its own endpoints (defense in depth) using X-User-Role
- Python's existing JWT auth middleware and user management are replaced entirely with service auth
- Catch-all proxy route: /api/backend/[...path]/route.ts forwards to Python's /api/* endpoints
- URL mapping: /api/backend/analyze -> Python /api/analyze (strip /api/backend prefix, forward to PYTHON_BACKEND_URL/api/*)
- Error handling: pass through Python's HTTP status codes and JSON error bodies as-is
- Timeouts: 30 seconds default, 5 minutes for analysis endpoints (configurable)
- SSE goes direct: browser connects to Python's SSE endpoint -- NOT proxied through Next.js
- SSE auth: short-lived SSE token issued by Next.js (GET /api/backend/sse-token), passed as ?token=xxx query param to Python
- CORS configured on Python to allow the Next.js origin
- Polling fallback: if SSE connection fails after 3 retries, frontend auto-switches to polling /api/backend/analyze/status/{job_id} every 3 seconds
- Python deployed on self-hosted VPS, accessible via subdomain (e.g., api.ftag.ch)
- Phase 11 scope is code only + env vars -- no Dockerfile, reverse proxy, or SSL config
- PYTHON_BACKEND_URL env var configures the Python backend URL

### Claude's Discretion
- Exact SSE token format and expiry (short-lived, e.g., 5-10 minutes)
- CORS header details on Python side
- Proxy implementation library choice (fetch, undici, etc.)
- Request/response header filtering (which headers to forward/strip)
- Health check endpoint design for monitoring Python availability from Next.js

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| AUTH-06 | JWT-Token-Bridging zwischen Next.js und Python-Backend | BFF proxy reads Better Auth session, forwards user context as X-User-* headers; Python validates service key and extracts role for authorization |
| INFRA-02 | Python/FastAPI auf Railway deployen mit Service-Auth | Service key middleware on Python replaces JWT auth; PYTHON_SERVICE_KEY env var validated on every request; code-only scope (no deployment config) |
| INFRA-03 | BFF-Pattern: Next.js API Routes proxyen zu Python-Backend | Catch-all Route Handler at /api/backend/[...path]/route.ts using native fetch; strips prefix, forwards with service key + user context headers |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Next.js Route Handlers | 16.1.6 | BFF catch-all proxy | Official App Router pattern, native fetch, no extra deps |
| better-auth | 1.5.4+ | Session extraction in proxy | Already installed, provides server-side getSession() |
| FastAPI middleware | 0.115+ | Service key validation | Already in place, just swap JWT check for key check |
| python-jose | 3.3.0 | SSE token creation/validation | Already in requirements.txt, HMAC-SHA256 signing |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| native fetch | built-in | HTTP proxy calls | All proxy requests from Next.js to Python |
| AbortController | built-in | Request timeout enforcement | Wrap fetch with signal for 30s/300s timeouts |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| native fetch | undici, node-fetch, http-proxy | fetch is built-in to Node.js 18+, no extra dep; undici slightly faster but unnecessary complexity |
| python-jose for SSE tokens | hashlib HMAC | python-jose already installed, provides clean JWT encode/decode; raw HMAC would need manual format |

**Installation:**
No new packages needed. All dependencies already exist in both frontend and backend.

## Architecture Patterns

### Recommended Project Structure
```
frontend/src/
├── app/
│   └── api/
│       ├── auth/[...all]/route.ts      # Better Auth (existing)
│       └── backend/
│           ├── [...path]/route.ts       # BFF catch-all proxy
│           └── sse-token/route.ts       # SSE token issuer
├── lib/
│   ├── auth.ts                          # Better Auth server config (existing)
│   ├── auth-client.ts                   # Better Auth client (existing)
│   ├── python-proxy.ts                  # Proxy utility: fetch + headers + timeout
│   └── sse-token.ts                     # SSE token generation (HMAC)

backend/
├── main.py                              # Replace auth_middleware with service_key_middleware
├── config.py                            # Add PYTHON_SERVICE_KEY, NEXTJS_ORIGIN, SSE_TOKEN_SECRET
├── services/
│   ├── service_auth.py                  # Service key validation + user context extraction
│   └── sse_token_validator.py           # Validate SSE tokens from query param
├── routers/
│   └── analyze.py                       # SSE endpoint updated to check SSE token
```

### Pattern 1: BFF Catch-All Proxy Route Handler
**What:** Single Next.js API route that forwards all /api/backend/* requests to Python
**When to use:** Every CRUD operation from browser to Python backend
**Example:**
```typescript
// Source: Next.js 16 official docs - BFF catch-all pattern
// frontend/src/app/api/backend/[...path]/route.ts

import { auth } from "@/lib/auth";
import { headers } from "next/headers";

const PYTHON_URL = process.env.PYTHON_BACKEND_URL || "http://localhost:8000";
const SERVICE_KEY = process.env.PYTHON_SERVICE_KEY!;

// Timeout config: 5 min for analysis, 30s default
const ANALYSIS_PATHS = ["/api/analyze", "/api/analyze/project"];
const ANALYSIS_TIMEOUT = 300_000;
const DEFAULT_TIMEOUT = 30_000;

async function proxyToPython(request: Request, params: { path: string[] }) {
  // 1. Verify session (Better Auth server-side)
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session?.user) {
    return Response.json({ error: "Nicht authentifiziert" }, { status: 401 });
  }

  // 2. Build target URL
  const path = params.path.join("/");
  const url = new URL(`/api/${path}`, PYTHON_URL);
  // Forward query params
  const incomingUrl = new URL(request.url);
  url.search = incomingUrl.search;

  // 3. Determine timeout
  const timeout = ANALYSIS_PATHS.some(p => url.pathname.startsWith(p))
    ? ANALYSIS_TIMEOUT : DEFAULT_TIMEOUT;

  // 4. Build forwarded headers
  const forwardHeaders = new Headers();
  forwardHeaders.set("X-Service-Key", SERVICE_KEY);
  forwardHeaders.set("X-User-Id", session.user.id);
  forwardHeaders.set("X-User-Role", session.user.role || "viewer");
  forwardHeaders.set("X-User-Email", session.user.email);
  forwardHeaders.set("Content-Type", request.headers.get("Content-Type") || "application/json");

  // 5. Proxy the request
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(url.toString(), {
      method: request.method,
      headers: forwardHeaders,
      body: request.method !== "GET" && request.method !== "HEAD"
        ? await request.arrayBuffer() : undefined,
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    // 6. Pass through Python's response as-is
    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: {
        "Content-Type": response.headers.get("Content-Type") || "application/json",
      },
    });
  } catch (error) {
    clearTimeout(timeoutId);
    if (error instanceof DOMException && error.name === "AbortError") {
      return Response.json({ error: "Request timeout" }, { status: 504 });
    }
    return Response.json({ error: "Backend nicht erreichbar" }, { status: 502 });
  }
}

export async function GET(req: Request, ctx: { params: Promise<{ path: string[] }> }) {
  return proxyToPython(req, await ctx.params);
}
export async function POST(req: Request, ctx: { params: Promise<{ path: string[] }> }) {
  return proxyToPython(req, await ctx.params);
}
export async function PUT(req: Request, ctx: { params: Promise<{ path: string[] }> }) {
  return proxyToPython(req, await ctx.params);
}
export async function DELETE(req: Request, ctx: { params: Promise<{ path: string[] }> }) {
  return proxyToPython(req, await ctx.params);
}
```

### Pattern 2: Python Service Key Middleware
**What:** Replace JWT auth middleware with service key validation
**When to use:** Every incoming request to Python /api/* endpoints
**Example:**
```python
# backend/services/service_auth.py
import os
import logging
from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

PYTHON_SERVICE_KEY = os.environ.get("PYTHON_SERVICE_KEY", "")

async def service_key_middleware(request: Request, call_next):
    """Validate service key on all /api/* routes (except health/whitelist)."""
    path = request.url.path
    method = request.method

    # Whitelist: health checks, docs, OPTIONS preflight
    WHITELIST = {"/health", "/api/health", "/docs", "/redoc", "/openapi.json", "/info", "/"}
    if method == "OPTIONS" or path in WHITELIST or not path.startswith("/api/"):
        return await call_next(request)

    # Check for SSE token auth (query param) on streaming endpoints
    if path.startswith("/api/analyze/stream/"):
        # SSE tokens validated separately in the route
        return await call_next(request)

    # Validate service key
    service_key = request.headers.get("X-Service-Key", "")
    if not service_key or service_key != PYTHON_SERVICE_KEY:
        logger.warning(f"[AUTH] Rejected request to {path}: invalid service key")
        return JSONResponse(
            status_code=401,
            content={"detail": "Ungueltige Service-Authentifizierung"},
        )

    return await call_next(request)


def get_user_context(request: Request) -> dict:
    """Extract user context from forwarded headers."""
    return {
        "user_id": request.headers.get("X-User-Id", ""),
        "role": request.headers.get("X-User-Role", "viewer"),
        "email": request.headers.get("X-User-Email", ""),
    }
```

### Pattern 3: SSE Token Flow
**What:** Short-lived token for browser-to-Python SSE connections
**When to use:** Before browser opens EventSource to Python's SSE endpoint
**Example:**
```typescript
// frontend/src/app/api/backend/sse-token/route.ts
import { auth } from "@/lib/auth";
import { headers } from "next/headers";
import crypto from "crypto";

const SSE_TOKEN_SECRET = process.env.SSE_TOKEN_SECRET || process.env.PYTHON_SERVICE_KEY!;
const SSE_TOKEN_EXPIRY_MINUTES = 10;

export async function GET() {
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session?.user) {
    return Response.json({ error: "Nicht authentifiziert" }, { status: 401 });
  }

  const payload = {
    sub: session.user.id,
    role: session.user.role || "viewer",
    email: session.user.email,
    exp: Math.floor(Date.now() / 1000) + SSE_TOKEN_EXPIRY_MINUTES * 60,
    iat: Math.floor(Date.now() / 1000),
  };

  // HMAC-signed token (compact, no library needed on frontend)
  const payloadB64 = Buffer.from(JSON.stringify(payload)).toString("base64url");
  const signature = crypto
    .createHmac("sha256", SSE_TOKEN_SECRET)
    .update(payloadB64)
    .digest("base64url");
  const token = `${payloadB64}.${signature}`;

  return Response.json({ token, expires_in: SSE_TOKEN_EXPIRY_MINUTES * 60 });
}
```

```python
# backend/services/sse_token_validator.py
import base64
import hashlib
import hmac
import json
import os
import time
import logging

logger = logging.getLogger(__name__)

SSE_TOKEN_SECRET = os.environ.get("SSE_TOKEN_SECRET", os.environ.get("PYTHON_SERVICE_KEY", ""))

def validate_sse_token(token: str) -> dict | None:
    """Validate HMAC-signed SSE token. Returns payload or None."""
    try:
        parts = token.split(".")
        if len(parts) != 2:
            return None
        payload_b64, signature = parts
        # Verify signature
        expected_sig = hmac.new(
            SSE_TOKEN_SECRET.encode(),
            payload_b64.encode(),
            hashlib.sha256,
        ).digest()
        expected_sig_b64 = base64.urlsafe_b64encode(expected_sig).rstrip(b"=").decode()
        if not hmac.compare_digest(signature, expected_sig_b64):
            return None
        # Decode payload
        # Add padding for base64url
        padded = payload_b64 + "=" * (4 - len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded))
        # Check expiry
        if payload.get("exp", 0) < time.time():
            logger.warning("SSE token expired")
            return None
        return payload
    except Exception as e:
        logger.warning(f"SSE token validation failed: {e}")
        return None
```

### Pattern 4: Health Check Endpoint
**What:** Next.js route that checks Python backend availability
**When to use:** Dashboard status indicators, monitoring
**Example:**
```typescript
// frontend/src/app/api/backend/health/route.ts
const PYTHON_URL = process.env.PYTHON_BACKEND_URL || "http://localhost:8000";

export async function GET() {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000);
    const res = await fetch(`${PYTHON_URL}/health`, { signal: controller.signal });
    clearTimeout(timeoutId);
    const data = await res.json();
    return Response.json({ status: "connected", python: data });
  } catch {
    return Response.json({ status: "disconnected" }, { status: 503 });
  }
}
```

### Anti-Patterns to Avoid
- **Proxying SSE through Next.js/Vercel:** Vercel edge functions have timeout and streaming limitations. SSE must go direct from browser to Python.
- **Storing PYTHON_SERVICE_KEY in client-side code:** The service key is server-only; it lives in Next.js environment vars (not NEXT_PUBLIC_*).
- **Using request.json() in proxy before forwarding:** This consumes the body. Use request.arrayBuffer() to forward the raw body.
- **Forwarding all incoming headers to Python:** Security risk. Only forward Content-Type and explicitly set service/user headers.
- **Putting auth logic in proxy.ts (formerly middleware.ts):** proxy.ts runs on edge/CDN, cannot do full session checks. Use Route Handler for auth.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Session extraction | Custom cookie parser | `auth.api.getSession({ headers })` | Better Auth handles cookie parsing, session validation, expiry |
| Token signing | Custom crypto format | HMAC-SHA256 with base64url encoding | Standard, simple, no library bloat; python-jose available if JWT preferred |
| CORS configuration | Manual header injection | FastAPI CORSMiddleware | Handles preflight, caching, credentials correctly |
| Request timeout | Custom Promise.race | AbortController + setTimeout | Native API, works with fetch, proper cleanup |

**Key insight:** The entire BFF proxy is ~80 lines of code using native fetch. No proxy libraries needed. The complexity is in getting the auth flow right, not in the HTTP plumbing.

## Common Pitfalls

### Pitfall 1: Better Auth Session Not Available in Route Handler
**What goes wrong:** `auth.api.getSession()` returns null because cookies aren't forwarded correctly
**Why it happens:** Route Handlers don't automatically have access to the request's cookies unless you pass headers explicitly
**How to avoid:** Always pass `{ headers: await headers() }` from `next/headers` to `getSession()`
**Warning signs:** All proxy requests return 401 even when logged in

### Pitfall 2: Next.js 16 Route Handler Params Are Promises
**What goes wrong:** `params.path` is undefined because params is a Promise
**Why it happens:** Next.js 16 changed route handler params to be async (Promise-based)
**How to avoid:** Always `await ctx.params` before accessing `.path`
**Warning signs:** TypeError: Cannot read properties of undefined

### Pitfall 3: Request Body Consumed Before Forwarding
**What goes wrong:** Python receives empty body on POST/PUT requests
**Why it happens:** Calling `request.json()` or `request.text()` consumes the ReadableStream
**How to avoid:** Use `request.arrayBuffer()` for forwarding raw body, or `request.clone()` if you need to read it
**Warning signs:** Python returns 422 validation errors on requests that work when called directly

### Pitfall 4: SSE CORS Preflight Missing
**What goes wrong:** Browser blocks EventSource connection to Python
**Why it happens:** EventSource doesn't support custom headers but CORS still applies for cross-origin
**How to avoid:** Python CORS must explicitly list the Next.js origin (not wildcard with credentials). EventSource doesn't send preflight, but if using withCredentials, CORS must be correct.
**Warning signs:** Browser console shows CORS errors on SSE endpoint

### Pitfall 5: Service Key Leaked to Client
**What goes wrong:** PYTHON_SERVICE_KEY appears in browser network tab or client bundle
**Why it happens:** Using NEXT_PUBLIC_ prefix or including key in client-side fetch calls
**How to avoid:** Service key is ONLY used in Route Handlers (server-side). Never prefix with NEXT_PUBLIC_. SSE uses separate token mechanism.
**Warning signs:** Service key visible in browser DevTools

### Pitfall 6: Python CORS allow_credentials with Wildcard Origins
**What goes wrong:** Browser rejects CORS response
**Why it happens:** `allow_credentials=True` with `allow_origins=["*"]` is invalid per CORS spec
**How to avoid:** When using credentials (cookies/auth), list explicit origins, never wildcard
**Warning signs:** CORS error mentioning credentials and wildcard

### Pitfall 7: AbortController Signal Not Cleaned Up
**What goes wrong:** Memory leaks, unexpected request cancellations
**Why it happens:** setTimeout not cleared after successful response
**How to avoid:** Always clearTimeout in both success and error paths
**Warning signs:** Requests sometimes abort prematurely under load

## Code Examples

### Python CORS Configuration for SSE
```python
# In backend/main.py - Updated CORS for v2
from config import settings

# Production: explicit Next.js origin for SSE direct connections
NEXTJS_ORIGIN = os.environ.get("NEXTJS_ORIGIN", "http://localhost:3000")

_cors_origins = [NEXTJS_ORIGIN]
if settings.ENVIRONMENT == "development":
    _cors_origins.extend([
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
    ])
elif settings.ENVIRONMENT == "production":
    _cors_origins.extend(settings.CORS_ORIGINS)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,  # SSE tokens via query param, no cookies needed
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["X-Service-Key", "X-User-Id", "X-User-Role", "X-User-Email", "Content-Type"],
    max_age=3600,
)
```

### SSE Endpoint with Token Validation
```python
# Updated backend/routers/analyze.py - stream endpoint
from services.sse_token_validator import validate_sse_token

@router.get("/analyze/stream/{job_id}")
async def stream_analyze_status(job_id: str, token: str = ""):
    """SSE endpoint with token-based auth for direct browser connections."""
    # Validate SSE token
    if not token:
        raise HTTPException(status_code=401, detail="SSE token required")
    payload = validate_sse_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired SSE token")

    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job nicht gefunden")

    # ... existing SSE logic unchanged ...
```

### Frontend SSE Client with Polling Fallback
```typescript
// frontend/src/lib/sse-client.ts (utility for future phases)
const MAX_SSE_RETRIES = 3;
const POLL_INTERVAL = 3000;

export async function connectToAnalysis(
  jobId: string,
  onEvent: (data: any) => void,
  onError?: (error: Error) => void,
) {
  const pythonUrl = process.env.NEXT_PUBLIC_PYTHON_SSE_URL; // Only the SSE base URL is public
  if (!pythonUrl) throw new Error("NEXT_PUBLIC_PYTHON_SSE_URL not configured");

  // 1. Get SSE token from our BFF
  const tokenRes = await fetch("/api/backend/sse-token");
  if (!tokenRes.ok) throw new Error("Failed to get SSE token");
  const { token } = await tokenRes.json();

  // 2. Try SSE connection
  let retries = 0;
  function attemptSSE() {
    const es = new EventSource(
      `${pythonUrl}/api/analyze/stream/${jobId}?token=${token}`
    );
    es.onmessage = (event) => {
      const data = JSON.parse(event.data);
      onEvent(data);
      if (data.status === "completed" || data.status === "failed") {
        es.close();
      }
    };
    es.onerror = () => {
      es.close();
      retries++;
      if (retries < MAX_SSE_RETRIES) {
        setTimeout(attemptSSE, 1000);
      } else {
        // 3. Fallback to polling
        startPolling(jobId, onEvent, onError);
      }
    };
    return es;
  }

  return attemptSSE();
}

function startPolling(
  jobId: string,
  onEvent: (data: any) => void,
  onError?: (error: Error) => void,
) {
  const interval = setInterval(async () => {
    try {
      const res = await fetch(`/api/backend/analyze/status/${jobId}`);
      if (!res.ok) throw new Error(`Status ${res.status}`);
      const data = await res.json();
      onEvent(data);
      if (data.status === "completed" || data.status === "failed") {
        clearInterval(interval);
      }
    } catch (err) {
      onError?.(err instanceof Error ? err : new Error(String(err)));
    }
  }, POLL_INTERVAL);
}
```

### Environment Variables
```bash
# frontend/.env.local (add these)
PYTHON_BACKEND_URL=http://localhost:8000
PYTHON_SERVICE_KEY=dev-service-key-change-in-production
SSE_TOKEN_SECRET=dev-sse-secret-change-in-production
NEXT_PUBLIC_PYTHON_SSE_URL=http://localhost:8000

# backend/.env (add these)
PYTHON_SERVICE_KEY=dev-service-key-change-in-production
SSE_TOKEN_SECRET=dev-sse-secret-change-in-production
NEXTJS_ORIGIN=http://localhost:3000
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Next.js middleware.ts | proxy.ts (renamed) | Next.js 16.0.0 | Function renamed from `middleware` to `proxy`; same functionality |
| Pages Router API routes | App Router Route Handlers | Next.js 13+ | Catch-all uses [...path]/route.ts not [...path].ts |
| Route handler params as object | Params as Promise | Next.js 15+ | Must await params: `const { path } = await ctx.params` |
| Python JWT per-user auth | Service key + user context headers | This phase | Simplification: Python trusts Next.js as auth gateway |

**Deprecated/outdated:**
- `middleware.ts`: Renamed to `proxy.ts` in Next.js 16. Codemod available: `npx @next/codemod@canary middleware-to-proxy .`
- Python's auth_service.py JWT flow: Being replaced with service key auth in this phase
- Python's auth router (/api/auth/login, /api/auth/me): No longer needed after service auth migration

## Open Questions

1. **Better Auth session.user.role field name**
   - What we know: Better Auth admin plugin assigns roles, stored in DB
   - What's unclear: Exact field path -- is it `session.user.role` or `session.user.adminRole` or accessed differently?
   - Recommendation: Check at implementation time via `console.log(session)` in dev. The permissions.ts shows roles are "viewer", "analyst", "manager", "admin"

2. **Python's v2 routers compatibility**
   - What we know: main.py lazy-imports v2 routers (upload_v2, analyze_v2, feedback_v2)
   - What's unclear: Whether these also need service key auth or have their own auth
   - Recommendation: Service key middleware applies globally to all /api/* routes, so v2 routers get it automatically

3. **File upload body size through proxy**
   - What we know: Python allows up to 500MB files. Vercel has 4.5MB body limit.
   - What's unclear: Whether file uploads will go through BFF proxy or use Vercel Blob (Phase 12)
   - Recommendation: For now, proxy handles it. Phase 12 (INFRA-04) switches to Vercel Blob with presigned URLs, bypassing the proxy for large uploads entirely.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework (frontend) | vitest 4.0.18 + jsdom |
| Framework (backend) | pytest 7.4.4 + pytest-asyncio |
| Config file (frontend) | frontend/vitest.config.ts |
| Config file (backend) | backend/tests/conftest.py |
| Quick run (frontend) | `cd frontend && npx vitest run --reporter=verbose` |
| Quick run (backend) | `cd backend && python -m pytest tests/ -x -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AUTH-06 | BFF proxy reads session and forwards user context headers | unit | `cd frontend && npx vitest run src/__tests__/proxy.test.ts` | No -- Wave 0 |
| AUTH-06 | Python validates service key and rejects without it | unit | `cd backend && python -m pytest tests/test_service_auth.py -x` | No -- Wave 0 |
| INFRA-02 | Python service key middleware replaces JWT auth | integration | `cd backend && python -m pytest tests/test_service_auth.py -x` | No -- Wave 0 |
| INFRA-03 | Catch-all proxy forwards requests to Python | unit | `cd frontend && npx vitest run src/__tests__/proxy.test.ts` | No -- Wave 0 |
| INFRA-03 | SSE token issuance and validation | unit | `cd backend && python -m pytest tests/test_sse_token.py -x` | No -- Wave 0 |
| INFRA-03 | Polling fallback when SSE fails | unit | `cd frontend && npx vitest run src/__tests__/sse-client.test.ts` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `cd frontend && npx vitest run --reporter=verbose` and `cd backend && python -m pytest tests/test_service_auth.py tests/test_sse_token.py -x -q`
- **Per wave merge:** Full frontend + backend test suites
- **Phase gate:** All new tests green + existing tests unbroken

### Wave 0 Gaps
- [ ] `frontend/src/__tests__/proxy.test.ts` -- covers AUTH-06, INFRA-03 (mock fetch, verify headers)
- [ ] `backend/tests/test_service_auth.py` -- covers AUTH-06, INFRA-02 (test middleware accepts/rejects)
- [ ] `backend/tests/test_sse_token.py` -- covers INFRA-03 (token creation, validation, expiry)
- [ ] `frontend/src/__tests__/sse-client.test.ts` -- covers INFRA-03 (SSE + polling fallback)

## Sources

### Primary (HIGH confidence)
- [Next.js 16 BFF Guide](https://nextjs.org/docs/app/guides/backend-for-frontend) - Official catch-all proxy pattern with Route Handlers
- [Next.js 16 proxy.ts (formerly middleware.ts)](https://nextjs.org/docs/app/api-reference/file-conventions/proxy) - proxy.ts is renamed middleware, NOT an HTTP proxy
- [Next.js 16 Route Handlers](https://nextjs.org/docs/app/getting-started/route-handlers) - Official route handler docs
- Existing codebase: `backend/main.py`, `backend/routers/analyze.py`, `frontend/src/lib/auth.ts` - Direct code inspection

### Secondary (MEDIUM confidence)
- [BFF Pattern with Next.js API Routes](https://medium.com/digigeek/bff-backend-for-frontend-pattern-with-next-js-api-routes-secure-and-scalable-architecture-d6e088a39855) - Community pattern verification
- [FastAPI API Key Authentication](https://itsjoshcampos.codes/fast-api-api-key-authorization) - Header-based API key patterns
- [Securing FastAPI with JWT](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/) - FastAPI official security docs

### Tertiary (LOW confidence)
- SSE token pattern is a well-known approach but no single authoritative source; implementation based on standard HMAC signing

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries already installed, official Next.js docs confirm pattern
- Architecture: HIGH - Direct code inspection of existing backend, official BFF docs from Next.js
- Pitfalls: HIGH - Based on known Next.js 16 breaking changes (Promise params) and common CORS issues
- SSE token format: MEDIUM - Custom HMAC approach is standard crypto but not a library pattern

**Research date:** 2026-03-11
**Valid until:** 2026-04-11 (stable patterns, unlikely to change)
