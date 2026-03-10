# Stack Research

**Domain:** SaaS Web Application (B2B AI Tender Matcher Platform)
**Researched:** 2026-03-10
**Confidence:** HIGH

## Context

This stack covers ONLY the new SaaS platform layer (v2.0 milestone). The existing Python/FastAPI AI pipeline (v1.0) remains unchanged and will be consumed as a backend service via HTTP from Next.js. The existing React/Vite frontend (`frontend-react/`) will be superseded entirely by the Next.js application.

**Existing stack (DO NOT change):** Python 3.12+, FastAPI, Claude API (anthropic SDK), openpyxl, pdfplumber, PyMuPDF, python-docx, scikit-learn TF-IDF, Pydantic.

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Next.js | 16.x (stable, Oct 2025) | Full-stack React framework | Current stable release. Turbopack stable by default, React Compiler built-in, App Router mature. proxy.ts replaces middleware.ts. Zero-config Vercel deployment. Do NOT use 15 -- deprecation warnings active since 15.5. |
| React | 19.x | UI library | Ships with Next.js 16. Already used in frontend-react (^19.2.0). React Compiler eliminates manual useMemo/useCallback. Server Components reduce client bundle. |
| TypeScript | 5.x | Type safety | Non-negotiable for multi-role SaaS. Prisma generates types, Better Auth provides type-safe APIs, Next.js has first-class TS support. Catches role/permission errors at compile time. |
| Tailwind CSS | 4.x (stable, Jan 2025) | Utility-first CSS | Ground-up rewrite: 5x faster builds, CSS-first config (no tailwind.config.js), automatic content detection. Configure FTAG Rot/Weiss design system via `@theme` in CSS. |
| Better Auth | latest | Authentication + RBAC | Auth.js (formerly NextAuth) team joined Better Auth in Sept 2025. Better Auth is the recommended path for ALL new projects. Built-in RBAC plugin, rate limiting, password policies, session management. Official Prisma adapter. Supports the 4-role system (Admin/Manager/Analyst/Viewer) out of the box via roles plugin. |
| Prisma ORM | 7.x (stable) | Database ORM + migrations | v7 dropped Rust engine -- pure TypeScript, 3x faster queries. Gold-standard migrations (`prisma migrate dev` auto-diffs). Better Auth has official Prisma adapter with CLI schema generation. Chosen over Drizzle for migration tooling maturity and Better Auth ecosystem fit. |
| Neon Postgres | managed service | Serverless PostgreSQL | Vercel Postgres IS Neon (transitioned Q4 2024-Q1 2025). No separate "Vercel Postgres" product exists anymore. Use Neon via Vercel Marketplace. Scale-to-zero, database branching for preview deployments, 80% storage cost reduction (late 2025). |
| Vercel Blob | managed service | File storage | Native Vercel integration. Server uploads via Server Actions (<4.5MB), client uploads via presigned URLs for larger files. 500MB per-file limit -- sufficient for tender PDFs/DOCX/XLSX. |
| Zustand | 5.x (5.0.11) | Client-side state | 2.7KB gzipped, hooks-based, zero boilerplate. Use ONLY for client state: wizard step tracking, UI state (filters, modals, sidebar). Server state belongs in React Query. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| @tanstack/react-query | 5.x | Server state management | ALL API calls to FastAPI backend and Next.js API routes. Caching, background refetching, optimistic updates. Zustand = client state, React Query = server state. |
| shadcn/ui | CLI v4 (Mar 2026) | UI component library | Pre-built accessible components (Dialog, Table, Tabs, Cards, Forms). Not an npm dep -- copies source into your codebase. Full control for FTAG Rot/Weiss customization. Built on Radix UI primitives. |
| @better-auth/prisma-adapter | latest | Better Auth DB adapter | Stores auth sessions, users, accounts in Neon Postgres via Prisma. CLI auto-generates required schema fields. |
| @prisma/adapter-neon | latest | Neon serverless driver | Optimized database connections from Vercel Functions. Eliminates connection pool issues in serverless. |
| @neondatabase/serverless | latest | Neon HTTP driver | Used by @prisma/adapter-neon under the hood. Low-latency serverless queries. |
| zod | 3.x | Schema validation | Form validation, API request/response schemas, env var validation. Used by Better Auth internally. |
| @vercel/blob | latest | Blob storage SDK | File uploads. Server Actions for small files, client tokens for large tender documents. |
| @t3-oss/env-nextjs | latest | Env var validation | Type-safe environment variables with zod. Prevents runtime crashes from missing DATABASE_URL, FASTAPI_URL, BLOB_READ_WRITE_TOKEN. |
| lucide-react | latest | Icons | Consistent icon set, used by shadcn/ui. Tree-shakable. |
| recharts | 2.x | Dashboard charts | Analysis counts, match confidence distribution, activity trends. Lightweight, React-native. |
| sonner | latest | Toast notifications | Best toast library for Next.js App Router. Used by shadcn/ui's toast component. |
| date-fns | 4.x | Date formatting | Audit logs, project timestamps, activity feeds. Tree-shakable, unlike moment.js. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| Turbopack | Dev server + builds | Ships with Next.js 16, enabled by default. No configuration needed. |
| Prisma Studio | Database GUI | `npx prisma studio` -- inspect/edit data during development. Free, built into Prisma CLI. |
| ESLint 9 + eslint-config-next | Linting | Next.js 16 includes built-in config. Use flat config format (eslint.config.mjs). |
| Prettier + prettier-plugin-tailwindcss | Formatting | Auto-sorts Tailwind classes. Essential for team consistency. |
| shadcn CLI v4 | Component scaffolding | `npx shadcn create` for visual project setup. `npx shadcn add [component]` to add components. |

## Installation

```bash
# Create Next.js 16 project with TypeScript + Tailwind CSS 4 + App Router
npx create-next-app@latest ftag-platform --typescript --tailwind --app --turbopack

# Authentication
npm install better-auth @better-auth/prisma-adapter

# Database
npm install prisma @prisma/client @prisma/adapter-neon @neondatabase/serverless

# UI + State
npm install zustand @tanstack/react-query zod sonner recharts date-fns lucide-react

# Vercel services
npm install @vercel/blob

# Dev dependencies
npm install -D @t3-oss/env-nextjs prettier prettier-plugin-tailwindcss

# shadcn/ui (copies components into your codebase, not an npm dependency)
npx shadcn@latest init
npx shadcn@latest add button card dialog table tabs input form select badge dropdown-menu avatar separator sheet command

# Initialize Prisma with PostgreSQL
npx prisma init --datasource-provider postgresql
```

## Architecture: Next.js <> Python/FastAPI Integration

**The critical decision:** Next.js owns auth, UI, CRUD, projects, users. Python/FastAPI owns AI analysis. The browser NEVER calls FastAPI directly.

```
Browser (React 19 + Zustand + React Query)
  |
  v
Next.js 16 on Vercel
  |-- App Router (pages, layouts, RSC)
  |-- Server Actions (CRUD: projects, catalogs, users)
  |-- API Routes (/api/analyze, /api/upload)
  |     |-- Validates auth (Better Auth session)
  |     |-- Stores metadata in Neon Postgres (Prisma)
  |     |-- Uploads files to Vercel Blob
  |     |-- Proxies AI requests to FastAPI
  |     |-- Streams SSE progress back to browser
  |-- Better Auth (sessions, RBAC, audit)
  |-- Prisma ORM (Neon Postgres)
  |-- Vercel Blob (file storage)
  |
  v (internal HTTP, never exposed to browser)
Python/FastAPI on Railway
  |-- AI Pipeline (unchanged v1.0)
  |-- Claude API (extraction, matching, validation)
  |-- Excel generation (openpyxl)
  |-- Returns results as JSON + file bytes
```

**FastAPI deployment:** Use Railway ($5/mo hobby, $20/mo pro). Set `FASTAPI_URL=https://ftag-api.up.railway.app` as Vercel env var. Do NOT use Vercel Python Functions -- they have 60s timeout, insufficient for multi-pass AI analysis that can take 2-5 minutes.

**File flow:**
1. User uploads tender doc in browser
2. Next.js Server Action stores in Vercel Blob, gets blob URL
3. Next.js API route sends blob URL to FastAPI
4. FastAPI downloads from Blob, runs AI pipeline, generates Excel
5. FastAPI returns result JSON + Excel bytes
6. Next.js stores Excel in Vercel Blob, saves metadata in Postgres

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Better Auth | NextAuth/Auth.js v5 | Never for new projects. Auth.js team joined Better Auth (Sept 2025). Auth.js gets security patches only. |
| Better Auth | Clerk | If you want fully managed auth with zero backend. Costs $25/mo+ at scale. Overkill for internal FTAG tool with <20 users. |
| Prisma 7 | Drizzle ORM | If cold start time is critical (Drizzle: 7.4KB vs Prisma: larger bundle). But Prisma's migration tooling and Better Auth adapter maturity win here. Migration friction not worth the bundle savings for this app. |
| Neon Postgres | Supabase | If you want auth + realtime + storage all-in-one. But we have Better Auth + Vercel Blob already -- Supabase would be redundant vendor complexity. |
| Zustand | Redux Toolkit | Never for this project. Redux adds boilerplate for wizard state and UI toggles. Zustand handles it in 10x less code. |
| Zustand | Jotai | If you prefer atomic (bottom-up) state. Zustand's store pattern (top-down) maps better to the wizard's sequential state shape. |
| Next.js 16 | Remix / React Router 7 | If you need to deploy outside Vercel. But FTAG is Vercel-first, so Next.js is the natural fit. |
| shadcn/ui | Ant Design / MUI | If you want an opinionated design system out of the box. But shadcn/ui gives full source control -- better for FTAG's custom Rot/Weiss branding. |
| Railway (FastAPI) | Render / Fly.io | If Railway pricing doesn't work. Render has free tier but cold starts. Fly.io needs Docker knowledge. Railway is simplest for "deploy FastAPI and get a URL." |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| NextAuth.js / Auth.js | Team merged into Better Auth (Sept 2025). Perpetual beta for 2+ years. Security patches only going forward. | Better Auth |
| Next.js 15 | Deprecation warnings active since 15.5. middleware.ts deprecated. Missing React Compiler stable, Turbopack builds. | Next.js 16 |
| middleware.ts | Deprecated in Next.js 16. Renamed to proxy.ts, runs on Node.js (not Edge). | proxy.ts |
| tailwind.config.js | Tailwind CSS 4 uses CSS-first configuration. JS config is legacy. | `@theme` block in global CSS |
| Vercel Postgres (direct) | No longer a separate product. All transitioned to Neon Q4 2024-Q1 2025. | Neon via Vercel Marketplace |
| Express.js | Next.js API routes + Server Actions handle everything. Express adds deployment complexity on Vercel. | Next.js API Routes |
| Axios | fetch is native in Next.js with caching semantics. Axios is unnecessary bundle weight. | Native fetch / React Query |
| Redux / MobX | Massive overkill. Wizard state + UI toggles are simple. | Zustand (client) + React Query (server) |
| moment.js | 300KB+, deprecated by maintainers. | date-fns (tree-shakable) |
| Vercel Python Functions | 60-second timeout. AI analysis takes 2-5 minutes. Not suitable. | Railway / Render for FastAPI |
| tRPC | Adds type-safety layer between Next.js frontend and backend, but our "backend" is Python/FastAPI -- tRPC can't bridge that. Server Actions + React Query are sufficient for Next.js-internal calls. | Server Actions + React Query |

## Stack Patterns by Use Case

**5-Step Analysis Wizard (Upload > Catalog > Config > Start > Result):**
- Zustand store for wizard state (current step, selections, uploaded files)
- React Query mutations for API calls (upload to Blob, trigger analysis)
- Server Actions for persisting wizard completion to Postgres
- SSE streaming: FastAPI emits SSE, Next.js API route proxies to browser via ReadableStream

**Dashboard (Stats, Activity, Recent Analyses):**
- React Server Components for initial data (zero client JS for static cards)
- React Query for client-refreshing data (activity feed)
- recharts for visualizations (analysis counts, confidence distributions)

**Admin Panel (Users, Audit Log, Settings):**
- Server Actions for all CRUD (no client-side fetching needed)
- Better Auth admin plugin for user management + role assignment
- Prisma transactions for atomic audit log entries

**File Handling (Tender Docs, Catalogs, Generated Excel):**
- Small files (<4.5MB): Server Action with `put()` from `@vercel/blob`
- Large files: Client upload with `@vercel/blob` client token + `handleUpload()`
- Store blob URLs in Postgres, never store files in DB

**Role-Based Access (Admin/Manager/Analyst/Viewer):**
- Better Auth RBAC plugin defines roles and permissions
- proxy.ts checks session + role on protected routes
- Server Actions verify permissions before mutations
- UI conditionally renders based on `session.user.role`

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| Next.js 16.x | React 19.x | Ships together. React Compiler stable. |
| Next.js 16.x | Tailwind CSS 4.x | Full support. CSS-first config via `@import "tailwindcss"`. |
| Prisma 7.x | Neon Postgres | Use `@prisma/adapter-neon`. Pure TS engine, no Rust binary. |
| Prisma 7.x | Node.js 18.18+ | Prisma 7 dropped Node 16 support. Vercel uses Node 20 by default. |
| Better Auth | Prisma 7.x | Via `@better-auth/prisma-adapter`. Run `npx better-auth generate` for schema. |
| shadcn/ui CLI v4 | Next.js 16 + Tailwind 4 | Full support. Visual project setup via `npx shadcn create`. |
| Zustand 5.x | React 19.x | Full compatibility via `useSyncExternalStore`. |
| React Query 5.x | React 19.x + Next.js 16 | RSC support via `HydrationBoundary` for server-side prefetching. |

## Critical Migration Notes

### proxy.ts (formerly middleware.ts)
Next.js 16 renamed `middleware.ts` to `proxy.ts`. The runtime changed from Edge to Node.js. All tutorials/guides referencing `middleware.ts` are outdated.
```typescript
// proxy.ts (NOT middleware.ts)
import { NextRequest, NextResponse } from 'next/server'

export function proxy(request: NextRequest) {
  // Better Auth session check, role validation, redirects
  return NextResponse.next()
}
```

### Tailwind CSS 4 Configuration
No `tailwind.config.js`. Configure via CSS:
```css
@import "tailwindcss";

@theme {
  --color-ftag-red: #cc0000;
  --color-ftag-red-dark: #990000;
  --color-ftag-white: #ffffff;
  --color-ftag-gray-50: #f9fafb;
  --radius-lg: 0.5rem;
  --font-sans: 'Inter', system-ui, sans-serif;
}
```

### From existing frontend-react (Vite + React 19)
- `frontend-react/` uses Vite + React 19 + react-router-dom -- Next.js 16 replaces ALL of this
- Component logic (JSX, hooks) can be migrated; routing and data-fetching patterns change entirely
- Do NOT embed Vite inside Next.js -- clean break to App Router
- The new Next.js app should live in a new directory (e.g., `web/` or `platform/`)

## Sources

- [Next.js 16 Release Blog](https://nextjs.org/blog/next-16) -- stable features, proxy.ts (HIGH confidence)
- [Next.js 16 Upgrade Guide](https://nextjs.org/docs/app/guides/upgrading/version-16) -- middleware to proxy migration (HIGH confidence)
- [Next.js 16.1 Release](https://nextjs.org/blog/next-16-1) -- latest stable patch (HIGH confidence)
- [Better Auth + Prisma Official Guide](https://www.prisma.io/docs/guides/authentication/better-auth/nextjs) -- Prisma docs (HIGH confidence)
- [Better Auth Prisma Adapter](https://better-auth.com/docs/adapters/prisma) -- adapter docs (HIGH confidence)
- [Auth.js joins Better Auth](https://better-auth.com/blog/authjs-joins-better-auth) -- merger announcement (HIGH confidence)
- [Prisma 7 Release](https://www.prisma.io/blog/announcing-prisma-orm-7-0-0) -- Rust-free, performance (HIGH confidence)
- [Prisma 7.2.0 Release](https://www.prisma.io/blog/announcing-prisma-orm-7-2-0) -- latest patch (HIGH confidence)
- [Tailwind CSS v4.0](https://tailwindcss.com/blog/tailwindcss-v4) -- CSS-first config, Oxide engine (HIGH confidence)
- [Neon Postgres Transition Guide](https://neon.com/docs/guides/vercel-postgres-transition-guide) -- Vercel Postgres IS Neon (HIGH confidence)
- [Vercel Blob Documentation](https://vercel.com/docs/vercel-blob) -- upload patterns, limits (HIGH confidence)
- [Zustand GitHub](https://github.com/pmndrs/zustand) -- v5.0.11 latest (HIGH confidence)
- [shadcn/ui CLI v4 Changelog](https://ui.shadcn.com/docs/changelog/2026-03-cli-v4) -- latest CLI (HIGH confidence)
- [Drizzle vs Prisma Comparison](https://makerkit.dev/blog/tutorials/drizzle-vs-prisma) -- ORM decision rationale (MEDIUM confidence)
- [Better Auth vs NextAuth Comparison](https://betterstack.com/community/guides/scaling-nodejs/better-auth-vs-nextauth-authjs-vs-autho/) -- auth decision rationale (MEDIUM confidence)

---
*Stack research for: FTAG KI-Angebotserstellung v2.0 SaaS Platform*
*Researched: 2026-03-10*
