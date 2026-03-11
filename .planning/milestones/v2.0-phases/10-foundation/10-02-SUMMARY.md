---
phase: 10-foundation
plan: 02
subsystem: auth
tags: [better-auth, login, password-reset, otp, session-timeout, proxy, route-protection, shadcn-ui]

# Dependency graph
requires:
  - phase: 10-foundation/01
    provides: Next.js 16 app shell, Better Auth config, auth-client.ts, shadcn/ui components, FTAG theme
provides:
  - Login page with email/password form and FTAG-themed Card
  - Password reset flow with 2-step OTP (request code, verify + reset)
  - Route protection via proxy.ts session cookie check
  - Session timeout warning modal with idle detection and countdown
  - useSessionTimeout hook for client-side activity tracking
affects: [10-03, 10-04, 11, 12]

# Tech tracking
tech-stack:
  added: []
  patterns: [proxy.ts route protection with PUBLIC_PATHS whitelist, 2-step password reset OTP flow, client-side idle detection with activity event listeners, non-dismissable session warning dialog]

key-files:
  created:
    - frontend/src/app/proxy.ts
    - frontend/src/app/(auth)/layout.tsx
    - frontend/src/app/(auth)/login/page.tsx
    - frontend/src/app/(auth)/passwort-reset/page.tsx
    - frontend/src/components/auth/login-form.tsx
    - frontend/src/components/auth/password-reset-form.tsx
    - frontend/src/components/auth/session-warning-modal.tsx
    - frontend/src/hooks/use-session-timeout.ts
  modified: []

key-decisions:
  - "Used authClient.emailOtp.sendVerificationOtp and authClient.emailOtp.resetPassword for password reset (Better Auth emailOTP client methods)"
  - "Session warning does not reset on user activity -- user must explicitly click Extend to dismiss"

patterns-established:
  - "Auth pages use (auth) route group with centered layout, no sidebar"
  - "proxy.ts checks session cookie existence only (no DB call) for lightweight route protection"
  - "useSessionTimeout hook accepts configurable expiresInMs parameter (default 8 hours)"
  - "All auth UI text in German with no special characters (ue instead of umlaut)"

requirements-completed: [AUTH-01, AUTH-02, AUTH-03, AUTH-05]

# Metrics
duration: 3min
completed: 2026-03-11
---

# Phase 10 Plan 02: Auth UI Summary

**Login page, password reset OTP flow, route protection via proxy.ts, and session timeout warning modal with idle detection**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-11T00:13:32Z
- **Completed:** 2026-03-11T00:16:39Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- Login page with email/password form, error handling, and expired session info message
- Password reset with 2-step OTP flow (request code via email, verify code + set new password)
- Route protection via proxy.ts redirecting unauthenticated users to /login
- Session timeout hook tracking user idle time with 5-minute warning before expiry
- Session warning modal with countdown timer, extend/logout buttons, non-dismissable

## Task Commits

Each task was committed atomically:

1. **Task 1: Create auth pages (login + password reset) with route protection** - `81d6703` (feat)
2. **Task 2: Implement session timeout warning modal with idle detection** - `74712f9` (feat)

## Files Created/Modified
- `frontend/src/app/proxy.ts` - Route protection with session cookie check and PUBLIC_PATHS whitelist
- `frontend/src/app/(auth)/layout.tsx` - Centered auth layout with FTAG logo placeholder
- `frontend/src/app/(auth)/login/page.tsx` - Login page (server component wrapper)
- `frontend/src/app/(auth)/passwort-reset/page.tsx` - Password reset page (server component wrapper)
- `frontend/src/components/auth/login-form.tsx` - Login form with signIn.email, error states, expired session message
- `frontend/src/components/auth/password-reset-form.tsx` - 2-step OTP reset form (request code, verify + set password)
- `frontend/src/components/auth/session-warning-modal.tsx` - Non-dismissable warning dialog with countdown
- `frontend/src/hooks/use-session-timeout.ts` - Idle detection hook with configurable timeout

## Decisions Made
- Used Better Auth emailOTP client methods (sendVerificationOtp, resetPassword) for the password reset flow
- Session warning modal is non-dismissable (no close button, no outside click dismiss) -- user must explicitly extend or logout
- Activity tracking does not reset timers while warning is showing -- prevents warning from flickering
- Used single text input with tracking-widest styling for OTP code entry (simpler than 6 individual digit boxes)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] React 19 useRef requires initial argument**
- **Found during:** Task 2 (session timeout hook)
- **Issue:** React 19 changed useRef signature to require an argument; `useRef<T>()` without argument causes TS2554
- **Fix:** Changed to `useRef<T>(null)` for all three timer refs
- **Files modified:** frontend/src/hooks/use-session-timeout.ts
- **Verification:** `npx tsc --noEmit` passes with zero errors
- **Committed in:** 74712f9 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Minor React 19 API change. No scope creep.

## Issues Encountered
- Next.js build worker crashes on Windows with exit code 3221226505/134 (OOM in V8) -- this is a known Windows-specific issue, not a compilation error. TypeScript compilation succeeds (verified via `tsc --noEmit`).

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Auth UI complete, ready for Plan 10-03 (app layout with sidebar, header, breadcrumbs)
- SessionWarningModal needs to be placed in (app) layout (Plan 03 scope)
- Login form connects to Better Auth signIn.email -- will work once database is connected

## Self-Check: PASSED

All 8 key files verified present. Both task commits (81d6703, 74712f9) verified in git log.

---
*Phase: 10-foundation*
*Completed: 2026-03-11*
