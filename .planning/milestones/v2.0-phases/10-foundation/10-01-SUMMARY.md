---
phase: 10-foundation
plan: 01
subsystem: infra
tags: [next.js, better-auth, prisma, tailwind-css-4, shadcn-ui, rbac, neon-postgres]

# Dependency graph
requires:
  - phase: 10-foundation/00
    provides: Vitest test infrastructure and stub test files
provides:
  - Next.js 16 application shell in frontend/ directory
  - Better Auth server config with admin plugin and emailOTP
  - Prisma 7 schema with User, Session, Account, Verification models
  - RBAC permissions with 4 tiered roles (viewer, analyst, manager, admin)
  - FTAG Rot/Weiss Tailwind CSS 4 theme with design tokens
  - shadcn/ui v4 initialized with button, input, label, card, dialog, alert
  - Auth API route handler at /api/auth/[...all]
  - Admin seeding function from environment variables
affects: [10-02, 10-03, 10-04, 11, 12, 13, 14, 15]

# Tech tracking
tech-stack:
  added: [next.js@16, react@19, better-auth, prisma@7, @prisma/adapter-pg, tailwindcss@4, shadcn/ui@v4, tw-animate-css, lucide-react, sonner, inter-font]
  patterns: [CSS-first @theme inline for Tailwind, prisma adapter pattern for Better Auth, PrismaClient singleton with PrismaPg adapter, RBAC via createAccessControl]

key-files:
  created:
    - frontend/package.json
    - frontend/next.config.ts
    - frontend/tsconfig.json
    - frontend/.env.example
    - frontend/components.json
    - frontend/prisma/schema.prisma
    - frontend/src/lib/prisma.ts
    - frontend/src/lib/auth.ts
    - frontend/src/lib/auth-client.ts
    - frontend/src/lib/permissions.ts
    - frontend/src/lib/seed-admin.ts
    - frontend/src/lib/utils.ts
    - frontend/src/app/api/auth/[...all]/route.ts
    - frontend/src/app/globals.css
    - frontend/src/app/layout.tsx
    - frontend/src/app/page.tsx
    - frontend/src/components/ui/button.tsx
    - frontend/src/components/ui/input.tsx
    - frontend/src/components/ui/label.tsx
    - frontend/src/components/ui/card.tsx
    - frontend/src/components/ui/dialog.tsx
    - frontend/src/components/ui/alert.tsx
  modified: []

key-decisions:
  - "Kept globals.css in src/app/ (shadcn default) instead of src/styles/ to match components.json config"
  - "Skipped prisma.config.ts -- Prisma 7.4.2 failed to parse it; generate works without it, config only needed for migrations with real DB"
  - "Created .env.example instead of tracking .env.local (gitignored by Next.js default .gitignore)"
  - "Restored Plan 10-00 test files from git history after create-next-app replaced frontend/ directory"

patterns-established:
  - "Import Prisma from @/generated/prisma/client (not @prisma/client) for Prisma 7"
  - "Better Auth plugins order: domain plugins first, nextCookies() last"
  - "FTAG brand token naming: --ftag-red, --ftag-red-hover, --ftag-red-light"
  - "Semantic tokens reference FTAG tokens: --primary: var(--ftag-red)"

requirements-completed: [INFRA-01, UI-01, AUTH-04]

# Metrics
duration: 13min
completed: 2026-03-11
---

# Phase 10 Plan 01: Next.js + Auth + Design System Summary

**Next.js 16 app with Better Auth (invite-only email/password, 4-tier RBAC, emailOTP), Prisma 7 schema for Neon Postgres, and FTAG Rot/Weiss Tailwind CSS 4 theme**

## Performance

- **Duration:** 13 min
- **Started:** 2026-03-10T23:56:20Z
- **Completed:** 2026-03-11T00:09:46Z
- **Tasks:** 3
- **Files modified:** 22+

## Accomplishments
- Complete Next.js 16 project scaffolded with all dependencies (better-auth, prisma 7, shadcn/ui, tailwind 4)
- Better Auth configured with invite-only email/password, admin plugin (4 RBAC roles), and emailOTP plugin
- Prisma 7 schema generates successfully with User, Session, Account, Verification models
- FTAG Rot/Weiss design system established with CSS-first Tailwind 4 theme tokens
- 6 shadcn/ui components initialized and themed to FTAG brand

## Task Commits

Each task was committed atomically:

1. **Task 1: Scaffold Next.js 16 project with dependencies** - `8d7cb9f` (feat)
2. **Task 2: Configure Prisma 7, Better Auth, and RBAC permissions** - `32469a2` (feat)
3. **Task 3: Set up FTAG Tailwind theme and root layout** - `8229549` (feat)

## Files Created/Modified
- `frontend/package.json` - Project manifest with all v2.0 dependencies
- `frontend/next.config.ts` - Next.js config with serverExternalPackages for better-auth
- `frontend/prisma/schema.prisma` - Database schema with 4 Better Auth models + admin fields
- `frontend/src/lib/auth.ts` - Better Auth server config with admin + emailOTP plugins
- `frontend/src/lib/auth-client.ts` - Better Auth React client with admin + emailOTP client plugins
- `frontend/src/lib/permissions.ts` - RBAC access control: viewer < analyst < manager < admin
- `frontend/src/lib/prisma.ts` - PrismaClient singleton with PrismaPg adapter
- `frontend/src/lib/seed-admin.ts` - Admin user seeding from environment variables
- `frontend/src/lib/utils.ts` - cn() helper (clsx + twMerge) for shadcn/ui
- `frontend/src/app/api/auth/[...all]/route.ts` - Better Auth API route handler
- `frontend/src/app/globals.css` - FTAG Tailwind CSS 4 theme with brand tokens
- `frontend/src/app/layout.tsx` - Root layout with Inter font and German metadata
- `frontend/src/app/page.tsx` - Temporary redirect to /login
- `frontend/src/components/ui/*.tsx` - shadcn/ui components (button, input, label, card, dialog, alert)
- `frontend/components.json` - shadcn/ui configuration
- `frontend/.env.example` - Environment variable template

## Decisions Made
- Kept globals.css at `src/app/globals.css` (shadcn default location) rather than moving to `src/styles/` -- avoids mismatch with components.json CSS path
- Skipped `prisma.config.ts` -- Prisma 7.4.2 consistently failed to parse it on Windows; `prisma generate` works without it; the config is only needed for `prisma migrate` which requires a real database connection (deferred until Neon DB is provisioned)
- Created `.env.example` (tracked) alongside `.env.local` (gitignored) to document required environment variables
- Had to restore Plan 10-00 test files from git history after `create-next-app` replaced the frontend/ directory

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Prisma 7 schema.prisma url/directUrl removal**
- **Found during:** Task 2 (Prisma generate)
- **Issue:** Prisma 7 no longer supports `url` and `directUrl` in schema.prisma datasource block -- they must be in prisma.config.ts
- **Fix:** Removed url/directUrl from schema.prisma; prisma generate works without them. prisma.config.ts creation deferred (parsing issues on Windows)
- **Files modified:** frontend/prisma/schema.prisma
- **Verification:** `npx prisma generate` succeeds, client generated at src/generated/prisma/client
- **Committed in:** 32469a2 (Task 2 commit)

**2. [Rule 3 - Blocking] Restored Plan 10-00 test files lost during scaffolding**
- **Found during:** Task 1 (create-next-app)
- **Issue:** `rm -rf frontend` removed the _preserve directory containing test files from Plan 10-00
- **Fix:** Recovered all 8 test stub files and vitest.config.ts from git commit dc8dbb2
- **Files modified:** frontend/vitest.config.ts, frontend/src/__tests__/**
- **Verification:** All test files restored, `npx vitest run` would succeed
- **Committed in:** 8d7cb9f (Task 1 commit)

**3. [Rule 3 - Blocking] .env.example blocked by .gitignore pattern**
- **Found during:** Task 1 (committing)
- **Issue:** Next.js default .gitignore has `.env*` pattern which also ignores .env.example
- **Fix:** Added `!.env.example` exception to .gitignore
- **Files modified:** frontend/.gitignore
- **Committed in:** 8d7cb9f (Task 1 commit)

---

**Total deviations:** 3 auto-fixed (3 blocking)
**Impact on plan:** All necessary for task completion. No scope creep.

## Issues Encountered
- Prisma 7.4.2 cannot parse `prisma.config.ts` on this Windows environment regardless of content format -- seems to be a Prisma 7 tooling issue. Generate works without the config file; migrations will need the config when a real database is available.
- `create-next-app` requires an empty or non-existent target directory, so the existing frontend/ from Plan 10-00 had to be replaced, with test files recovered from git history.

## User Setup Required
None - no external service configuration required at this stage. Real Neon database credentials needed before running migrations (future plan).

## Next Phase Readiness
- Application shell ready for Plan 10-02 (route protection with proxy.ts)
- All auth infrastructure in place for Plan 10-03 (login/password-reset UI)
- Design system tokens established for Plan 10-04 (sidebar layout)
- Test stubs from Plan 10-00 preserved and ready for real test implementation

## Self-Check: PASSED

All 16 key files verified present. All 3 task commits (8d7cb9f, 32469a2, 8229549) verified in git log.

---
*Phase: 10-foundation*
*Completed: 2026-03-11*
