# Phase 10: Foundation (Auth + Database + Design System) - Context

**Gathered:** 2026-03-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can log in with email/password, have 4-tier role-based access enforced across routes and API endpoints, and see a polished FTAG Rot/Weiss responsive layout with sidebar navigation and breadcrumbs. Account creation, project management, analysis, and all business features belong to later phases.

</domain>

<decisions>
## Implementation Decisions

### Design System
- FTAG Rot/Weiss: Classic FTAG Red (#C8102E) as primary, white backgrounds, dark gray text
- Visual style: Linear/Notion-style — clean, minimal, lots of whitespace, subtle borders, flat design, professional B2B feel
- Dark charcoal sidebar with white text, red accent for active nav item
- Typography: Inter font family
- Components via shadcn/ui CLI v4, themed to FTAG brand
- Tailwind CSS 4 with CSS-first @theme config (no tailwind.config.js)

### Auth Flow & UX
- Account creation: Invite-only — Admin sends email invitations, user sets own password via signup link
- No public registration
- Login page: Centered card on clean background with FTAG logo above, email + password + submit
- Password reset: 6-digit code via email (not magic link), then set new password
- Session timeout: Configurable by Admin in settings (default 8 hours), warning modal 5 minutes before expiry with "Extend" button

### Navigation & Layout
- Sidebar items: Dashboard, Projekte, Neue Analyse, Katalog, Admin (role-gated) — items appear as phases ship
- Mobile: Slide-out drawer (hamburger menu opens overlay drawer)
- Desktop: Collapsible sidebar (toggle to icon-only mode for more content space)
- Top header: Breadcrumbs on left, notification bell + user avatar dropdown (profile, logout) on right
- Responsive breakpoints: desktop (sidebar expanded), tablet (sidebar collapsed to icons), mobile (sidebar hidden, hamburger)

### Role Permissions
- Tiered access model (each role inherits permissions from the role below):
  - **Viewer**: View analysis results only
  - **Analyst**: Run analyses + view results
  - **Manager**: + manage projects and product catalog
  - **Admin**: + user management, system settings, audit log
- Default role for new invites: Set by Admin during invitation (no fixed default)
- Unauthorized access: Show page skeleton with "Keine Berechtigung" message and note to contact Admin
- All nav items visible to all roles (denied pages show permission message, not hidden)
- First Admin: Pre-seeded via environment variables (DEFAULT_ADMIN_EMAIL, DEFAULT_ADMIN_PASSWORD)

### Claude's Discretion
- Exact red hex code refinement (start with #C8102E, adjust if needed)
- Button styles, card styling, spacing system details
- Breadcrumb separator and truncation behavior
- Error message styling and toast positioning
- Login form validation UX (inline vs. on-submit)
- Account lockout policy (if any)
- Notification bell placeholder behavior (empty state until Phase 15)

</decisions>

<specifics>
## Specific Ideas

- App should feel like Linear — clean, not cluttered, professional B2B tool
- Sidebar follows Linear's dark sidebar pattern with smooth collapse animation
- Login page is minimal and corporate — no illustrations or fancy graphics

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend-react/src/context/AuthContext.jsx`: Existing auth context pattern (React) — not directly reusable in Next.js but shows the auth flow design
- `frontend-react/src/hooks/useSSE.js`: SSE hook pattern — can inform real-time features later
- `backend/config.py`: Already has DEFAULT_ADMIN_EMAIL, DEFAULT_ADMIN_PASSWORD, JWT_SECRET env vars — Python backend auth config aligns

### Established Patterns
- Python backend uses FastAPI with Pydantic models — Next.js BFF will proxy to this (Phase 11)
- v1.0 frontend is vanilla React (Vite) — v2.0 is a complete rewrite in Next.js App Router, no code reuse expected
- German language throughout UI (error messages, labels) — maintain this in v2.0

### Integration Points
- Phase 10 creates the Next.js app shell — all subsequent phases build into this structure
- Better Auth provides the auth layer — Prisma adapter connects to Neon Postgres
- Design system tokens (colors, typography, spacing) defined here are used by all future components

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 10-foundation*
*Context gathered: 2026-03-11*
