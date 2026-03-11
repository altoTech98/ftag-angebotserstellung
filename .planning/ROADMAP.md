# Roadmap: FTAG KI-Angebotserstellung v2

## Milestones

- v1.0 **KI-Angebotserstellung v2 Pipeline** -- Phases 1-9 (shipped 2026-03-10)
- v2.0 **AI Tender Matcher -- Web-Oberflaeche & Platform** -- Phases 10-15 (in progress)

## Phases

<details>
<summary>v1.0 KI-Angebotserstellung v2 Pipeline (Phases 1-9) -- SHIPPED 2026-03-10</summary>

- [x] Phase 1: Document Parsing & Pipeline Schemas (2/2 plans) -- completed 2026-03-10
- [x] Phase 2: Multi-Pass Extraction (3/3 plans) -- completed 2026-03-10
- [x] Phase 3: Cross-Document Intelligence (3/3 plans) -- completed 2026-03-10
- [x] Phase 4: Product Matching Engine (2/2 plans) -- completed 2026-03-10
- [x] Phase 5: Adversarial Validation (2/2 plans) -- completed 2026-03-10
- [x] Phase 6: Gap Analysis (2/2 plans) -- completed 2026-03-10
- [x] Phase 7: Excel Output Generation (2/2 plans) -- completed 2026-03-10
- [x] Phase 8: Quality, Observability & End-to-End (3/3 plans) -- completed 2026-03-10
- [x] Phase 9: Frontend V2 Offer & Feedback Wiring (2/2 plans) -- completed 2026-03-10

Full details: `.planning/milestones/v1.0-ROADMAP.md`

</details>

### v2.0 AI Tender Matcher -- Web-Oberflaeche & Platform

**Milestone Goal:** Professionelle SaaS-Web-Applikation (Next.js) um die bestehende AI-Matching-Engine -- minimalistisch, uebersichtlich, B2B-tauglich.

- [x] **Phase 10: Foundation (Auth + Database + Design System)** - Next.js app with Better Auth login, 4-role RBAC, Prisma/Neon DB, and FTAG Rot/Weiss design system (completed 2026-03-11)
- [x] **Phase 11: Python Backend Integration (BFF + Service Auth)** - BFF proxy layer connecting Next.js to Python/FastAPI with service auth and SSE validation (completed 2026-03-11)
- [x] **Phase 12: File Handling + Project Management** - Vercel Blob file uploads, project CRUD with history, archiving, and sharing (completed 2026-03-11)
- [ ] **Phase 13: Analysis Wizard + Results View** - 5-step analysis wizard with SSE progress and full results view with filtering, detail expansion, and Excel export
- [ ] **Phase 14: Catalog Management** - Product catalog upload, browse, search, versioning, and individual product CRUD
- [ ] **Phase 15: Admin + Dashboard + Polish** - Admin user/settings management, audit log, dashboard KPIs, keyboard shortcuts, and email notifications

## Phase Details

### Phase 10: Foundation (Auth + Database + Design System)
**Goal**: Users can log in, have roles enforced across the app, and see a polished FTAG-branded responsive layout
**Depends on**: Nothing (first v2.0 phase)
**Requirements**: AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05, UI-01, UI-02, UI-03, UI-04, INFRA-01
**Success Criteria** (what must be TRUE):
  1. User can create an account, log in with email/password, and log out from any page
  2. User can reset a forgotten password via email link
  3. Session expires after configurable inactivity with a visible warning before timeout
  4. Routes and API endpoints enforce role-based access (Admin/Manager/Analyst/Viewer) -- unauthorized users see an error or redirect, not protected content
  5. App displays the FTAG Rot/Weiss design system with sidebar navigation, breadcrumbs, and responsive layout across desktop, tablet, and mobile
**Plans**: 6 plans

Plans:
- [ ] 10-00-PLAN.md -- Wave 0: Install test infrastructure (Vitest) and create stub test files
- [ ] 10-01-PLAN.md -- Scaffold Next.js 16 with Prisma 7, Better Auth RBAC, and FTAG Tailwind theme
- [ ] 10-02-PLAN.md -- Auth pages (login, password reset) with route protection and session timeout
- [ ] 10-03-PLAN.md -- Layout shell (sidebar, header, breadcrumbs) with responsive behavior and placeholder pages
- [ ] 10-04-PLAN.md -- Integration wiring (session warning in layout, root redirect) and visual checkpoint
- [ ] 10-05-PLAN.md -- Gap closure: enforce invite-only auth and lift session timeout hook to AppShellClient

### Phase 11: Python Backend Integration (BFF + Service Auth)
**Goal**: Next.js can securely proxy requests to the Python/FastAPI backend, and SSE streaming (or polling fallback) is validated end-to-end
**Depends on**: Phase 10
**Requirements**: AUTH-06, INFRA-02, INFRA-03
**Success Criteria** (what must be TRUE):
  1. Every Python API endpoint is reachable through a Next.js API route -- the browser never calls the Python backend directly for CRUD operations
  2. Python backend validates a shared API key on every request and rejects unauthenticated calls with 401
  3. JWT token from Better Auth is forwarded to Python, and Python can extract the user role from it
  4. SSE progress events from the Python backend reach the browser in real-time (either proxied or via direct connection with CORS), with a working polling fallback if SSE is unreliable
**Plans**: 3 plans

Plans:
- [ ] 11-01-PLAN.md -- Python service key auth middleware, SSE token validator, CORS config update
- [ ] 11-02-PLAN.md -- Next.js BFF catch-all proxy, SSE token issuer, SSE client with polling fallback
- [ ] 11-03-PLAN.md -- Gap closure: fix SSE token signature encoding mismatch and add cross-system compatibility test

### Phase 12: File Handling + Project Management
**Goal**: Users can create projects, upload tender documents, and organize their work with sharing and archiving
**Depends on**: Phase 11
**Requirements**: INFRA-04, PROJ-01, PROJ-02, PROJ-03, PROJ-04, ANLZ-01
**Success Criteria** (what must be TRUE):
  1. User can drag-and-drop upload PDF/DOCX/XLSX files (including files over 4.5 MB) and see them stored persistently via Vercel Blob
  2. User can create a project with name, customer, deadline, and description, and see it in a project list
  3. User can view a project detail page showing multiple past analyses with their status and dates
  4. User can archive and delete projects, and share a project with other users who then see it in their project list
**Plans**: 3 plans

Plans:
- [ ] 12-01-PLAN.md -- Prisma schema (Project, File, Analysis, ProjectShare), Vercel Blob upload route, server actions
- [ ] 12-02-PLAN.md -- Project list, create form, detail page with drag-and-drop upload and archive/delete
- [ ] 12-03-PLAN.md -- Project sharing dialog with user search, share management, and detail page wiring

### Phase 13: Analysis Wizard + Results View
**Goal**: Users can run the full AI tender analysis through a guided wizard and explore results with filtering, detail expansion, and Excel export
**Depends on**: Phase 12
**Requirements**: ANLZ-02, ANLZ-03, ANLZ-04, ANLZ-05, RSLT-01, RSLT-02, RSLT-03, RSLT-04
**Success Criteria** (what must be TRUE):
  1. User can walk through the 5-step wizard: select uploaded files, choose a product catalog, configure thresholds and validation passes, start analysis, and see results -- all with per-step validation
  2. User sees real-time progress during analysis (progress bar with stage names) via SSE or polling
  3. User can view all matched requirements in a sortable, filterable table with green/yellow/red confidence color coding
  4. User can expand any requirement row to see the AI reasoning, 6-dimension confidence breakdown, and a side-by-side comparison of requirement vs. matched product
  5. User can download the complete Excel result file (identical to v1.0 4-sheet format) from the results view
**Plans**: TBD

Plans:
- [ ] 13-01: TBD
- [ ] 13-02: TBD
- [ ] 13-03: TBD

### Phase 14: Catalog Management
**Goal**: Managers and Admins can upload, browse, version, and edit the FTAG product catalog without touching files on the server
**Depends on**: Phase 11 (uses BFF layer; does not depend on Phase 12/13)
**Requirements**: KAT-01, KAT-02, KAT-03, KAT-04
**Success Criteria** (what must be TRUE):
  1. User can upload a new product catalog (Excel/CSV) and see import validation results (row count, errors, warnings)
  2. User can browse and search across all products in the catalog with filtering
  3. User can view catalog version history, compare versions, and roll back to a previous version
  4. User can add, edit, or delete individual products in the current catalog
**Plans**: TBD

Plans:
- [ ] 14-01: TBD
- [ ] 14-02: TBD

### Phase 15: Admin + Dashboard + Polish
**Goal**: Admins can manage users and system settings, all users see a useful dashboard, and the app feels polished with keyboard shortcuts and proper loading states
**Depends on**: Phase 13 (dashboard needs analysis data to display)
**Requirements**: ADMIN-01, ADMIN-02, ADMIN-03, ADMIN-04, DASH-01, DASH-02, DASH-03, DASH-04, UI-05, UI-06, INFRA-05
**Success Criteria** (what must be TRUE):
  1. Admin can create, edit, deactivate users and assign roles from a user management page
  2. Admin can view a chronological audit log showing who performed which actions and when, and can configure system settings (default thresholds, max upload size, session timeout, API keys)
  3. All users see a dashboard with status cards (running/completed/failed analyses), recent activity feed, match/gap statistics, and a quick-action button to start a new analysis
  4. Power users can use keyboard shortcuts (e.g., N for new analysis) and all pages show skeleton loaders instead of spinners during loading
  5. System sends email notifications for password reset and analysis completion
**Plans**: TBD

Plans:
- [ ] 15-01: TBD
- [ ] 15-02: TBD
- [ ] 15-03: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 10 -> 11 -> 12 -> 13 -> 14 -> 15
(Phase 14 can run in parallel with 12/13 if desired, as it only depends on Phase 11)

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Document Parsing & Pipeline Schemas | v1.0 | 2/2 | Complete | 2026-03-10 |
| 2. Multi-Pass Extraction | v1.0 | 3/3 | Complete | 2026-03-10 |
| 3. Cross-Document Intelligence | v1.0 | 3/3 | Complete | 2026-03-10 |
| 4. Product Matching Engine | v1.0 | 2/2 | Complete | 2026-03-10 |
| 5. Adversarial Validation | v1.0 | 2/2 | Complete | 2026-03-10 |
| 6. Gap Analysis | v1.0 | 2/2 | Complete | 2026-03-10 |
| 7. Excel Output Generation | v1.0 | 2/2 | Complete | 2026-03-10 |
| 8. Quality, Observability & End-to-End | v1.0 | 3/3 | Complete | 2026-03-10 |
| 9. Frontend V2 Offer & Feedback Wiring | v1.0 | 2/2 | Complete | 2026-03-10 |
| 10. Foundation | 6/6 | Complete   | 2026-03-11 | 2026-03-11 |
| 11. Python Integration | v2.0 | Complete    | 2026-03-11 | 2026-03-11 |
| 12. File Handling + Projects | 3/3 | Complete   | 2026-03-11 | - |
| 13. Analysis Wizard + Results | v2.0 | 0/? | Not started | - |
| 14. Catalog Management | v2.0 | 0/? | Not started | - |
| 15. Admin + Dashboard + Polish | v2.0 | 0/? | Not started | - |
