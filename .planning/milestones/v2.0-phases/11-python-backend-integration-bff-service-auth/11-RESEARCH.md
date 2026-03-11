# Phase 11: Python Backend Integration (BFF + Service Auth) - Research

**Researched:** 2026-03-11
**Domain:** Next.js BFF proxy pattern, FastAPI service authentication, SSE streaming
**Confidence:** HIGH

## Summary

This phase connects the Next.js frontend to the existing Python/FastAPI backend using a Backend-for-Frontend (BFF) proxy pattern. The browser never calls Python directly for CRUD operations -- all requests route through a Next.js catch-all API route that adds service authentication headers. SSE streaming for analysis progress goes direct from browser to Python (bypassing Next.js) using short-lived SSE tokens.

The existing Python backend has a full JWT auth system (`backend/services/auth_service.py` with bcrypt+jose, `backend/routers/auth.py` with login/me/logout/users endpoints, and an auth middleware in `main.py` lines 280-324) that will be **replaced** with a simpler service key + user context header model. The existing Next.js frontend has Better Auth (v1.5.4) with cookie-based sessions, 4 roles (viewer/analyst/manager/admin), and an admin plugin -- the BFF proxy reads these sessions server-side to extract user context.

**Primary recommendation:** Use a single Next.js catch-all Route Handler at `/api/backend/[...path]/route.ts` with native `fetch()` for proxying (pattern confirmed by official Next.js 16 BFF docs). Replace Python's JWT auth middleware with a service key check (`X-Service-Key` header) and user context extraction from `X-User-Id`, `X-User-Role`, `X-User-Email` headers. Issue short-lived HMAC-signed SSE tokens from a dedicated Next.js route.

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
| AUTH-06 | JWT-Token-Bridging zwischen Next.js und Python-Backend | BFF proxy reads Better Auth session via `auth.api.getSession({ headers: await headers() })`, forwards user context as X-User-* headers; Python validates service key and extracts role for authorization |
| INFRA-02 | Python/FastAPI auf VPS deployen mit Service-Auth | Service key middleware on Python replaces JWT auth; PYTHON_SERVICE_KEY env var validated on every request; existing auth_middleware in main.py (lines 280-324) gets replaced; code-only scope (no deployment config) |
| INFRA-03 | BFF-Pattern: Next.js API Routes proxyen zu Python-Backend | Catch-all Route Handler at /api/backend/[...path]/route.ts using native fetch (pattern confirmed by Next.js 16 official BFF docs); strips prefix, forwards with service key + user context headers |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Next.js Route Handlers | 16.1.6 | BFF catch-all proxy | Official App Router pattern, native fetch, no extra deps; official BFF guide shows exact catch-all pattern |
| better-auth | 1.5.4+ | Session extraction in proxy | Already installed, provides server-side `auth.api.getSession()` |
| FastAPI middleware | 0.115+ | Service key validation | Already in place at main.py, just swap JWT check for key check |
| Node.js crypto | built-in | SSE token HMAC signing | No library needed, `crypto.createHmac()` is native |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| native fetch | built-in | HTTP proxy calls | All proxy requests from Next.js to Python |
| AbortController | built-in | Request timeout enforcement | Wrap fetch with signal for 30s/300s timeouts |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| native fetch | undici, node-fetch, http-proxy | fetch is built-in to Node.js 18+, no extra dep; undici slightly faster but unnecessary complexity |
| Node crypto HMAC for SSE tokens | python-jose JWT format | HMAC is simpler, fewer bytes, no library on Next.js side; JWT would add consistency but overkill for 10-min tokens |

**Installation:**
No new packages needed. All dependencies already exist in both frontend and backend.

## Architecture Patterns

### Recommended Project Structure
```
frontend/src/
├── app/
│   ├── proxy.ts                           # Existing: session cookie check (Next.js 16 renamed from middleware.ts)
│   └── api/
│       ├── auth/[...all]/route.ts         # Existing: Better Auth handler
│       └── backend/
│           ├── [...path]/route.ts         # NEW: BFF catch-all proxy
│           ├── sse-token/route.ts         # NEW: SSE token issuer
│           └── health/route.ts            # NEW: Python health check proxy
├── lib/
│   ├── auth.ts                            # Existing: Better Auth server config
│   ├── auth-client.ts                     # Existing: Better Auth client
│   ├── python-proxy.ts                    # NEW: Proxy utility (fetch + headers + timeout)
│   └── sse-client.ts                      # NEW: SSE + polling fallback client

backend/
├── main.py                                # MODIFY: Replace auth_middleware (lines 280-324) with service_key_middleware
├── config.py                              # MODIFY: Add PYTHON_SERVICE_KEY, NEXTJS_ORIGIN, SSE_TOKEN_SECRET
├── services/
│   ├── auth_service.py                    # KEEP but DEPRECATE: no longer called by middleware
│   ├── service_auth.py                    # NEW: Service key validation + user context extraction
│   └── sse_token_validator.py             # NEW: Validate SSE tokens from query param
├── routers/
│   ├── auth.py                            # KEEP but DEPRECATE: /api/auth/* routes no longer needed
│   └── analyze.py                         # MODIFY: SSE endpoint adds token validation (line 49)
```

### Pattern 1: BFF Catch-All Proxy Route Handler
**What:** Single Next.js API route that forwards all /api/backend/* requests to Python
**When to use:** Every CRUD operation from browser to Python backend
**Example:**
```typescript
// Source: Confirmed by Next.js 16 official BFF docs (https://nextjs.org/docs/app/guides/backend-for-frontend)
// frontend/src/app/api/backend/[...path]/route.ts

import { auth } from "@/lib/auth";
import { headers } from "next/headers";

const PYTHON_URL = process.env.PYTHON_BACKEND_URL || "http://localhost:8000";
const SERVICE_KEY = process.env.PYTHON_SERVICE_KEY!;

// Timeout config: 5 min for analysis, 30s default
const LONG_TIMEOUT_PATHS = ["/api/analyze", "/api/analyze/project"];
const LONG_TIMEOUT = 300_000;
const DEFAULT_TIMEOUT = 30_000;

async function proxyToPython(request: Request, params: { path: string[] }) {
  // 1. Verify session (Better Auth server-side)
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session?.user) {
    return Response.json({ error: "Nicht authentifiziert" }, { status: 401 });
  }

  // 2. Build target URL (strip /api/backend, forward to PYTHON_URL/api/*)
  const path = params.path.join("/");
  const url = new URL(`/api/${path}`, PYTHON_URL);
  // Forward query params
  const incomingUrl = new URL(request.url);
  url.search = incomingUrl.search;

  // 3. Determine timeout
  const timeout = LONG_TIMEOUT_PATHS.some(p => url.pathname.startsWith(p))
    ? LONG_TIMEOUT : DEFAULT_TIMEOUT;

  // 4. Build forwarded headers (only explicit headers, not all incoming)
  const forwardHeaders = new Headers();
  forwardHeaders.set("X-Service-Key", SERVICE_KEY);
  forwardHeaders.set("X-User-Id", session.user.id);
  forwardHeaders.set("X-User-Role", session.user.role || "viewer");
  forwardHeaders.set("X-User-Email", session.user.email);
  const ct = request.headers.get("Content-Type");
  if (ct) forwardHeaders.set("Content-Type", ct);

  // 5. Proxy the request with timeout
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

// Next.js 16: params is a Promise, must await
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
export async function PATCH(req: Request, ctx: { params: Promise<{ path: string[] }> }) {
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

# Whitelist: health checks, docs, OPTIONS preflight
WHITELIST = {"/health", "/api/health", "/docs", "/redoc", "/openapi.json", "/info", "/"}

async def service_key_middleware(request: Request, call_next):
    """Validate service key on all /api/* routes (except health/whitelist)."""
    path = request.url.path
    method = request.method

    if method == "OPTIONS" or path in WHITELIST or not path.startswith("/api/"):
        return await call_next(request)

    # SSE streaming endpoints use token auth (query param), not service key
    if path.startswith("/api/analyze/stream/"):
        return await call_next(request)

    # Validate service key
    service_key = request.headers.get("X-Service-Key", "")
    if not PYTHON_SERVICE_KEY:
        logger.error("[AUTH] PYTHON_SERVICE_KEY not configured!")
        return JSONResponse(status_code=500, content={"detail": "Service auth not configured"})

    if not service_key or service_key != PYTHON_SERVICE_KEY:
        logger.warning(f"[AUTH] Rejected request to {path}: invalid service key")
        return JSONResponse(
            status_code=401,
            content={"detail": "Ungueltige Service-Authentifizierung"},
        )

    return await call_next(request)


def get_user_context(request: Request) -> dict:
    """Extract user context from forwarded headers (set by Next.js BFF proxy)."""
    return {
        "user_id": request.headers.get("X-User-Id", ""),
        "role": request.headers.get("X-User-Role", "viewer"),
        "email": request.headers.get("X-User-Email", ""),
    }


def require_role(request: Request, *allowed_roles: str) -> dict:
    """Check user role from headers. Raises 403 if not allowed."""
    ctx = get_user_context(request)
    if ctx["role"] not in allowed_roles:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Unzureichende Berechtigung")
    return ctx
```

### Pattern 3: SSE Token Flow
**What:** Short-lived HMAC token for browser-to-Python SSE connections
**When to use:** Before browser opens EventSource to Python's SSE endpoint
**Recommended:** 10-minute expiry, HMAC-SHA256 signed, base64url-encoded payload

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

  // HMAC-signed token: base64url(payload).base64url(signature)
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
    """Validate HMAC-signed SSE token. Returns payload dict or None."""
    try:
        parts = token.split(".")
        if len(parts) != 2:
            return None
        payload_b64, signature = parts

        # Verify HMAC signature
        expected_sig = hmac.new(
            SSE_TOKEN_SECRET.encode(),
            payload_b64.encode(),
            hashlib.sha256,
        ).digest()
        expected_sig_b64 = base64.urlsafe_b64encode(expected_sig).rstrip(b"=").decode()

        if not hmac.compare_digest(signature, expected_sig_b64):
            logger.warning("SSE token signature mismatch")
            return None

        # Decode payload (add base64 padding)
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
**When to use:** Dashboard status indicators, monitoring, startup checks
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
- **Proxying SSE through Next.js/Vercel:** Vercel serverless functions have timeout and streaming limitations. SSE must go direct from browser to Python.
- **Storing PYTHON_SERVICE_KEY in client-side code:** The service key is server-only; it lives in Next.js environment vars (not NEXT_PUBLIC_*). Only NEXT_PUBLIC_PYTHON_SSE_URL is public.
- **Using request.json() in proxy before forwarding:** This consumes the ReadableStream body. Use `request.arrayBuffer()` to forward the raw body intact.
- **Forwarding all incoming headers to Python:** Security risk. Only forward Content-Type and explicitly set service/user headers. The official Next.js docs warn: "Be deliberate about where headers go."
- **Putting BFF auth logic in proxy.ts:** `proxy.ts` (formerly middleware.ts) checks session cookies for page protection but cannot do full session extraction for API proxying. Use Route Handlers for that.
- **Using `request.clone()` unnecessarily:** Only clone if you need to read the body AND forward it. For pure forwarding, just use `request.arrayBuffer()` once.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Session extraction | Custom cookie parser | `auth.api.getSession({ headers: await headers() })` | Better Auth handles cookie parsing, session validation, expiry |
| Token signing | Custom crypto format | HMAC-SHA256 with `crypto.createHmac()` / `hmac.new()` | Standard, simple, no library needed on either side |
| CORS configuration | Manual header injection | FastAPI `CORSMiddleware` | Handles preflight, caching, credentials correctly |
| Request timeout | Custom Promise.race | `AbortController` + `setTimeout` | Native API, works with fetch, proper cleanup |
| User context forwarding | JWT re-signing for Python | Plain HTTP headers (X-User-*) behind service key | Service key proves trust; headers carry context without crypto overhead |

**Key insight:** The entire BFF proxy is ~80 lines of code using native fetch. No proxy libraries needed. The complexity is in getting the auth flow right, not in the HTTP plumbing.

## Common Pitfalls

### Pitfall 1: Better Auth Session Not Available in Route Handler
**What goes wrong:** `auth.api.getSession()` returns null because cookies aren't forwarded correctly
**Why it happens:** Route Handlers don't automatically have access to the request's cookies unless you pass headers explicitly
**How to avoid:** Always pass `{ headers: await headers() }` from `next/headers` to `getSession()`. The `headers()` function is async in Next.js 16.
**Warning signs:** All proxy requests return 401 even when logged in

### Pitfall 2: Next.js 16 Route Handler Params Are Promises
**What goes wrong:** `params.path` is undefined because params is a Promise
**Why it happens:** Next.js 15+ changed route handler params to be async (Promise-based)
**How to avoid:** Always `await ctx.params` before accessing `.path`. Type as `ctx: { params: Promise<{ path: string[] }> }`
**Warning signs:** TypeError: Cannot read properties of undefined

### Pitfall 3: Request Body Consumed Before Forwarding
**What goes wrong:** Python receives empty body on POST/PUT requests
**Why it happens:** Calling `request.json()` or `request.text()` consumes the ReadableStream. Official docs confirm: "You can only read the request body once."
**How to avoid:** Use `request.arrayBuffer()` for forwarding raw body
**Warning signs:** Python returns 422 validation errors on requests that work when called directly

### Pitfall 4: SSE CORS Preflight Missing
**What goes wrong:** Browser blocks EventSource connection to Python
**Why it happens:** EventSource doesn't support custom headers but CORS still applies for cross-origin requests
**How to avoid:** Python CORS must explicitly list the Next.js origin (not wildcard with credentials). EventSource doesn't send preflight for simple GET, but CORS headers must be on the response.
**Warning signs:** Browser console shows CORS errors on SSE endpoint

### Pitfall 5: Service Key Leaked to Client
**What goes wrong:** PYTHON_SERVICE_KEY appears in browser network tab or client bundle
**Why it happens:** Using NEXT_PUBLIC_ prefix or including key in client-side fetch calls
**How to avoid:** Service key is ONLY used in Route Handlers (server-side). Never prefix with NEXT_PUBLIC_. SSE uses separate token mechanism.
**Warning signs:** Service key visible in browser DevTools

### Pitfall 6: Python CORS allow_credentials with Wildcard Origins
**What goes wrong:** Browser rejects CORS response
**Why it happens:** `allow_credentials=True` with `allow_origins=["*"]` is invalid per CORS spec
**How to avoid:** SSE doesn't need credentials (token is in query param). Set `allow_credentials=False` and list explicit origins. Current main.py already has the logic at line 253 but will need updating for Next.js origin.
**Warning signs:** CORS error mentioning credentials and wildcard

### Pitfall 7: Python Service Key Not Set in Production
**What goes wrong:** All requests to Python return 500 or pass through without auth
**Why it happens:** PYTHON_SERVICE_KEY env var not set, middleware either crashes or falls through
**How to avoid:** Service key middleware should check if key is configured and return 500 with clear error if not. Never fall through silently.
**Warning signs:** Python logs show "PYTHON_SERVICE_KEY not configured"

## Code Examples

### Python main.py Middleware Replacement
```python
# In backend/main.py - Replace the existing auth_middleware (lines 280-324)
# with service_key_middleware from services/service_auth.py

from services.service_auth import service_key_middleware

# REMOVE the old auth_middleware function entirely
# REMOVE the AUTH_WHITELIST dict

# ADD this after CORSMiddleware and GZIPMiddleware:
@app.middleware("http")
async def service_auth(request: Request, call_next):
    return await service_key_middleware(request, call_next)
```

### Python CORS Configuration for SSE
```python
# In backend/main.py - Updated CORS for v2 (replaces lines 253-261)
import os
NEXTJS_ORIGIN = os.environ.get("NEXTJS_ORIGIN", "http://localhost:3000")

_cors_origins = [NEXTJS_ORIGIN]
if settings.ENVIRONMENT == Environment.DEVELOPMENT:
    _cors_origins.extend([
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
    ])
elif settings.ENVIRONMENT == Environment.PRODUCTION:
    _cors_origins.extend([
        "https://franktueren.ch",
        "https://www.franktueren.ch",
    ])

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(set(_cors_origins)),  # deduplicate
    allow_credentials=False,  # SSE tokens via query param, no cookies needed
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["X-Service-Key", "X-User-Id", "X-User-Role", "X-User-Email", "Content-Type"],
    max_age=3600,
)
```

### SSE Endpoint with Token Validation
```python
# Updated backend/routers/analyze.py - stream endpoint (line 49)
from services.sse_token_validator import validate_sse_token

@router.get("/analyze/stream/{job_id}")
async def stream_analyze_status(job_id: str, token: str = ""):
    """SSE endpoint with token-based auth for direct browser connections."""
    if not token:
        raise HTTPException(status_code=401, detail="SSE token required")
    payload = validate_sse_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired SSE token")

    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job nicht gefunden")

    # ... existing SSE event_generator() logic (lines 58-76) unchanged ...
```

### Frontend SSE Client with Polling Fallback
```typescript
// frontend/src/lib/sse-client.ts
const MAX_SSE_RETRIES = 3;
const POLL_INTERVAL_MS = 3000;

export type AnalysisEvent = {
  status?: string;
  progress?: string;
  type?: string;
  [key: string]: unknown;
};

export async function connectToAnalysis(
  jobId: string,
  onEvent: (data: AnalysisEvent) => void,
  onError?: (error: Error) => void,
): Promise<{ close: () => void }> {
  const pythonSseUrl = process.env.NEXT_PUBLIC_PYTHON_SSE_URL;
  if (!pythonSseUrl) throw new Error("NEXT_PUBLIC_PYTHON_SSE_URL not configured");

  // 1. Get SSE token from our BFF
  const tokenRes = await fetch("/api/backend/sse-token");
  if (!tokenRes.ok) throw new Error("Failed to get SSE token");
  const { token } = await tokenRes.json();

  // 2. Try SSE connection with retries
  let retries = 0;
  let currentEs: EventSource | null = null;
  let pollInterval: ReturnType<typeof setInterval> | null = null;

  function attemptSSE() {
    const es = new EventSource(
      `${pythonSseUrl}/api/analyze/stream/${jobId}?token=${token}`
    );
    currentEs = es;

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
        setTimeout(attemptSSE, 1000 * retries); // exponential-ish backoff
      } else {
        // 3. Fallback to polling through BFF (not direct to Python)
        pollInterval = setInterval(async () => {
          try {
            const res = await fetch(`/api/backend/analyze/status/${jobId}`);
            if (!res.ok) throw new Error(`Status ${res.status}`);
            const data = await res.json();
            onEvent(data);
            if (data.status === "completed" || data.status === "failed") {
              if (pollInterval) clearInterval(pollInterval);
            }
          } catch (err) {
            onError?.(err instanceof Error ? err : new Error(String(err)));
          }
        }, POLL_INTERVAL_MS);
      }
    };
  }

  attemptSSE();

  return {
    close: () => {
      currentEs?.close();
      if (pollInterval) clearInterval(pollInterval);
    },
  };
}
```

### Environment Variables
```bash
# frontend/.env.local (add these -- none are NEXT_PUBLIC_ except SSE URL)
PYTHON_BACKEND_URL=http://localhost:8000
PYTHON_SERVICE_KEY=dev-service-key-change-in-production
SSE_TOKEN_SECRET=dev-sse-secret-change-in-production
NEXT_PUBLIC_PYTHON_SSE_URL=http://localhost:8000

# backend/.env or system env vars (add these)
PYTHON_SERVICE_KEY=dev-service-key-change-in-production
SSE_TOKEN_SECRET=dev-sse-secret-change-in-production
NEXTJS_ORIGIN=http://localhost:3000
```

### Python config.py Additions
```python
# Add to Settings class in backend/config.py
# Service Auth (v2 - replaces JWT auth)
PYTHON_SERVICE_KEY: str = os.environ.get("PYTHON_SERVICE_KEY", "")
SSE_TOKEN_SECRET: str = os.environ.get("SSE_TOKEN_SECRET", os.environ.get("PYTHON_SERVICE_KEY", ""))
NEXTJS_ORIGIN: str = os.environ.get("NEXTJS_ORIGIN", "http://localhost:3000")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Next.js middleware.ts | proxy.ts (renamed) | Next.js 16.0.0 | Function exported as `proxy`, not `middleware`; runs on Node.js runtime (not edge) |
| Pages Router API routes | App Router Route Handlers | Next.js 13+ | Catch-all uses `[...path]/route.ts` not `[...path].ts` |
| Route handler params as object | Params as Promise | Next.js 15+ | Must await params: `const { path } = await ctx.params` |
| Python JWT per-user auth | Service key + user context headers | This phase | Simplification: Python trusts Next.js as auth gateway |

**Deprecated/outdated:**
- `middleware.ts`: Renamed to `proxy.ts` in Next.js 16. Codemod: `npx @next/codemod@canary middleware-to-proxy .`
- Python's `services/auth_service.py` JWT flow: Being replaced with service key auth in this phase. File should be kept but deprecated (may be needed for admin CLI tools).
- Python's `routers/auth.py` login/logout/users routes: No longer needed after service auth migration but keep for backward compatibility.
- Existing `auth_middleware` in `main.py` (lines 267-324): Replaced entirely by `service_key_middleware`.

## Open Questions

1. **Better Auth session.user.role field name**
   - What we know: Better Auth admin plugin assigns roles; permissions.ts defines viewer/analyst/manager/admin roles
   - What's unclear: Exact property path -- might be `session.user.role`, `session.user.adminRole`, or need `session.user.role` from the admin plugin
   - Recommendation: Test with `console.log(JSON.stringify(session))` in dev during implementation. The admin plugin stores role on the user object.

2. **Python's v2 routers compatibility**
   - What we know: main.py lazy-imports v2 routers (upload_v2, analyze_v2, feedback_v2) at lines 419-432
   - What's unclear: Whether v2 routers have their own auth checks that need updating
   - Recommendation: Service key middleware applies globally to all /api/* routes, so v2 routers get it automatically. No per-router changes needed.

3. **File upload body size through proxy**
   - What we know: Python allows up to 500MB files. Vercel has 4.5MB body limit on serverless functions.
   - What's unclear: Whether file uploads will go through BFF proxy in this phase
   - Recommendation: For Phase 11 scope, proxy handles it (works in local dev). Phase 12 (INFRA-04) switches to Vercel Blob with presigned URLs, bypassing the proxy for large uploads.

4. **Existing Python auth imports cleanup**
   - What we know: Several routers import `get_current_user` from auth_service.py (e.g., auth.py uses it as a FastAPI Depends)
   - What's unclear: Which routers use `get_current_user` and need to switch to `get_user_context` from service_auth.py
   - Recommendation: Search for all `from services.auth_service import` usages. The service key middleware handles auth globally, so per-route `Depends(get_current_user)` can be replaced with `get_user_context(request)` calls where role checks are needed.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework (frontend) | vitest 4.0.18 + jsdom |
| Framework (backend) | pytest (existing conftest.py at backend/tests/conftest.py) |
| Config file (frontend) | frontend/vitest.config.ts |
| Config file (backend) | backend/tests/conftest.py |
| Quick run (frontend) | `cd frontend && npx vitest run --reporter=verbose` |
| Quick run (backend) | `cd backend && python -m pytest tests/ -x -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AUTH-06 | BFF proxy reads session and forwards user context headers | unit | `cd frontend && npx vitest run src/__tests__/proxy/bff-proxy.test.ts` | No -- Wave 0 |
| AUTH-06 | Python validates service key and rejects without it | unit | `cd backend && python -m pytest tests/test_service_auth.py -x` | No -- Wave 0 |
| INFRA-02 | Python service key middleware accepts valid key, rejects invalid | unit | `cd backend && python -m pytest tests/test_service_auth.py -x` | No -- Wave 0 |
| INFRA-02 | Python extracts user context from X-User-* headers | unit | `cd backend && python -m pytest tests/test_service_auth.py::test_user_context -x` | No -- Wave 0 |
| INFRA-03 | Catch-all proxy forwards requests with correct URL mapping | unit | `cd frontend && npx vitest run src/__tests__/proxy/bff-proxy.test.ts` | No -- Wave 0 |
| INFRA-03 | SSE token issuance returns valid signed token | unit | `cd frontend && npx vitest run src/__tests__/proxy/sse-token.test.ts` | No -- Wave 0 |
| INFRA-03 | SSE token validation accepts valid, rejects expired/tampered | unit | `cd backend && python -m pytest tests/test_sse_token.py -x` | No -- Wave 0 |
| INFRA-03 | SSE client falls back to polling after 3 failed retries | unit | `cd frontend && npx vitest run src/__tests__/proxy/sse-client.test.ts` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `cd frontend && npx vitest run --reporter=verbose` and relevant backend tests
- **Per wave merge:** Full frontend + backend test suites
- **Phase gate:** All new tests green + existing tests unbroken

### Wave 0 Gaps
- [ ] `frontend/src/__tests__/proxy/bff-proxy.test.ts` -- covers AUTH-06, INFRA-03 (mock fetch, verify headers sent to Python)
- [ ] `frontend/src/__tests__/proxy/sse-token.test.ts` -- covers INFRA-03 (token generation, format verification)
- [ ] `frontend/src/__tests__/proxy/sse-client.test.ts` -- covers INFRA-03 (SSE connection + polling fallback)
- [ ] `backend/tests/test_service_auth.py` -- covers AUTH-06, INFRA-02 (middleware accepts/rejects, user context extraction)
- [ ] `backend/tests/test_sse_token.py` -- covers INFRA-03 (token validation, expiry, tamper detection)

## Sources

### Primary (HIGH confidence)
- [Next.js 16 BFF Guide](https://nextjs.org/docs/app/guides/backend-for-frontend) - Official catch-all proxy pattern with Route Handlers; includes explicit "Proxying to a backend" section with `[...slug]` pattern
- [Next.js 16 proxy.ts docs](https://nextjs.org/docs/app/api-reference/file-conventions/proxy) - Confirms proxy.ts replaces middleware.ts, runs on Node.js runtime
- [Next.js 16 Upgrade Guide](https://nextjs.org/docs/app/guides/upgrading/version-16) - Confirms middleware -> proxy rename
- Existing codebase: `backend/main.py` (auth middleware lines 267-324), `backend/routers/analyze.py` (SSE endpoint lines 49-82), `frontend/src/lib/auth.ts` (Better Auth config), `frontend/src/app/proxy.ts` (session cookie check)

### Secondary (MEDIUM confidence)
- [Next.js 16 middleware-to-proxy rename](https://nextjs.org/docs/messages/middleware-to-proxy) - Official migration guide
- FastAPI CORSMiddleware - existing usage in main.py confirms pattern

### Tertiary (LOW confidence)
- SSE token HMAC pattern: Standard cryptographic approach but custom format (not JWT). Well-understood but no canonical reference implementation.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries already installed, official Next.js 16 docs confirm BFF catch-all proxy pattern exactly as planned
- Architecture: HIGH - Direct code inspection of existing backend (main.py, analyze.py, auth_service.py, config.py); official docs verified
- Pitfalls: HIGH - Based on verified Next.js 16 changes (Promise params, proxy.ts rename) and CORS spec requirements
- SSE token format: MEDIUM - Custom HMAC approach is standard crypto but not a library-provided pattern; implementation is straightforward

**Research date:** 2026-03-11
**Valid until:** 2026-04-11 (stable patterns, unlikely to change)
