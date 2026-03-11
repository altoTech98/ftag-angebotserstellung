# Phase 15: Admin + Dashboard + Polish - Context

**Gathered:** 2026-03-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Admins can manage users and system settings, all users see a useful dashboard, and the app feels polished with keyboard shortcuts and proper loading states. Email notifications are wired for password reset, user invitation, and analysis completion. The analysis wizard, project management, and catalog management are already built in prior phases.

</domain>

<decisions>
## Implementation Decisions

### Dashboard Layout
- Top row of 3-4 equal-width stat cards: Laufende Analysen, Abgeschlossene Analysen, Fehlerhafte Analysen, Gesamt-Matches
- Below cards: two-column layout — activity feed (left/wider) + statistics widget (right)
- Activity feed shows all user actions: analyses started/completed, projects created, files uploaded, catalogs updated — who did what and when
- Statistics widget: summary numbers (total matches, total gaps, average confidence) + mini horizontal bar chart showing match vs gap ratio
- "Neue Analyse starten" primary button prominent in page header area (top-right, next to title) — Linear-style
- Dashboard page is the landing page after login

### Admin User Management
- Full-width table: Name, Email, Rolle, Status (aktiv/deaktiviert), Erstellt am
- Actions column with edit/deactivate buttons per row
- "Benutzer einladen" button in header to trigger invite flow
- Edit opens dialog for name, role assignment, status toggle
- Consistent with results table pattern from Phase 13

### Audit Log
- Chronological table: Zeitpunkt, Benutzer, Aktion, Details
- Filter by user, action type, date range
- Newest first, paginated
- Track: login, user CRUD, analysis start/complete/fail, project CRUD, catalog changes, settings changes

### System Settings
- Tabbed sections: Analyse | Sicherheit | API-Schluessel
- Analyse tab: default confidence thresholds, max upload size, validation passes
- Sicherheit tab: session timeout duration
- API-Schluessel tab: Claude API key (masked with eye icon reveal toggle)
- Save button per tab section

### Email Notifications (Resend)
- Provider: Resend (API-based, React Email templates)
- Three email types:
  1. Password reset OTP code (replaces console.log placeholder in auth.ts emailOTP)
  2. User invitation ("Sie wurden eingeladen") with signup link
  3. Analysis complete — project name, matches/gaps count, avg confidence, "Ergebnisse ansehen" button
- Template design: minimal branded — FTAG logo, red accent line, white background, gray footer
- German language throughout

### Keyboard Shortcuts
- Decided not to discuss — Claude has discretion on implementation approach

### Skeleton Loaders
- Decided not to discuss — Claude has discretion on implementation approach

### Claude's Discretion
- Keyboard shortcut selection and discoverability (help modal, tooltips, etc.)
- Skeleton loader design and placement
- Dashboard responsive breakpoints and mobile adaptation
- Audit log pagination strategy (cursor vs offset)
- Activity feed item design and grouping
- Invite email flow UX details
- Exact stat card icons and colors
- System settings validation and error handling

</decisions>

<specifics>
## Specific Ideas

- Dashboard should match Linear's clean dashboard feel — big numbers, no clutter
- Activity feed should make it obvious at a glance what's happening in the team
- Admin table follows the same table pattern established in Phase 13 results view
- Email templates should be minimal and corporate — FTAG brand, not marketing-style
- Analysis complete email includes enough info that the user knows whether to click through immediately

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/src/components/ui/table.tsx`: shadcn Table component — use for user management and audit log tables
- `frontend/src/components/ui/card.tsx`: shadcn Card — use for dashboard stat cards
- `frontend/src/components/ui/badge.tsx`: shadcn Badge — use for role badges and status indicators
- `frontend/src/components/ui/dialog.tsx`: shadcn Dialog — use for user edit/invite dialogs
- `frontend/src/components/ui/input.tsx`, `select.tsx`, `button.tsx`: Form components for settings
- `frontend/src/components/layout/no-permission.tsx`: Permission denied component — already wired in admin page
- `frontend/src/app/(app)/admin/page.tsx`: Admin page placeholder with role-gate already working
- `frontend/src/app/(app)/dashboard/page.tsx`: Dashboard placeholder — replace with real implementation

### Established Patterns
- Server component + client component split (page.tsx server, client.tsx client) — Phase 12 pattern
- Server Actions for data mutations (e.g., project-actions.ts, file-actions.ts)
- `auth.api.userHasPermission` with permissions object for role checks
- Better Auth admin plugin already configured with 4 roles and RBAC
- `emailOTP` plugin has `sendVerificationOTP` placeholder ready for Resend integration
- German language throughout UI

### Integration Points
- Better Auth `admin` plugin: provides user CRUD APIs (listUsers, createUser, banUser, etc.)
- Prisma models: User, Session tables already exist via Better Auth
- Need new Prisma models: AuditLog, SystemSettings
- Need new API route or Server Action for audit log queries
- Resend SDK integrates in Next.js API routes or Server Actions
- Python backend: needs endpoint to receive updated settings (thresholds, API key)

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 15-admin-dashboard-polish*
*Context gathered: 2026-03-11*
