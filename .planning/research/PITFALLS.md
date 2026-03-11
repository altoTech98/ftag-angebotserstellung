# Domain Pitfalls

**Domain:** Adding Next.js SaaS platform (auth, roles, DB, file storage) to existing Python/FastAPI AI backend
**Researched:** 2026-03-10

## Critical Pitfalls

Mistakes that cause rewrites or major issues.

### Pitfall 1: Vercel Serverless Timeout Kills AI Analysis

**What goes wrong:** The existing AI analysis pipeline (multi-pass extraction + adversarial validation + gap analysis) takes 60-180 seconds per tender. Vercel serverless functions time out at 10s (Hobby) or 60s (Pro). The analysis never completes.
**Why it happens:** Teams assume Next.js API routes can proxy long-running requests to the Python backend. They cannot -- the Vercel function itself times out waiting for the Python response, even if the Python backend is still processing.
**Consequences:** Analysis appears to hang. Users get 504 errors. The core product feature is broken on deploy.
**Prevention:** Never proxy AI analysis through Vercel serverless functions. Instead: (1) Next.js sends a "start analysis" request to Python backend, which returns immediately with a job ID. (2) Python backend processes asynchronously. (3) Frontend polls or uses SSE directly to the Python backend for progress. The Next.js layer handles auth/metadata only; the Python backend handles all long-running work.
**Detection:** Test with a real 50+ position tender in staging before launch. If any Vercel function call takes >10s, the architecture is wrong.

### Pitfall 2: SSE Progress Streaming Breaks on Vercel

**What goes wrong:** The existing v1 system uses SSE (Server-Sent Events) for live progress updates during analysis. Teams try to proxy SSE through Next.js API routes on Vercel. The connection drops after the function timeout, or events arrive in batches instead of streaming.
**Why it happens:** Vercel serverless functions are request-response, not long-lived connections. Even with Fluid Compute (up to 300s), SSE connections are unreliable because Vercel's infrastructure buffers responses.
**Consequences:** Users see frozen progress bars. The "live analysis" experience -- a key v1 feature -- is degraded or broken.
**Prevention:** SSE must flow directly from the Python/FastAPI backend to the browser, bypassing Vercel entirely. Architecture: browser connects to `api.ftag.example.com` (Python) for SSE, while `app.ftag.example.com` (Next.js/Vercel) handles pages and auth. The Next.js frontend JavaScript initiates SSE connections to the Python backend URL, not to Next.js API routes. This requires CORS configuration on the Python backend to allow the Vercel domain.
**Detection:** Open browser DevTools Network tab during analysis. SSE events should arrive every 1-2 seconds. If they arrive in bursts or stop, the connection is being buffered/proxied.

### Pitfall 3: 4.5MB Upload Body Limit on Vercel

**What goes wrong:** Tender documents (PDF, XLSX, DOCX) commonly exceed 4.5MB. Vercel serverless functions reject request bodies larger than 4.5MB with a hard, non-configurable limit.
**Why it happens:** Teams route file uploads through Next.js API routes (the obvious pattern), not realizing the body size limit.
**Consequences:** Users cannot upload large tenders. The error message is cryptic (413 Payload Too Large from Vercel's edge, not your code).
**Prevention:** Two options: (A) Client-side upload directly to Vercel Blob using signed URLs (Next.js API route generates the signed URL, client uploads directly to Blob, then Next.js or Python processes the Blob URL). (B) Client uploads directly to the Python backend (bypassing Vercel entirely for uploads). Option A is cleaner if you want Vercel Blob as primary storage. Option B is simpler if Python backend already handles uploads (which it does in v1).
**Detection:** Test file upload with a 10MB PDF in staging. If it fails, the upload path goes through a Vercel function.

### Pitfall 4: NextAuth.js Middleware Authorization Bypass (CVE-2025-29927)

**What goes wrong:** A critical vulnerability disclosed in March 2025 allows attackers to completely bypass Next.js middleware authentication by manipulating the `x-middleware-subrequest` header. If your only auth check is in middleware, the entire app is unprotected.
**Why it happens:** Teams rely solely on middleware for route protection (the pattern shown in most tutorials). This is defense at one layer only.
**Consequences:** Unauthenticated users access protected pages. Admin routes exposed. Data breach.
**Prevention:** (1) Upgrade to Next.js 15.2.3+ (patched). (2) Never rely on middleware as the sole auth check. Implement defense-in-depth: middleware for redirects, server component checks for page-level auth, API route checks for data access, Python backend checks for AI operations. Every data access point must independently verify authentication. (3) Block `x-middleware-subrequest` header at your reverse proxy/CDN.
**Detection:** Automated security test: send requests to protected routes with spoofed `x-middleware-subrequest` header. If they succeed, you are vulnerable.

### Pitfall 5: Auth Token Not Reaching Python Backend

**What goes wrong:** NextAuth.js manages sessions in the Next.js layer. The Python/FastAPI backend has no knowledge of NextAuth sessions. API calls from Next.js server components to Python work (server-to-server), but direct browser calls to Python (for SSE, uploads) have no auth.
**Why it happens:** NextAuth.js uses HTTP-only cookies scoped to the Next.js domain. These cookies are not sent to the Python backend on a different domain/port.
**Consequences:** Either (A) the Python backend is completely unprotected (anyone with the URL can trigger analysis), or (B) you implement a second auth system on the Python side that drifts out of sync with NextAuth.
**Prevention:** Use JWT strategy in NextAuth.js. On login, generate a signed JWT containing user ID and role. Pass this JWT to the Python backend as a Bearer token in the Authorization header. Python backend validates the JWT using the same secret/public key. For direct browser-to-Python calls (SSE, uploads), the Next.js frontend must include the JWT in the request. Store it in a way the frontend JavaScript can access (not HTTP-only cookie -- use a short-lived token endpoint).
**Detection:** Try calling a Python backend endpoint from the browser without going through Next.js. If it works without auth, the backend is unprotected.

## Moderate Pitfalls

### Pitfall 1: Prisma Connection Pool Exhaustion in Serverless

**What goes wrong:** Every Vercel function invocation opens a new database connection. Under moderate load (10-20 concurrent users), PostgreSQL's default 100-connection limit is exhausted. New requests fail with connection errors.
**Why it happens:** Serverless functions are stateless -- each cold start creates a new Prisma Client instance with its own connection pool. Unlike a traditional server, connections are not reused across requests.
**Prevention:** Use Prisma Accelerate or an external connection pooler (PgBouncer). Vercel Postgres includes a built-in connection pooler -- use the pooled connection string (`?pgbouncer=true`) in the Prisma datasource, not the direct connection string. Set `connection_limit=1` in the Prisma datasource URL for serverless. Enable Vercel Fluid Compute to reuse function instances and their connections.
**Detection:** Monitor active PostgreSQL connections: `SELECT count(*) FROM pg_stat_activity`. Alert if >50. Test with 20 concurrent users in staging.

### Pitfall 2: Role Not Available in NextAuth Middleware

**What goes wrong:** You add a `role` field to the user model, configure the JWT callback to include it, but `req.auth?.user?.role` is undefined in middleware. Role-based route protection fails silently -- all authenticated users access all routes.
**Why it happens:** NextAuth.js v5 has a specific execution order. If callbacks are defined in `auth.ts` instead of `auth.config.ts`, the JWT is not populated before middleware runs. Also, when using a database adapter, the default session strategy is "database" not "jwt" -- and middleware cannot read database sessions.
**Prevention:** (1) Define callbacks in `auth.config.ts`, not `auth.ts`. (2) Explicitly set `session: { strategy: "jwt" }` when using a database adapter. (3) In the `jwt` callback, add `token.role = user.role`. (4) In the `session` callback, add `session.user.role = token.role`. (5) Extend the TypeScript types for Session and JWT to include `role`. Test middleware with each role to verify access control.
**Detection:** Log `req.auth` in middleware during development. If `role` is missing, the callback chain is misconfigured.

### Pitfall 3: Server Component vs Client Component Auth State Confusion

**What goes wrong:** Auth state is available in server components via `auth()` but not in client components without a `SessionProvider`. Teams mix the two patterns, resulting in pages where some parts show authenticated content and others show "not logged in".
**Why it happens:** Next.js App Router renders server and client components differently. Server components call `auth()` directly. Client components need `useSession()` from a `SessionProvider` wrapper. Forgetting the provider, or placing it incorrectly in the component tree, breaks client-side auth.
**Prevention:** Wrap the root layout in a `SessionProvider`. For server components, use `auth()` from `@/auth`. For client components, use `useSession()`. Never pass the session object as a prop deep into the tree -- use the provider pattern. Document this pattern once and enforce it.
**Detection:** If any client component shows "unauthenticated" while the page header shows the user's name, the SessionProvider is missing or misplaced.

### Pitfall 4: CORS Misconfiguration Between Next.js and Python Backend

**What goes wrong:** The browser blocks direct requests from the Next.js domain (e.g., `app.ftag.ch`) to the Python backend (e.g., `api.ftag.ch`). SSE connections fail. File uploads fail. The app appears to work in development (same localhost, different ports) but breaks in production.
**Why it happens:** In development, CORS is permissive or both services run on localhost. In production, they are on different (sub)domains. The Python backend's CORS configuration does not include the production Next.js domain, or it does not handle preflight OPTIONS requests correctly, or it does not allow credentials (cookies/headers).
**Prevention:** Configure FastAPI CORS middleware explicitly for production:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://app.ftag.ch"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)
```
Use environment variables for allowed origins (different in dev vs prod). Test CORS in a staging environment that mimics production domains. Do not use `allow_origins=["*"]` with `allow_credentials=True` -- browsers reject this combination.
**Detection:** Open browser console in production. CORS errors appear as "Access-Control-Allow-Origin" failures. Test every direct browser-to-Python flow: SSE, uploads, downloads.

### Pitfall 5: Prisma Schema Migrations on Vercel Postgres

**What goes wrong:** `prisma migrate deploy` fails on Vercel Postgres because the database user lacks `CREATE` permissions on the public schema, or because concurrent deployments run migrations simultaneously, causing conflicts.
**Why it happens:** Vercel Postgres (powered by Neon) has specific permission models. The default connection string may use a pooled connection that does not support DDL (schema changes). Migrations must use the direct (non-pooled) connection string.
**Prevention:** Use two connection strings in `schema.prisma`:
```prisma
datasource db {
  provider  = "postgresql"
  url       = env("DATABASE_URL")       // pooled, for queries
  directUrl = env("DIRECT_DATABASE_URL") // direct, for migrations
}
```
Run `prisma migrate deploy` in the Vercel build step (before the app starts). Never run migrations from a running serverless function. Test migration scripts locally against a Neon database before deploying.
**Detection:** Build logs show migration errors. Check that `DIRECT_DATABASE_URL` is set in Vercel environment variables separately from `DATABASE_URL`.

### Pitfall 6: Two Databases, Two Sources of Truth

**What goes wrong:** The Next.js layer stores users, projects, and analysis metadata in Vercel Postgres (Prisma). The Python backend stores feedback, analysis results, and matching data in JSON files or its own state. Data drifts between the two. A project deleted in Next.js still has results on the Python side. A user's role changes in Postgres but the Python backend has a cached old JWT.
**Why it happens:** Adding a new database layer on top of an existing system without migrating the old data store creates dual state. Teams plan to "migrate later" but never do.
**Prevention:** Define clear ownership: Prisma/Postgres owns users, projects, audit logs, analysis metadata (job ID, status, timestamps). Python backend owns analysis results, matching data, feedback. The Python backend should not store any user/project data -- it receives a project ID and user ID from the Next.js layer. Analysis results are stored as files (Vercel Blob or local storage) referenced by ID in Postgres. JSON feedback files should eventually migrate to Postgres too.
**Detection:** Draw a data ownership diagram. If any entity (user, project, analysis) is written by both systems, there is a consistency bug waiting to happen.

## Minor Pitfalls

### Pitfall 1: Next.js App Router Caching Surprises

**What goes wrong:** Next.js aggressively caches server component renders and `fetch` responses. A user starts an analysis, navigates away, and returns -- but sees stale data because the page was cached.
**Prevention:** Use `export const dynamic = 'force-dynamic'` on pages that show live data (analysis status, results). Use `revalidatePath()` or `revalidateTag()` after mutations. For the analysis status page, poll with client-side `fetch` rather than relying on server component re-renders.

### Pitfall 2: Environment Variable Confusion Between Next.js and Python

**What goes wrong:** Next.js requires `NEXT_PUBLIC_` prefix for client-side environment variables. Teams put the Python backend URL in `PYTHON_BACKEND_URL` (server-only) and cannot access it from client-side JavaScript to initiate SSE connections.
**Prevention:** Variables needed in the browser (Python backend URL for SSE) must be prefixed with `NEXT_PUBLIC_`. Variables that must stay secret (JWT secret, API keys) must NOT have this prefix. Document every environment variable and which runtime needs it. Create a `.env.example` with all required variables.

### Pitfall 3: Vercel Build Size Limit

**What goes wrong:** The Next.js bundle plus Prisma Client plus generated types exceeds Vercel's 250MB compressed deployment size limit.
**Prevention:** Use `prisma generate --no-engine` if using Prisma Accelerate (no need for local query engine). Exclude development dependencies. Check bundle size with `@next/bundle-analyzer`. Prisma's generated client can be large -- use `binaryTargets` to include only the Vercel runtime target.

### Pitfall 4: Audit Log Gaps

**What goes wrong:** The admin audit log captures Next.js-layer actions (login, project create) but misses Python-backend actions (analysis started, matching completed, feedback submitted). The audit trail is incomplete.
**Prevention:** Python backend must emit audit events to a shared store. Options: (A) Python writes audit entries directly to Postgres via a lightweight DB client. (B) Python sends audit events to a Next.js API endpoint. (C) Both systems write to the same audit table/collection. Option A is simplest. Define the audit event schema once and use it in both systems.

### Pitfall 5: Role Hierarchy Not Enforced Consistently

**What goes wrong:** Admin > Manager > Analyst > Viewer is defined in the Next.js middleware, but the Python backend only checks "is authenticated" vs "is not authenticated". An Analyst can trigger admin-only operations by calling the Python API directly.
**Prevention:** Pass the user role in the JWT to the Python backend. Python backend must check roles for sensitive operations (delete analysis, manage catalog, view other users' projects). Define a shared role hierarchy and enforce it in both systems. Never trust the client -- always verify the role from the JWT on the server side.

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Auth setup (NextAuth.js) | Role not in JWT/session, middleware bypass CVE | Use JWT strategy, callbacks in auth.config.ts, patch Next.js |
| Database (Prisma + Vercel Postgres) | Connection pool exhaustion, migration failures | Pooled + direct connection strings, connection_limit=1 |
| File upload | 4.5MB body limit on Vercel functions | Client-side upload to Vercel Blob or direct to Python |
| SSE progress | Vercel serverless cannot sustain SSE connections | SSE direct from Python backend, not through Next.js |
| AI analysis integration | Vercel function timeout on long-running analysis | Async job pattern: start job, poll/SSE for status |
| RBAC enforcement | Role checked in Next.js but not in Python backend | Pass role in JWT, verify in both systems |
| CORS in production | Works in dev (localhost), breaks in production | Explicit origin config, test in staging with real domains |
| Data ownership | Two systems, two truth sources for same entities | Clear ownership diagram, single writer per entity |
| Deployment | Build size limits, env var confusion | Prisma no-engine mode, NEXT_PUBLIC_ prefix discipline |
| Caching | Stale data on dynamic pages | force-dynamic on live pages, revalidation after mutations |

## Sources

- [Vercel Functions Timeout KB](https://vercel.com/kb/guide/what-can-i-do-about-vercel-serverless-functions-timing-out) -- timeout limits and Fluid Compute
- [Vercel Functions Limitations](https://vercel.com/docs/functions/limitations) -- body size limits, duration limits
- [Vercel Blob Client Upload](https://vercel.com/docs/vercel-blob/client-upload) -- bypassing 4.5MB limit
- [CVE-2025-29927 Analysis](https://projectdiscovery.io/blog/nextjs-middleware-authorization-bypass) -- middleware bypass vulnerability
- [Auth.js RBAC Guide](https://authjs.dev/guides/role-based-access-control) -- official role-based access control docs
- [NextAuth.js Middleware Discussion #9609](https://github.com/nextauthjs/next-auth/discussions/9609) -- role in middleware issues
- [Prisma Serverless Connection Pooling](https://dev.to/prisma/using-prisma-to-address-connection-pooling-issues-in-serverless-environments-3g66) -- connection pool strategies
- [Prisma Deploy to Vercel](https://www.prisma.io/docs/orm/prisma-client/deployment/serverless/deploy-to-vercel) -- directUrl for migrations
- [Vercel Connection Pooling KB](https://vercel.com/kb/guide/connection-pooling-with-functions) -- pooled vs direct connections
- [Next.js SSE Discussion #48427](https://github.com/vercel/next.js/discussions/48427) -- SSE limitations in API routes
- [Fixing SSE Streaming on Vercel (Jan 2026)](https://medium.com/@oyetoketoby80/fixing-slow-sse-server-sent-events-streaming-in-next-js-and-vercel-99f42fbdb996) -- practical SSE workarounds
- [Next.js Security Guide (Official)](https://nextjs.org/blog/security-nextjs-server-components-actions) -- defense-in-depth auth pattern
- [Next.js Auth Guide 2026 (WorkOS)](https://workos.com/blog/nextjs-app-router-authentication-guide-2026) -- comprehensive auth patterns
- [Inngest Long-Running Functions on Vercel](https://www.inngest.com/blog/vercel-long-running-background-functions) -- async job orchestration
- v1 codebase analysis -- existing SSE, upload, and FastAPI patterns
