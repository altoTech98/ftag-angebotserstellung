---
phase: 15-admin-dashboard-polish
plan: "03"
subsystem: infra, ui
tags: [react-email, resend, keyboard-shortcuts, skeleton-loaders, email-notifications]

requires:
  - phase: 15-00
    provides: "email.ts Resend client, useKeyboardShortcuts hook, Skeleton component"
  - phase: 15-01
    provides: "Admin actions (inviteUser), auth.ts with emailOTP plugin"
  - phase: 15-02
    provides: "Dashboard page layout for skeleton loader shape"
provides:
  - "3 FTAG-branded React Email templates (password-reset, user-invitation, analysis-complete)"
  - "Resend wired into auth OTP, user invite, and analysis completion"
  - "Global keyboard shortcuts (N/D/P/K/?) with help dialog"
  - "Skeleton loading.tsx for dashboard, projekte, admin, katalog"
affects: []

tech-stack:
  added: [@react-email/components (templates)]
  patterns: [fire-and-forget email sends with try/catch, custom event for shortcuts toggle]

key-files:
  created:
    - frontend/src/emails/password-reset.tsx
    - frontend/src/emails/user-invitation.tsx
    - frontend/src/emails/analysis-complete.tsx
    - frontend/src/components/keyboard-shortcuts/shortcut-provider.tsx
    - frontend/src/components/keyboard-shortcuts/shortcuts-help.tsx
    - frontend/src/app/(app)/dashboard/loading.tsx
    - frontend/src/app/(app)/projekte/loading.tsx
    - frontend/src/app/(app)/admin/loading.tsx
    - frontend/src/app/(app)/katalog/loading.tsx
  modified:
    - frontend/src/lib/auth.ts
    - frontend/src/lib/email.ts
    - frontend/src/lib/actions/admin-actions.ts
    - frontend/src/lib/actions/analysis-actions.ts
    - frontend/src/components/layout/app-shell.tsx

key-decisions:
  - "Resend constructor uses placeholder key when RESEND_API_KEY not set (prevents test failures)"
  - "ShortcutProvider placed inside AppShell (client boundary) rather than server layout"
  - "Analysis completion email parses match_items/gap_items arrays from result JSON for stats"

patterns-established:
  - "Email templates: shared FTAG layout (logo text + red Hr + gray footer) in German"
  - "Fire-and-forget email pattern: try/catch with console.error, never throw"

requirements-completed: [INFRA-05, UI-05, UI-06]

duration: 4min
completed: 2026-03-11
---

# Phase 15 Plan 03: Email Notifications, Keyboard Shortcuts & Skeleton Loaders Summary

**FTAG-branded React Email templates wired to Resend for OTP/invite/completion, global keyboard shortcuts with help dialog, skeleton loaders for all main routes**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-11T15:38:10Z
- **Completed:** 2026-03-11T15:42:39Z
- **Tasks:** 2
- **Files modified:** 14

## Accomplishments
- Three React Email templates with FTAG branding (red accent, German text, logo text header)
- Resend wired into auth.ts (password reset OTP), admin-actions.ts (user invitation), analysis-actions.ts (completion notification)
- sendAnalysisCompleteEmail called fire-and-forget from saveAnalysisResult with match/gap/confidence stats
- Global keyboard shortcuts (N/D/P/K/?) active in app shell, disabled in input fields
- Shortcuts help dialog ("Tastenkuerzel") with kbd-styled key display
- Skeleton loading.tsx files for dashboard, projekte, admin, katalog matching page layouts

## Task Commits

Each task was committed atomically:

1. **Task 1: React Email templates + Resend wiring** - `c08ab49` (feat)
2. **Task 2: Keyboard shortcuts + skeleton loaders** - `2fe2b78` (feat)

## Files Created/Modified
- `frontend/src/emails/password-reset.tsx` - OTP email template with large code display
- `frontend/src/emails/user-invitation.tsx` - Invitation email with "Jetzt anmelden" button
- `frontend/src/emails/analysis-complete.tsx` - Completion email with match/gap/confidence stats table
- `frontend/src/lib/auth.ts` - Replaced console.log placeholder with Resend email send
- `frontend/src/lib/email.ts` - Added placeholder key fallback for test environments
- `frontend/src/lib/actions/admin-actions.ts` - Added invitation email send after user creation
- `frontend/src/lib/actions/analysis-actions.ts` - Added sendAnalysisCompleteEmail function + call site in saveAnalysisResult
- `frontend/src/components/keyboard-shortcuts/shortcut-provider.tsx` - Global shortcut handler with help dialog state
- `frontend/src/components/keyboard-shortcuts/shortcuts-help.tsx` - Dialog showing all keyboard shortcuts
- `frontend/src/components/layout/app-shell.tsx` - Wrapped children with ShortcutProvider
- `frontend/src/app/(app)/dashboard/loading.tsx` - Skeleton: stat cards + two-column layout
- `frontend/src/app/(app)/projekte/loading.tsx` - Skeleton: project cards grid
- `frontend/src/app/(app)/admin/loading.tsx` - Skeleton: tabs + table rows
- `frontend/src/app/(app)/katalog/loading.tsx` - Skeleton: catalog cards grid

## Decisions Made
- Resend constructor uses placeholder key (`re_placeholder`) when env var not set to prevent test suite crashes
- ShortcutProvider placed inside AppShell (client component) rather than server layout.tsx to stay within client boundary
- Analysis completion email extracts stats from result JSON (match_items/gap_items arrays, computed avgConfidence)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed Resend constructor crash in test environment**
- **Found during:** Task 1 (Email template wiring)
- **Issue:** Resend constructor throws "Missing API key" when RESEND_API_KEY env var not set, breaking all tests that import auth.ts
- **Fix:** Changed email.ts to use `process.env.RESEND_API_KEY || 're_placeholder'` -- placeholder key allows instantiation but actual sends would fail gracefully
- **Files modified:** frontend/src/lib/email.ts
- **Verification:** All 98 tests pass
- **Committed in:** c08ab49 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Essential fix for test environment compatibility. No scope creep.

## Issues Encountered
None beyond the Resend constructor issue documented above.

## User Setup Required
None - Resend API key (RESEND_API_KEY) was already configured in Phase 15-00.

## Next Phase Readiness
- All email notifications wired and ready for production use with valid Resend API key
- Keyboard shortcuts active for all authenticated users
- Skeleton loaders provide instant feedback on all main routes
- Ready for Phase 15-04 (final polish/cleanup)

---
*Phase: 15-admin-dashboard-polish*
*Completed: 2026-03-11*
