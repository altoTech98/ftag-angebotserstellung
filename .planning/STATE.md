---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: AI Tender Matcher -- Web-Oberflaeche & Platform
status: in-progress
stopped_at: Completed 12-01 (Data Foundation)
last_updated: "2026-03-11T09:25:00Z"
last_activity: 2026-03-11 -- Completed Plan 12-01 (Data Foundation)
progress:
  total_phases: 6
  completed_phases: 2
  total_plans: 10
  completed_plans: 10
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-10)

**Core value:** 100% korrekte Zuordnung jeder Anforderung zum richtigen Produkt -- oder eine explizite, begruendete Gap-Meldung.
**Current focus:** Phase 12 - File Handling & Project Management

## Current Position

Phase: 12 of 15 (File Handling & Project Management)
Plan: 1 of 3 (in progress)
Status: Executing Phase 12
Last activity: 2026-03-11 -- Completed Plan 12-01 (Data Foundation)

Progress: [##########] 100%

## Performance Metrics

**Velocity:**
- Total plans completed: 10 (v2.0)
- Average duration: 4.2min
- Total execution time: 42min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 10-foundation | 6/6 | 27min | 4.5min |
| 11-python-backend | 3/3 | 11min | 3.7min |
| 12-file-handling | 1/? | 4min | 4.0min |

## Accumulated Context

### Decisions

- Better Auth (not NextAuth/Auth.js) for authentication -- official successor, built-in RBAC plugin
- Prisma 7 + Neon Postgres (not Vercel Postgres) -- pure TS engine, Better Auth adapter
- Python/FastAPI deploys to Railway (not Vercel Functions) -- no timeout limits
- BFF pattern: Next.js proxies to Python (browser never calls Python directly for CRUD)
- SSE connects browser directly to Python for progress events (Vercel cannot reliably proxy SSE)
- Vercel Blob for file uploads with presigned URLs (bypasses 4.5 MB body limit)
- Tailwind CSS 4 with CSS-first @theme config (no tailwind.config.js)
- shadcn/ui CLI v4 for FTAG-branded components
- [Phase 10-foundation]: Initialized frontend/package.json for v2.0 test infrastructure (frontend/ directory had no package.json)
- [Phase 10-01]: Kept globals.css in src/app/ (shadcn default) instead of src/styles/ to match components.json config
- [Phase 10-01]: Skipped prisma.config.ts -- Prisma 7.4.2 failed to parse it on Windows; generate works without it
- [Phase 10-01]: Import Prisma from @/generated/prisma/client (Prisma 7 pattern, not @prisma/client)
- [Phase 10-foundation]: Used Better Auth emailOTP client methods for password reset flow
- [Phase 10-foundation]: Session warning modal is non-dismissable -- user must explicitly extend or logout
- [Phase 10-03]: Created AppShell client wrapper to bridge server layout with client-side SidebarProvider context
- [Phase 10-03]: Better Auth userHasPermission returns { success } directly, not { data: { success } }
- [Phase 10-03]: shadcn v4 dropdown-menu uses base-ui without asChild prop
- [Phase 10-04]: AppShellClient is a dedicated client component wrapping session timeout logic separately from AppShell
- [Phase 10-04]: Root page uses server-side session check for redirect (no client-side flash)
- [Phase 11-01]: Used os.environ.get() in service_auth.py/sse_token_validator.py for self-contained testability
- [Phase 11-01]: SSE stream paths skip service key check, use dedicated HMAC token auth via query param
- [Phase 11-01]: CORS allows explicit headers (X-Service-Key, X-User-*), credentials=False (tokens via query param)
- [Phase 11-02]: BFF proxy reads PYTHON_SERVICE_KEY from server-side env only (no NEXT_PUBLIC_ prefix)
- [Phase 11-02]: SSE token format: base64url(payload).hex(HMAC-SHA256 signature) matching Python validator (corrected in 11-03)
- [Phase 11-03]: Token format contract: base64url(payload).hex(HMAC-SHA256) -- hex chosen over base64url for signature to match Python hexdigest()
- [Phase 11-02]: Analysis endpoints get 300s timeout; all others get 30s default
- [Phase 11-02]: SSE client retries 3x with linear backoff then falls back to polling every 3s
- [Phase 12-01]: Created migration SQL manually (prisma migrate dev hangs on remote Neon DB in dev env)
- [Phase 12-01]: Server Actions pattern: auth.api.getSession -> userHasPermission -> prisma query -> revalidatePath

### Pending Todos

None.

### Blockers/Concerns

- SSE reliability on Vercel needs empirical validation in Phase 11 (spike task)
- Python audit event emission contract (direct DB write vs. API callback) -- define in Phase 11
- Catalog reload trigger mechanism -- define in Phase 14 planning

## Session Continuity

Last session: 2026-03-11T09:20:42Z
Stopped at: Completed 12-01 (Data Foundation)
Resume file: None
