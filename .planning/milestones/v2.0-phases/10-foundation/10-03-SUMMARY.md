---
phase: 10-foundation
plan: 03
subsystem: ui
tags: [sidebar, header, breadcrumbs, layout, responsive, role-gating, shadcn-ui, lucide-react]

# Dependency graph
requires:
  - phase: 10-foundation/01
    provides: Next.js 16 app shell, Better Auth config, FTAG Tailwind theme, shadcn/ui components
  - phase: 10-foundation/02
    provides: Auth pages, route protection via proxy.ts, auth-client.ts with signOut
provides:
  - Dark charcoal sidebar with 5 nav items and red active indicator
  - Collapsible sidebar (desktop toggle, tablet icon-only, mobile drawer)
  - Top header with breadcrumbs and user avatar dropdown
  - Authenticated (app) layout with session check and redirect
  - 5 placeholder pages with role-based permission gating
  - Reusable NoPermission component for unauthorized access
  - SidebarProvider context for mobile drawer state sharing
affects: [10-04, 11, 12, 13, 14, 15]

# Tech tracking
tech-stack:
  added: []
  patterns: [SidebarProvider context for shared mobile state, AppShell client wrapper in server layout, userHasPermission for page-level role gating, localStorage sidebar collapsed state persistence]

key-files:
  created:
    - frontend/src/components/layout/sidebar.tsx
    - frontend/src/components/layout/header.tsx
    - frontend/src/components/layout/breadcrumbs.tsx
    - frontend/src/components/layout/user-menu.tsx
    - frontend/src/components/layout/app-shell.tsx
    - frontend/src/components/layout/no-permission.tsx
    - frontend/src/hooks/use-breadcrumbs.ts
    - frontend/src/components/ui/dropdown-menu.tsx
    - frontend/src/app/(app)/layout.tsx
    - frontend/src/app/(app)/dashboard/page.tsx
    - frontend/src/app/(app)/projekte/page.tsx
    - frontend/src/app/(app)/neue-analyse/page.tsx
    - frontend/src/app/(app)/katalog/page.tsx
    - frontend/src/app/(app)/admin/page.tsx
  modified: []

key-decisions:
  - "Created AppShell client wrapper to bridge server layout with client-side SidebarProvider context"
  - "Better Auth userHasPermission returns { success } directly, not wrapped in { data: { success } }"
  - "Used shadcn v4 dropdown-menu (base-ui) without asChild prop -- base-ui Trigger renders directly"

patterns-established:
  - "SidebarProvider context pattern for cross-component mobile drawer state"
  - "NoPermission component for consistent unauthorized access display"
  - "Server-side permission check pattern: auth.api.userHasPermission({ body: { userId, permissions } }).success"
  - "Breadcrumb segment labels map for German translations"

requirements-completed: [UI-02, UI-03, UI-04]

# Metrics
duration: 4min
completed: 2026-03-11
---

# Phase 10 Plan 03: App Shell Layout Summary

**Dark charcoal sidebar with 5 nav items, responsive collapse/drawer, breadcrumb header with user menu, and 5 role-gated placeholder pages**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-11T00:19:25Z
- **Completed:** 2026-03-11T00:23:30Z
- **Tasks:** 2
- **Files modified:** 14

## Accomplishments
- Complete app shell with dark sidebar navigation (5 items with lucide icons and red active indicator)
- Responsive sidebar: collapsible on desktop, icon-only on tablet, slide-out drawer on mobile
- Header with pathname-based German breadcrumbs, disabled notification bell, and user avatar dropdown
- Authenticated layout with server-side session check and redirect to /login
- Role-gated pages: Neue Analyse requires analyst+, Admin requires admin role
- Reusable NoPermission component with ShieldX icon and German text

## Task Commits

Each task was committed atomically:

1. **Task 1: Build sidebar navigation and header with breadcrumbs** - `47dd3a7` (feat)
2. **Task 2: Create authenticated layout and placeholder pages with role gating** - `81f28d6` (feat)

## Files Created/Modified
- `frontend/src/components/layout/sidebar.tsx` - Dark sidebar with nav items, collapse toggle, mobile drawer, SidebarProvider context
- `frontend/src/components/layout/header.tsx` - Sticky header with hamburger, breadcrumbs, notification bell, user menu
- `frontend/src/components/layout/breadcrumbs.tsx` - Breadcrumb trail with German segment labels
- `frontend/src/components/layout/user-menu.tsx` - Avatar initials dropdown with profile and logout
- `frontend/src/components/layout/app-shell.tsx` - Client wrapper bridging server layout with SidebarProvider
- `frontend/src/components/layout/no-permission.tsx` - Centered permission denied display
- `frontend/src/hooks/use-breadcrumbs.ts` - Hook deriving breadcrumb segments from pathname
- `frontend/src/components/ui/dropdown-menu.tsx` - shadcn v4 dropdown-menu (base-ui)
- `frontend/src/app/(app)/layout.tsx` - Server layout with auth session check
- `frontend/src/app/(app)/dashboard/page.tsx` - Dashboard placeholder (all roles)
- `frontend/src/app/(app)/projekte/page.tsx` - Projekte placeholder (all roles)
- `frontend/src/app/(app)/neue-analyse/page.tsx` - Neue Analyse with analysis.create permission check
- `frontend/src/app/(app)/katalog/page.tsx` - Katalog placeholder (all roles)
- `frontend/src/app/(app)/admin/page.tsx` - Admin with admin.access permission check

## Decisions Made
- Created AppShell client wrapper component to bridge the server-side (app) layout with client-side SidebarProvider context for mobile drawer state sharing
- Better Auth `userHasPermission` returns `{ success }` directly (not `{ data: { success } }` as the plan's code example suggested)
- Used shadcn v4 dropdown-menu without `asChild` prop since base-ui Trigger renders the trigger element directly

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed Better Auth userHasPermission return type**
- **Found during:** Task 2 (permission check pages)
- **Issue:** Plan code example used `hasAccess.data?.success` but Better Auth returns `{ error, success }` directly
- **Fix:** Changed to `hasAccess.success` in admin and neue-analyse pages
- **Files modified:** frontend/src/app/(app)/admin/page.tsx, frontend/src/app/(app)/neue-analyse/page.tsx
- **Verification:** `tsc --noEmit` passes with zero errors
- **Committed in:** 81f28d6 (Task 2 commit)

**2. [Rule 1 - Bug] Removed asChild prop from shadcn v4 dropdown-menu usage**
- **Found during:** Task 1 (user menu component)
- **Issue:** shadcn v4 uses base-ui which doesn't support `asChild` prop on DropdownMenuTrigger and DropdownMenuItem
- **Fix:** Removed asChild and rendered content directly inside Trigger/Item components
- **Files modified:** frontend/src/components/layout/user-menu.tsx
- **Verification:** `tsc --noEmit` passes with zero errors
- **Committed in:** 47dd3a7 (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (2 bugs)
**Impact on plan:** Both fixes necessary for TypeScript compilation. No scope creep.

## Issues Encountered
None beyond the auto-fixed items above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- App shell complete, ready for Plan 10-04 (integration/polish)
- SessionWarningModal from Plan 02 needs to be placed in (app) layout (Plan 04 scope per plan note)
- All nav items visible to all roles -- denied pages show NoPermission component as intended

## Self-Check: PASSED

All 14 key files verified present. Both task commits (47dd3a7, 81f28d6) verified in git log.

---
*Phase: 10-foundation*
*Completed: 2026-03-11*
