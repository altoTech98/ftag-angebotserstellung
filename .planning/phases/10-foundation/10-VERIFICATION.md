---
phase: 10-foundation
verified: 2026-03-11T03:00:00Z
status: human_needed
score: 10/10 must-haves verified
re_verification: true
previous_status: gaps_found
previous_score: 8/10
gaps_closed:
  - "Better Auth emailAndPassword config now includes disableSignUp: true — public self-registration is blocked (auth.ts line 22)"
  - "AppShellClient now calls useSessionTimeout directly and passes showWarning/remainingTime/extendSession as props to SessionWarningModal (app-shell-client.tsx lines 3, 16)"
gaps_remaining: []
regressions: []
human_verification:
  - test: "Login form end-to-end with real Neon database"
    expected: "User submits email/password, Better Auth authenticates, session cookie set, redirect to /dashboard"
    why_human: "Requires live Neon Postgres DB with migrated schema; cannot verify auth flow without real database connection"
  - test: "Password reset OTP flow"
    expected: "Step 1 sends OTP (printed to console in dev), Step 2 accepts code + new password and resets successfully"
    why_human: "Requires live database; OTP flow uses Better Auth emailOTP plugin against real DB"
  - test: "Sidebar responsive behavior on mobile"
    expected: "Hamburger menu opens slide-out drawer on mobile breakpoint, backdrop click closes it"
    why_human: "Visual/interactive behavior requiring browser resize; grep cannot verify responsive CSS at runtime"
  - test: "Session timeout warning at 5 minutes before expiry"
    expected: "After 7h55m of inactivity, SessionWarningModal appears with countdown and Extend/Logout buttons"
    why_human: "Requires waiting or mocking timer; idle detection requires browser event system"
  - test: "Sidebar collapse toggle persists across page refresh"
    expected: "Collapse state saved to localStorage ftag-sidebar-collapsed, survives page reload"
    why_human: "localStorage behavior requires browser; grep confirms code but not runtime behavior"
  - test: "Role-gated pages as non-admin"
    expected: "/admin and /neue-analyse show NoPermission for Viewer role; Analyst can access /neue-analyse but not /admin"
    why_human: "Requires live DB with user-role assignment; userHasPermission makes real DB calls"
---

# Phase 10: Foundation Verification Report

**Phase Goal:** Scaffold Next.js 16 app with Better Auth authentication (4-role RBAC), Prisma 7 + Neon Postgres, and FTAG design system. Build login/password-reset flows, session timeout warning, route protection, and the authenticated app shell (sidebar, header, breadcrumbs).
**Verified:** 2026-03-11T03:00:00Z
**Status:** human_needed
**Re-verification:** Yes — after gap closure via Plan 10-05 (commit c97373c)

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Next.js 16 app scaffolded in frontend/ with all dependencies | VERIFIED | frontend/package.json, next.config.ts, tsconfig.json exist; better-auth, prisma, tailwindcss, shadcn in deps |
| 2 | Prisma schema has User, Session, Account, Verification models with admin fields | VERIFIED | frontend/prisma/schema.prisma: all 4 models with role, banned, banReason, banExpiresAt on User |
| 3 | Better Auth exports auth with RBAC (4 roles) and emailOTP plugins | VERIFIED | auth.ts: admin plugin with viewer/analyst/manager/admin roles, emailOTP with 6-digit 10-min codes, nextCookies last |
| 4 | Better Auth is configured invite-only (disableSignUp: true) | VERIFIED | auth.ts line 22: `disableSignUp: true` present in emailAndPassword block — public self-registration blocked |
| 5 | FTAG Tailwind CSS 4 theme has --ftag-red (#C8102E) and sidebar charcoal | VERIFIED | globals.css: --ftag-red: hsl(350 85% 42%), --sidebar-bg: hsl(220 13% 18%), @theme inline block present |
| 6 | Login page with email/password form, session cookie on success, redirect to /dashboard | VERIFIED | login-form.tsx calls signIn.email, handles result.error, router.push("/dashboard") on success |
| 7 | Password reset 2-step OTP flow (request code, verify + set password) | VERIFIED | password-reset-form.tsx: 3 states (request/verify/success), authClient.emailOtp.sendVerificationOtp + resetPassword |
| 8 | Session warning modal appears 5 min before expiry with Extend/Logout — hook lifted to AppShellClient | VERIFIED | app-shell-client.tsx line 3: imports useSessionTimeout; line 16: `const { showWarning, extendSession, remainingTime } = useSessionTimeout()`; props passed to SessionWarningModal |
| 9 | Unauthenticated users redirected from protected routes to /login | VERIFIED | proxy.ts: getSessionCookie check, redirect to /login, PUBLIC_PATHS whitelist |
| 10 | Authenticated app shell: dark charcoal sidebar, header, breadcrumbs | VERIFIED | sidebar.tsx (197 lines): 5 nav items, red active indicator, collapse toggle, mobile drawer; header.tsx, breadcrumbs.tsx all present and wired |

**Score: 10/10 truths verified**

---

## Required Artifacts

### Plan 00 (Wave 0 — Test Infrastructure)

| Artifact | Status | Details |
|----------|--------|---------|
| `frontend/vitest.config.ts` | VERIFIED | jsdom environment, globals: true, @ alias to ./src |
| `frontend/src/__tests__/auth/login.test.ts` | VERIFIED | [AUTH-01] describe block with it.todo() |
| `frontend/src/__tests__/auth/password-reset.test.ts` | VERIFIED | [AUTH-02] describe block with it.todo() |
| `frontend/src/__tests__/hooks/session-timeout.test.ts` | VERIFIED | [AUTH-03] describe block with it.todo() |
| `frontend/src/__tests__/auth/permissions.test.ts` | VERIFIED | [AUTH-04] describe block with it.todo() |
| `frontend/src/__tests__/auth/route-protection.test.ts` | VERIFIED | [AUTH-05] describe block with it.todo() |
| `frontend/src/__tests__/ui/theme.test.ts` | VERIFIED | [UI-01] describe block with it.todo() |
| `frontend/src/__tests__/ui/breadcrumbs.test.ts` | VERIFIED | [UI-04] describe block with it.todo() |
| `frontend/src/__tests__/infra/database.test.ts` | VERIFIED | [INFRA-01] describe block with it.todo() |

### Plan 01 (Wave 1 — Scaffold)

| Artifact | Status | Details |
|----------|--------|---------|
| `frontend/package.json` | VERIFIED | Exists, contains better-auth, prisma, next, tailwindcss, shadcn |
| `frontend/prisma/schema.prisma` | VERIFIED | model User present, 4 Better Auth models, @@map for lowercase tables |
| `frontend/src/lib/auth.ts` | VERIFIED | Exports auth with prismaAdapter, admin plugin (4 roles), emailOTP, nextCookies, disableSignUp: true |
| `frontend/src/lib/permissions.ts` | VERIFIED | Exports ac, viewerRole, analystRole, managerRole, adminRole |
| `frontend/src/styles/globals.css` | PARTIAL | File is at `frontend/src/app/globals.css` (shadcn default); contains --ftag-red. Path deviation documented in SUMMARY-01; functionality verified. |

### Plan 02 (Wave 2 — Auth UI)

| Artifact | Status | Details |
|----------|--------|---------|
| `frontend/src/app/proxy.ts` | VERIFIED | Exports default function proxy with getSessionCookie, PUBLIC_PATHS, config.matcher |
| `frontend/src/app/(auth)/login/page.tsx` | VERIFIED | Server component, checks session, redirects authenticated users, renders LoginForm |
| `frontend/src/components/auth/login-form.tsx` | VERIFIED | Client component, signIn.email call, error handling, expired session message |
| `frontend/src/components/auth/password-reset-form.tsx` | VERIFIED | 2-step OTP flow, emailOtp.sendVerificationOtp + resetPassword |
| `frontend/src/components/auth/session-warning-modal.tsx` | VERIFIED | Pure presentational component: interface accepts showWarning/remainingTime/extendSession props; no useSessionTimeout import; Dialog with countdown, Extend/Logout buttons |
| `frontend/src/hooks/use-session-timeout.ts` | VERIFIED | Exports useSessionTimeout, 5-min warning, fetch to /api/auth/session for extend |

### Plan 03 (Wave 2 — App Shell)

| Artifact | Status | Details |
|----------|--------|---------|
| `frontend/src/components/layout/sidebar.tsx` | VERIFIED | 197 lines, SidebarProvider context, 5 nav items, lucide icons, red active indicator (border-l-[3px] border-sidebar-active), collapse toggle, mobile drawer |
| `frontend/src/components/layout/header.tsx` | VERIFIED | Sticky header, hamburger (mobile), Breadcrumbs, notification bell placeholder, UserMenu |
| `frontend/src/components/layout/breadcrumbs.tsx` | VERIFIED | Uses useBreadcrumbs, ChevronRight separator, last item non-linked |
| `frontend/src/components/layout/user-menu.tsx` | VERIFIED | Avatar initials, DropdownMenu, signOut on Abmelden, redirects to /login |
| `frontend/src/app/(app)/layout.tsx` | VERIFIED | Server component, auth.api.getSession check, redirect if no session, renders AppShell |
| `frontend/src/hooks/use-breadcrumbs.ts` | VERIFIED | Exports useBreadcrumbs, usePathname, German segment labels, starts with "Start" |

### Plan 04 (Wave 3 — Integration)

| Artifact | Status | Details |
|----------|--------|---------|
| `frontend/src/app/(app)/layout.tsx` | VERIFIED | Contains AppShell which renders AppShellClient |
| `frontend/src/components/layout/app-shell-client.tsx` | VERIFIED | Imports useSessionTimeout (line 3), calls it at line 16, passes showWarning/remainingTime/extendSession as props to SessionWarningModal |
| `frontend/src/app/page.tsx` | VERIFIED | Server component, auth.api.getSession, redirect to /dashboard or /login |

### Plan 05 (Gap Closure)

| Artifact | Status | Details |
|----------|--------|---------|
| `frontend/src/lib/auth.ts` | VERIFIED | disableSignUp: true at line 22 in emailAndPassword block |
| `frontend/src/components/layout/app-shell-client.tsx` | VERIFIED | useSessionTimeout imported and called; props passed to SessionWarningModal |
| `frontend/src/components/auth/session-warning-modal.tsx` | VERIFIED | useSessionTimeout removed; interface is `{ showWarning, remainingTime, extendSession }` props |

---

## Key Link Verification

### Plan 01 Key Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/lib/auth.ts` | `src/lib/prisma.ts` | prismaAdapter import | WIRED | Line 2: import prismaAdapter; line 16: prismaAdapter(prisma, ...) |
| `src/lib/auth.ts` | `src/lib/permissions.ts` | access control import | WIRED | Lines 8-13: imports ac and 4 role definitions |
| `src/app/api/auth/[...all]/route.ts` | `src/lib/auth.ts` | auth handler export | WIRED | export { GET, POST } = toNextJsHandler(auth.handler) |

### Plan 02 Key Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/app/proxy.ts` | `better-auth/cookies` | getSessionCookie | WIRED | Lines 2, 15: imported and called |
| `src/components/auth/login-form.tsx` | `src/lib/auth-client.ts` | signIn.email | WIRED | Line 5: import signIn; line 36: signIn.email({...}) |
| `src/components/auth/password-reset-form.tsx` | `src/lib/auth-client.ts` | emailOTP client | WIRED | Lines 36, 70: authClient.emailOtp.sendVerificationOtp, resetPassword |
| `src/hooks/use-session-timeout.ts` | `/api/auth/session` | fetch to refresh | WIRED | Line 64: fetch("/api/auth/session", { method: "GET", credentials: "include" }) |

### Plan 03 Key Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/app/(app)/layout.tsx` | `src/lib/auth.ts` | auth.api.getSession | WIRED | Line 11: auth.api.getSession({ headers: await headers() }) |
| `src/components/layout/sidebar.tsx` | `lucide-react` | icon imports | WIRED | Line 16: imports LayoutDashboard, FolderOpen, PlusCircle, BookOpen, Settings |
| `src/components/layout/user-menu.tsx` | `src/lib/auth-client.ts` | signOut | WIRED | Line 4: import signOut; line 29: await signOut() |
| `src/hooks/use-breadcrumbs.ts` | `next/navigation` | usePathname | WIRED | Line 3: import usePathname; line 19: called |

### Plan 04 Key Links (Previously Partial — Now Wired)

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/app/(app)/layout.tsx` | `src/components/layout/app-shell-client.tsx` | AppShellClient render | WIRED | layout.tsx -> AppShell -> AppShellClient chain; confirmed by SUMMARY-04 and file content |
| `src/components/layout/app-shell-client.tsx` | `src/components/auth/session-warning-modal.tsx` | SessionWarningModal with props | WIRED | app-shell-client.tsx lines 4, 20-24: imports and renders SessionWarningModal with showWarning/remainingTime/extendSession props |
| `src/components/layout/app-shell-client.tsx` | `src/hooks/use-session-timeout.ts` | direct import and call | WIRED | app-shell-client.tsx line 3: import useSessionTimeout; line 16: const { showWarning, extendSession, remainingTime } = useSessionTimeout() |

---

## Requirements Coverage

| Requirement | Plans | Description | Status | Evidence |
|-------------|-------|-------------|--------|----------|
| AUTH-01 | 02, 04, 05 | User kann sich mit E-Mail und Passwort einloggen | SATISFIED | login-form.tsx calls signIn.email, handles success/error, redirects to /dashboard |
| AUTH-02 | 02 | User kann Passwort per E-Mail-Link zuruecksetzen | SATISFIED (with note) | REQUIREMENTS.md says "E-Mail-Link" but implementation uses 6-digit OTP per CONTEXT.md design. Intentional deviation documented in SUMMARY-02. |
| AUTH-03 | 02, 04, 05 | Session nach konfigurierbarer Inaktivitaet beendet (mit Warnung) | SATISFIED | use-session-timeout.ts: idle tracking, 5-min warning; hook lifted to AppShellClient; redirect to /login?expired=true on expire |
| AUTH-04 | 01 | 4 Rollen: Admin, Manager, Analyst, Viewer | SATISFIED | permissions.ts defines 4 tiered roles; auth.ts admin plugin uses them; Prisma User.role defaults "viewer" |
| AUTH-05 | 02 | Routen und API-Endpoints rollenbasiert geschuetzt | SATISFIED | proxy.ts redirects unauthenticated requests; (app)/layout.tsx server-side session check; admin/neue-analyse pages use userHasPermission |
| UI-01 | 01 | Rot/Weiss Design-System (Tailwind CSS 4 + shadcn/ui) | SATISFIED | globals.css: @theme inline, --ftag-red, --sidebar-bg charcoal; shadcn components initialized |
| UI-02 | 03 | Responsive Layout (Desktop, Tablet, Mobil) | SATISFIED | sidebar.tsx: desktop collapsible, tablet icon-only via localStorage, mobile overlay drawer |
| UI-03 | 03 | Sidebar-Navigation mit rotem Akzent fuer aktives Item | SATISFIED | sidebar.tsx active item: border-l-[3px] border-sidebar-active bg-sidebar-active/10 where sidebar-active = --ftag-red |
| UI-04 | 03, 04 | Breadcrumb-Navigation auf allen Seiten | SATISFIED | use-breadcrumbs.ts + breadcrumbs.tsx rendered in header.tsx on all (app) pages |
| INFRA-01 | 00, 01 | Next.js 16 App Router + Prisma 7 + Neon Postgres | SATISFIED | Next.js 16 scaffolded, Prisma 7 schema, PrismaClient singleton with PrismaPg adapter, env template for Neon URL |

**Orphaned requirements:** None. All 10 requirement IDs from plan frontmatter are accounted for.

AUTH-06, UI-05, UI-06, INFRA-02 through INFRA-05 are assigned to later phases and are not expected in Phase 10.

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/lib/auth.ts` | 44 | `// placeholder until INFRA-05 (Phase 15)` | Info | Expected — email OTP console.log is intentional dev placeholder; INFRA-05 planned for Phase 15 |
| `src/app/globals.css` | — | Path is `src/app/globals.css` not `src/styles/globals.css` | Info | Documented deviation in SUMMARY-01; shadcn default location; components.json points to correct path |
| `src/components/layout/user-menu.tsx` | 49 | `DropdownMenuItem onClick={() => {}}` for Profil | Warning | Profil link is a no-op placeholder; acceptable per plan ("links to # for now") |

No blocker anti-patterns remain. The previous blocker (missing disableSignUp) is resolved.

---

## Gap Closure Verification (Re-verification)

### Gap 1: disableSignUp: true — CLOSED

**Previous state:** `emailAndPassword` block had `enabled: true`, `minPasswordLength: 8`, `maxPasswordLength: 128`, `requireEmailVerification: false` — no `disableSignUp`.

**Current state:** `auth.ts` line 22 reads `disableSignUp: true`. Block is complete and invite-only enforcement is active.

**Commit:** c97373c — "fix(10-05): add disableSignUp and lift useSessionTimeout to AppShellClient"

### Gap 2: useSessionTimeout at AppShellClient level — CLOSED

**Previous state:** `app-shell-client.tsx` did not import or call `useSessionTimeout`; the hook lived entirely inside `session-warning-modal.tsx`. The plan's key link contract was not met.

**Current state:**
- `app-shell-client.tsx` line 3: `import { useSessionTimeout } from "@/hooks/use-session-timeout"`
- `app-shell-client.tsx` line 16: `const { showWarning, extendSession, remainingTime } = useSessionTimeout()`
- Props are passed explicitly: `<SessionWarningModal showWarning={showWarning} remainingTime={remainingTime} extendSession={extendSession} />`
- `session-warning-modal.tsx` has no `useSessionTimeout` import (confirmed: grep returns exit code 1)
- `session-warning-modal.tsx` interface is now `{ showWarning: boolean; remainingTime: number; extendSession: () => void }` — purely presentational

**Commit:** c97373c — same atomic commit covers both fixes

### Regression Check

No regressions found. Session warning functionality is preserved: same hook, same timing constants, same German UI text — only the call site changed from modal to shell. `handleLogout` still redirects to `/login`. `formatRemainingTime` helper is unchanged.

---

## Human Verification Required

All automated checks pass. The following items require human testing with a live environment.

### 1. Login Flow with Live Database

**Test:** Set up Neon Postgres, run `npx prisma migrate dev --name init`, create a user via seed-admin.ts, visit http://localhost:3000, submit login form with valid credentials.
**Expected:** Session cookie set, redirect to /dashboard, sidebar appears with user's name in header.
**Why human:** Requires live Neon DB connection; auth handshake cannot be verified statically.

### 2. Password Reset OTP Flow

**Test:** Click "Passwort vergessen?" on login page, submit email, check server console for OTP code, enter code + new password on step 2.
**Expected:** OTP logged to console (DEV), new password accepted, success message displayed, login with new password succeeds.
**Why human:** OTP generated server-side by Better Auth against real DB; cannot mock without live environment.

### 3. Sidebar Responsive Behavior

**Test:** Open app in browser, resize from desktop (>1024px) to tablet (~768px) to mobile (<768px).
**Expected:** Desktop shows expanded sidebar; tablet shows icon-only (collapsed, restored from localStorage); mobile hides sidebar and shows hamburger that opens slide-out overlay drawer; backdrop click closes drawer.
**Why human:** CSS breakpoint behavior requires browser rendering at actual viewport dimensions.

### 4. Session Timeout Warning

**Test:** Log in, then either wait 7h55m or mock `IDLE_TIMEOUT_MS` / `WARNING_BEFORE_MS` in use-session-timeout.ts to shorter durations, observe modal.
**Expected:** SessionWarningModal appears with countdown timer; "Sitzung verlaengern" resets timer and closes modal; "Abmelden" redirects to /login.
**Why human:** Real timer requires 8 hours or test mocking; browser idle event system needed.

### 5. Sidebar Collapse Persistence

**Test:** Collapse sidebar, refresh page, observe sidebar state.
**Expected:** Sidebar remains collapsed; `ftag-sidebar-collapsed` key in localStorage is `"true"` and read on mount.
**Why human:** localStorage persistence requires browser runtime.

### 6. Role-Gated Pages as Non-Admin

**Test:** Log in as a Viewer-role user (role = "viewer" in DB), navigate to /admin and /neue-analyse.
**Expected:** /admin shows "Keine Berechtigung" (NoPermission component); /neue-analyse shows NoPermission (analyst+ required); log in as Analyst, /neue-analyse now accessible.
**Why human:** Requires live DB with user role assignment; `userHasPermission` makes real server-side DB calls.

---

_Verified: 2026-03-11T03:00:00Z_
_Verifier: Claude (gsd-verifier)_
_Re-verification: Yes — gap closure via Plan 10-05 (commit c97373c)_
