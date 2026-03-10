# Project Research Summary

**Project:** FTAG KI-Angebotserstellung v2.0 SaaS Platform
**Domain:** B2B SaaS web platform wrapping an existing Python/FastAPI AI tender analysis pipeline
**Researched:** 2026-03-10
**Confidence:** HIGH

## Executive Summary

The v2.0 milestone transforms a working single-user local tool into a multi-user B2B SaaS platform. The core AI pipeline — multi-pass document extraction, adversarial matching against 891 FTAG products, gap analysis, and Excel generation — is complete in v1.0 and stays untouched. The new work is entirely the SaaS wrapper: a Next.js 16 frontend, authentication with four-role RBAC, persistent file storage, project management, and a professional results UI. The recommended architecture is a Backend-for-Frontend (BFF) pattern: Next.js on Vercel handles auth, UI, DB, and file storage; the existing Python/FastAPI backend deploys to Railway and owns all AI processing. The browser never calls the Python backend directly — every request passes through authenticated Next.js API routes.

The recommended stack is Next.js 16 with the App Router, Better Auth (the official successor to NextAuth.js/Auth.js after the teams merged in September 2025) with a Prisma 7 adapter, Neon Postgres (which Vercel Postgres transitioned to in Q4 2024–Q1 2025), Vercel Blob for file storage, Tailwind CSS 4 with CSS-first configuration, and shadcn/ui CLI v4 for components. The four-role system (Admin/Manager/Analyst/Viewer) maps directly to Better Auth's RBAC plugin. Total feature scope is estimated at 36–49 development days for the full platform, organized into six phases.

The central technical risk is that Vercel serverless functions cannot host long-running AI analysis (2–10 minutes), have unreliable SSE streaming, and enforce a hard 4.5 MB request body limit. Each constraint has a concrete mitigation: an async job pattern for analysis dispatch, direct Python-to-browser SSE bypassing Vercel entirely, and client-side upload to Vercel Blob via presigned URLs. Defense-in-depth authentication is non-negotiable given CVE-2025-29927 (the March 2025 Next.js middleware authorization bypass).

## Key Findings

### Recommended Stack

The stack is strongly opinionated toward the Vercel ecosystem to minimize operational overhead for a small internal team. Next.js 16 is the current stable release (October 2025), with Turbopack enabled by default, the React Compiler built in, and `proxy.ts` replacing the now-deprecated `middleware.ts`. Better Auth supersedes the NextAuth.js/Auth.js path; Auth.js receives security patches only going forward. Prisma 7 dropped its Rust engine and is now pure TypeScript with 3x faster queries and an official Better Auth adapter.

**Core technologies:**
- Next.js 16 (App Router): Full-stack framework — Vercel-native, stable App Router, React 19, React Compiler
- Better Auth: Authentication + 4-role RBAC — official successor to Auth.js, built-in Prisma adapter and RBAC plugin
- Prisma 7: ORM + migrations — pure TypeScript engine, gold-standard migration tooling, official Better Auth adapter
- Neon Postgres: Serverless PostgreSQL — Vercel Marketplace, scale-to-zero, database branching for preview deployments
- Vercel Blob: File storage — presigned client uploads for large tender documents, server uploads for small files
- Tailwind CSS 4: Utility CSS — CSS-first `@theme` configuration for FTAG Rot/Weiss design system (no tailwind.config.js)
- shadcn/ui CLI v4: UI components — copies source into codebase for full FTAG brand control, built on Radix UI
- Zustand 5: Client state only (wizard steps, UI toggles) — React Query owns all server state
- React Query 5: Server state management — all API calls, caching, optimistic updates, background refetching
- Railway.app: Python/FastAPI deployment — persistent volumes for SQLite and product catalog, no 60-second timeout

Do NOT use: NextAuth.js/Auth.js, Next.js 15, `middleware.ts`, `tailwind.config.js`, Vercel Python Functions, Redux, moment.js, or tRPC.

### Expected Features

All v1.0 AI pipeline features (extraction, matching, gap analysis, Excel generation) are already built and are out of scope for v2.0. The platform adds a professional SaaS layer on top.

**Must have (table stakes):**
- Email/password authentication with 4-role RBAC (Admin/Manager/Analyst/Viewer)
- Role-based route protection enforced at proxy.ts, server component, API route, and Python backend levels
- Dashboard with KPI status cards and recent activity feed
- Project list with search and breadcrumb navigation
- Analysis file upload with drag-and-drop (3–15 files per tender)
- Analysis progress indicator via SSE streaming from the Python backend
- Results table with sorting, filtering, and confidence color coding (green/yellow/red)
- Match detail expansion showing AI reasoning and confidence breakdown
- Excel download from the results view
- Skeleton loaders, toast notifications, and error boundaries throughout

**Should have (differentiators):**
- 5-step Analysis Wizard (Upload > Catalog Select > Config > Analysis > Results) with per-step Zod validation
- Product Catalog management — upload Excel, browse 891 products, search, edit individual products
- Product Catalog versioning with rollback; each analysis records the catalog version used
- Project sharing between users and project archiving with full history
- Gap analysis drill-down (interactive, beyond what the Excel shows)
- Admin user management (create/edit/deactivate users, assign roles)
- Admin audit log (who ran which analysis, when, with what parameters)
- System settings panel (confidence thresholds, API key config)
- FTAG Rot/Weiss design system applied consistently across all pages

**Defer to v3.0+:**
- Multi-tenancy, 2FA/MFA, dark mode, German/English i18n, PDF export, mobile-optimized layout, real-time collaboration, email notifications, custom dashboard widgets, file preview in browser

### Architecture Approach

The system uses a BFF (Backend-for-Frontend) pattern. Next.js API routes act as the auth boundary and orchestration layer between the browser and the Python AI backend. The browser never calls the Python backend directly. Files upload to Vercel Blob first (persistent, CDN-backed), then blob URLs pass to the Python backend for processing. The Python backend requires minimal changes: a shared API key replaces its current JWT auth for service-to-service calls, and the analyze endpoint gains a `blob_urls` parameter to download files from Vercel Blob. All AI pipeline services remain untouched.

Two databases serve distinct purposes with clear ownership: Prisma/Neon Postgres owns users, projects, file references (blob URLs), audit log, and analysis metadata; Python's local SQLAlchemy/SQLite owns analysis job state, feedback corrections, and the product catalog cache. No entity is written by both systems.

**Major components:**
1. Next.js App Router (Vercel) — UI rendering, routing, server components, auth, CRUD via Server Actions and Prisma
2. Next.js API Routes / BFF Layer (Vercel) — auth enforcement, request validation, async job dispatch to Python, SSE proxy or polling fallback
3. Better Auth (Vercel) — session management, JWT issuance, 4-role RBAC enforcement
4. Prisma + Neon Postgres (Vercel) — users, projects, file references, audit log, analysis metadata
5. Vercel Blob — persistent CDN-backed storage for uploaded tender documents and generated Excel results
6. Python/FastAPI (Railway) — AI pipeline execution: document parsing, Claude API matching, gap analysis, Excel generation; local SQLite for job state

### Critical Pitfalls

1. **Vercel serverless timeout kills AI analysis** — Never proxy long-running analysis through a Vercel function. Use async job pattern: Next.js sends "start" to Python (returns immediately with a job ID), Python processes asynchronously, the frontend polls or subscribes to SSE for progress. Test with a real 50+ position tender in staging before launch.

2. **SSE streaming breaks on Vercel** — Do not proxy SSE through Next.js API routes on Vercel. Have the browser connect to the Python backend (Railway) directly for SSE. This requires CORS on the Python side and `NEXT_PUBLIC_PYTHON_API_URL` in the Next.js environment. Implement a polling fallback if direct SSE proves unreliable.

3. **4.5 MB upload body limit on Vercel functions** — Route all file uploads through Vercel Blob client-side upload: Next.js API route generates a presigned URL, the browser uploads directly to Blob, then the blob URL is passed to Python. Test with a 10 MB PDF in staging.

4. **Middleware authorization bypass (CVE-2025-29927)** — Never rely on `proxy.ts` as the sole auth check. Implement defense-in-depth: proxy.ts for redirects, server component session checks for page-level auth, API route validation for data access, and Python backend API key plus role verification for AI operations.

5. **Auth token not reaching Python backend** — Use JWT strategy in Better Auth. Pass the signed JWT to Python as a Bearer token. For direct browser-to-Python calls (SSE), the frontend must include the token. Python validates using the shared AUTH_SECRET. Pass user role in the JWT so Python can enforce role checks independently of the Next.js layer.

## Implications for Roadmap

Based on combined research, the recommended structure has six phases with a clear dependency chain. Auth is a hard prerequisite for everything. The BFF layer must be validated before any analysis UI is built on top of it. The analysis wizard cannot exist without working projects and file uploads. The dashboard is a pure consumer of other data and comes last.

### Phase 1: Foundation (Auth + Database + Design System)

**Rationale:** Authentication is a hard prerequisite for every other feature — routing, data access, and the admin panel all depend on knowing who the user is. Establishing the Prisma schema up front prevents costly migration headaches. This phase has no dependencies and the highest documentation quality of any phase in the project.
**Delivers:** Working Next.js 16 app with login/logout, 4-role RBAC via Better Auth, Prisma schema and Neon Postgres connection, FTAG Rot/Weiss design system tokens via Tailwind CSS 4 `@theme`, base layout shell with sidebar and breadcrumbs.
**Addresses:** Authentication, role-based route protection, responsive desktop-first layout, loading states (FEATURES.md table stakes).
**Avoids:** Role not in JWT/session (use Better Auth JWT strategy with callbacks in auth.config.ts); middleware-only auth (defense-in-depth from day one); Prisma migration failures (configure pooled + direct connection strings before first deploy to Vercel).

### Phase 2: Python Backend Integration (BFF + Service Auth)

**Rationale:** All user-facing features from Phase 3 onward require a working Next.js-to-Python connection. Establishing the BFF proxy layer and shared API key auth early means integration failures surface before any UI is built around them. SSE reliability is the highest-uncertainty question in the project — it must be answered here, not discovered during the analysis wizard build.
**Delivers:** API key middleware on Python backend, Next.js API route proxy for every Python endpoint, SSE proxy validation or confirmed polling fallback, health check endpoint, service-to-service connectivity verified in staging with real domains.
**Uses:** `PYTHON_API_KEY` shared secret, `NEXT_PUBLIC_PYTHON_API_URL` for client-side SSE, async job dispatch pattern (STACK.md patterns).
**Implements:** BFF pattern, shared auth boundary, async job ID flow (ARCHITECTURE.md patterns).
**Avoids:** Proxying long-running calls through Vercel functions; SSE buffering on Vercel (validate here, not later); CORS misconfiguration (configure Python CORS for production domains in this phase).

### Phase 3: File Handling + Project Management

**Rationale:** Projects are the container for everything else. The analysis wizard (Phase 4) needs projects to exist before it can create analyses. File upload must be built before the wizard to validate the Vercel Blob client-side upload pattern against real tender documents before the wizard depends on it working.
**Delivers:** Vercel Blob integration with client-side upload for files over 4.5 MB, project CRUD (create/list/search/archive), project detail page, project sharing between users, Python backend modified to accept `blob_urls` parameter.
**Addresses:** Project list with search, drag-and-drop file upload, project archiving, project sharing (FEATURES.md).
**Avoids:** 4.5 MB body limit — client-side Vercel Blob upload must be validated with real PDF/XLSX files here; file storage in Python filesystem — all files go to Vercel Blob, Python downloads from blob URLs.

### Phase 4: Analysis Wizard + Results View

**Rationale:** This is the core product workflow and delivers the primary user value. It depends on all three prior phases. The 5-step wizard with SSE progress and the results table with confidence color coding are the daily-use path for the sales team.
**Delivers:** 5-step Analysis Wizard with per-step Zod validation (Upload > Catalog Select > Config > Analysis Start > Results), SSE progress display (or polling fallback confirmed in Phase 2), results table with sort/filter/confidence color coding, match detail expansion with AI reasoning, gap analysis drill-down, Excel download.
**Uses:** Zustand wizard state store, React Query mutations for API calls, shadcn/ui Table and Dialog components, recharts for confidence distribution (STACK.md).
**Addresses:** Analysis wizard, wizard validation, SSE progress, results table, match detail, gap drill-down, Excel download, confidence color coding (FEATURES.md).
**Avoids:** Stale analysis status data (use `force-dynamic` on results pages; poll with React Query); `NEXT_PUBLIC_` prefix discipline for environment variables the browser needs; dual sources of truth for analysis status (Prisma owns status metadata, Python owns result data — Next.js polls Python for completion and writes the outcome back to Prisma).

### Phase 5: Product Catalog Management

**Rationale:** Catalog management is a lower-frequency workflow used by Managers and Admins. It depends on auth and the database schema but not on the analysis wizard. Building it after the wizard means catalog versioning can be shaped by what the wizard actually needs from a catalog record (catalog ID, version, blob URL).
**Delivers:** Catalog upload from Excel, product browse/search across 891 products, product edit, catalog versioning with rollback, version displayed on each analysis result.
**Addresses:** Catalog CRUD, catalog versioning, catalog search (FEATURES.md differentiators).
**Avoids:** Dual sources of truth for catalog — Prisma owns version metadata and blob URL; Python owns the in-memory catalog and TF-IDF index. Define a clear reload trigger (a Next.js API call to a Python `/admin/reload-catalog` endpoint) so catalog version changes are reflected without a Railway restart.

### Phase 6: Admin Panel + Dashboard + Polish

**Rationale:** The dashboard is a consumer of all other data models and cannot show meaningful KPIs until analyses, projects, and users exist. The admin panel is standard CRUD and is low risk. Polish (keyboard shortcuts, activity feed, system settings) is additive and does not block shipping the product.
**Delivers:** Dashboard with KPI status cards and activity feed, admin user management (create/edit/deactivate, role assignment), admin audit log viewer, system settings panel, keyboard shortcuts for power users.
**Addresses:** Dashboard, status cards, activity feed, admin user management, audit log, system settings (FEATURES.md).
**Avoids:** Audit log gaps — Python backend must emit audit events to Postgres; define this contract in Phase 2 even though the UI arrives in Phase 6. Role hierarchy not enforced in Python — verify Python checks roles from the JWT in Phase 2; Phase 6 only adds the management UI.

### Phase Ordering Rationale

- Auth before everything: Better Auth + Prisma schema is a hard dependency for all data access and role-protected routing. No feature can be built without identity.
- BFF before UI: Validating the Next.js-to-Python connection (including SSE reliability and the async job pattern) in isolation prevents discovering integration failures inside complex UI work. Phase 2 is a proof-of-concept phase.
- Projects before wizard: The analysis wizard creates analyses that belong to projects; the data model dependency is direct.
- File upload before wizard: The 4.5 MB Vercel body limit pitfall must be resolved with real tenant files before the wizard depends on working uploads. Discovering this in Phase 4 would cause a mid-wizard refactor.
- Wizard before catalog management: The wizard is the daily-use path; catalog management is a low-frequency admin task. Build high-value paths first.
- Dashboard last: It is a pure consumer of other data models. No other feature depends on it.

### Research Flags

Phases needing deeper research or a spike task during planning:

- **Phase 2 (BFF + SSE):** SSE proxying through Vercel has known reliability issues documented in multiple community sources (2026 articles). The decision between SSE proxy, direct browser-to-Python SSE, or polling fallback needs a working proof-of-concept — not just a plan. Recommend a spike task as the first item in Phase 2 before any other work.
- **Phase 4 (Analysis Wizard state shape):** Zustand wizard state across 5 steps with React Query mutations and SSE subscription is a non-trivial design problem. Underspecifying this leads to mid-phase refactors. Recommend a state design document at Phase 4 start before any component code is written.
- **Phase 5 (Catalog reload trigger):** The interaction between Prisma catalog version records and the Python in-memory catalog reload is unspecified. The API contract for triggering a Python reload must be defined before Phase 5 implementation begins.

Phases with well-documented standard patterns (skip research-phase):

- **Phase 1 (Auth + DB):** Better Auth + Prisma + Neon is an officially documented, fully supported path with high-confidence sources. No technology bets.
- **Phase 3 (Projects + File Upload):** Vercel Blob client upload is thoroughly documented in official Vercel docs; project CRUD with Prisma is standard. Low risk.
- **Phase 6 (Admin + Dashboard):** User management CRUD and dashboard KPI cards are standard B2B SaaS patterns. recharts + Server Components is well-understood.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All technology choices backed by official release notes and docs. Version pinning is specific with explicit rationale. One caveat: Next.js 16 is recent (stable Oct 2025); minor ecosystem library compatibility gaps may exist. |
| Features | HIGH | Feature list derived from direct v1.0 codebase analysis plus PROJECT.md requirements. Table stakes and anti-features clearly scoped. Role permission matrix is complete and internally consistent. |
| Architecture | HIGH | BFF pattern is well-established. All key constraints (Vercel timeouts, body limits, two-database split, file flow) are backed by official documentation and real Vercel platform limits. |
| Pitfalls | HIGH | Every critical pitfall is sourced from official docs, CVE advisories, or verified community findings with detection criteria. The SSE reliability question (Pitfall 2) carries the most uncertainty and is the only item requiring empirical validation. |

**Overall confidence:** HIGH

### Gaps to Address

- **SSE reliability on Vercel:** Research is clear that Vercel serverless does not reliably sustain SSE. The exact solution (direct browser-to-Python SSE vs. polling fallback) needs a working proof-of-concept in Phase 2. Document the chosen pattern in the Phase 2 plan before any Phase 4 work begins.
- **Python audit event emission:** How the Python backend emits audit events to the Postgres audit log (direct DB write vs. Next.js API callback) is unresolved. Define the contract during Phase 2 BFF design even though the audit log UI is Phase 6 work.
- **Catalog reload trigger mechanism:** When a new catalog version is uploaded via the Next.js platform, Python's in-memory TF-IDF index and product catalog must reload. The reload mechanism (a Python admin endpoint, scheduled polling, or Railway restart) is unspecified. Address in Phase 5 planning.
- **Railway persistent volume configuration:** The Python backend uses SQLite (analysis job state) and JSON files (feedback corrections). Confirm Railway persistent volume configuration before Phase 2 deployment to avoid data loss on container restarts.

## Sources

### Primary (HIGH confidence)
- Next.js 16 Release Blog and Upgrade Guide — stable features, proxy.ts migration, React Compiler
- Better Auth documentation and Auth.js merger announcement (September 2025) — official successor status, RBAC plugin
- Prisma 7 Release Blog — pure TypeScript engine, Neon adapter, Better Auth adapter
- Neon Postgres Vercel transition guide — Vercel Postgres transitioned to Neon Q4 2024–Q1 2025
- Vercel Blob documentation — client upload pattern, 4.5 MB API route limit, presigned URLs
- Tailwind CSS v4.0 blog — CSS-first config, Oxide engine, `@theme` syntax
- CVE-2025-29927 analysis (ProjectDiscovery) — middleware authorization bypass, detection, remediation
- Vercel Functions Limitations documentation — timeout limits, body size limits, Fluid Compute
- fastapi-nextauth-jwt PyPI — purpose-built JWT validation for FastAPI + NextAuth integration
- Prisma deploy to Vercel documentation — directUrl for migrations, serverless connection pooling
- Railway FastAPI deployment guide — persistent volumes, Nixpacks, gunicorn + uvicorn workers
- Existing v1.0 codebase (direct analysis) — all service implementations, current patterns, known issues
- PROJECT.md requirements specification (direct analysis) — scope boundaries, deferred features

### Secondary (MEDIUM confidence)
- SSE streaming on Vercel fix article (January 2026) — `X-Accel-Buffering: no` header, buffering workarounds
- Drizzle vs. Prisma comparison (makerkit.dev) — ORM decision rationale, migration friction trade-offs
- Better Auth vs. NextAuth comparison (betterstack.com) — auth library decision rationale
- Next.js + FastAPI GitHub discussions (#43724) — community integration patterns
- Prisma serverless connection pooling (dev.to) — PgBouncer, connection_limit=1 strategy
- Auth.js RBAC guide — role callback configuration, JWT strategy requirements

### Tertiary (LOW confidence)
- shadcn/ui CLI v4 changelog (March 2026) — very recent release, limited community validation time; verify component API before use

---
*Research completed: 2026-03-10*
*Ready for roadmap: yes*
