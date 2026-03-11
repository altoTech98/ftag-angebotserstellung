# Feature Landscape

**Domain:** B2B SaaS web platform for AI-powered construction tender analysis (Next.js frontend for existing FastAPI/Claude AI pipeline)
**Researched:** 2026-03-10
**Overall confidence:** HIGH (well-understood SaaS patterns + clear project requirements)

## Scope Note

This document covers ONLY v2.0 SaaS platform features. The AI pipeline (multi-pass extraction, adversarial matching, gap analysis, Excel generation) is already shipped in v1.0 and is NOT covered here. These features wrap the existing pipeline in a professional B2B web application.

---

## Table Stakes

Features users expect from a professional B2B SaaS tool. Missing = product feels amateur or incomplete.

| Feature | Why Expected | Complexity | Dependencies |
|---------|--------------|------------|--------------|
| **Authentication with email/password** | Any multi-user system requires login. Internal tool with 4 roles demands identity | Low | NextAuth.js + Prisma adapter |
| **Role-based route protection** | Admin pages visible to Analysts = security failure. Middleware-level blocking is minimum viable RBAC | Low | Auth system must exist first |
| **Dashboard with status overview** | First screen after login. Users need: active projects count, recent analyses, pending reviews at a glance | Medium | Project + Analysis data models must exist |
| **Status cards (KPIs)** | How many analyses this week? How many gaps found? Average confidence? Users expect quantified overview | Low | Aggregate queries on analysis results |
| **Recent activity feed** | "What happened since I last logged in?" -- standard in every B2B tool from Notion to Linear | Low | Audit log or activity tracking |
| **Analysis file upload with drag-and-drop** | Users upload 3-15 files per tender. Drag-and-drop is baseline UX for file upload in 2026 | Low | Vercel Blob Storage for file persistence |
| **Analysis progress indicator (SSE)** | Existing v1 feature. Analyses take 2-10 minutes. No progress = user abandonment | Low | Already exists in FastAPI backend, needs Next.js SSE client |
| **Results table with sorting and filtering** | 200-500 positions per tender. Unsorted flat list is unusable. Filter by confidence, status, gap type | Medium | Analysis results data model |
| **Match detail expansion (click-to-expand rows)** | Users need to see WHY a match was chosen: confidence breakdown, reasoning, alternatives | Medium | Chain-of-thought data from AI pipeline |
| **Excel download from results view** | Final deliverable is always Excel. Download button on results page is the minimum output action | Low | Existing Excel generator in FastAPI |
| **Project list with search** | Users manage 5-20 active tenders. Need to find by name, customer, date | Low | Project data model with text search |
| **Responsive layout (desktop-first)** | Sales team uses laptops and desktop monitors. Layout must not break at common resolutions (1280-1920px) | Low | Tailwind CSS responsive utilities |
| **Loading states and error handling** | Skeleton loaders, toast notifications, error boundaries. Without these, app feels broken during API calls | Low | Standard React/Next.js patterns |
| **Breadcrumb navigation** | Multi-level app (Dashboard > Project > Analysis > Results). Users must know where they are | Low | Next.js layout nesting |

## Differentiators

Features that elevate this from "internal tool" to "professional SaaS platform." Not expected by the 4-person sales team initially, but create significant quality-of-life improvements.

| Feature | Value Proposition | Complexity | Dependencies |
|---------|-------------------|------------|--------------|
| **5-step Analysis Wizard** | Guided flow: Upload > Catalog Select > Configuration > Analysis > Results. Prevents misconfiguration, reduces errors vs. single-page form. Users cannot skip steps or submit incomplete data | High | File upload, catalog system, AI pipeline integration |
| **Wizard step validation with Zod schemas** | Each wizard step validates before allowing "Next." Catches problems early (wrong file types, missing catalog, invalid config) instead of failing during analysis | Medium | react-hook-form + Zod per step |
| **Product Catalog versioning** | Upload new catalog version without breaking existing analyses. Roll back if new version has errors. Each analysis records which catalog version was used | High | Catalog data model with version tracking, Vercel Blob for catalog files |
| **Product Catalog CRUD with search** | Browse, search, filter the 891 products. Edit individual products. Bulk import from Excel. Avoids "upload and pray" workflow | Medium | Catalog data model, search index |
| **Project archiving with full history** | Completed tenders move to archive but remain searchable. Analysis history preserved for audits and re-analysis | Medium | Project status enum, soft-delete pattern |
| **Project sharing between users** | Manager assigns project to Analyst. Multiple people can view same project results. Simple permission model (owner + shared-with) | Medium | Project-User junction table |
| **Confidence-based color coding in results** | Green (95%+), Yellow (80-94%), Red (<80%) -- visual scanning of 500 positions in seconds. Mirrors Excel output but interactive | Low | Existing confidence scores from AI pipeline |
| **Gap analysis drill-down** | Click a gap to see: which dimensions failed, severity, suggested alternatives, reasoning. More interactive than Excel sheet | Medium | Gap data from AI pipeline |
| **Admin audit log** | Who ran which analysis, when, with what parameters. Required for B2B compliance and debugging | Medium | Event logging to database on key actions |
| **Admin user management** | Create/edit/deactivate users, assign roles. Admin does not want to touch database directly | Medium | User CRUD with role assignment |
| **System settings panel** | API key configuration, default confidence thresholds, catalog defaults. Avoids environment variable management | Low | Settings table in database |
| **Red/White design system** | FTAG brand identity (red primary). Consistent across all pages. Professional B2B appearance (Linear/Notion style) | Medium | Tailwind CSS config + shadcn/ui theming |
| **Keyboard shortcuts for power users** | Navigate wizard steps, toggle filters, quick-search projects. Sales team processes 5+ tenders/week | Low | Event listeners, can be added incrementally |

## Anti-Features

Features to explicitly NOT build in v2.0. Each has been considered and rejected for specific reasons.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Multi-tenancy** | PROJECT.md explicitly defers to v3.0+. FTAG is single company. Architecture can prepare (tenant_id column) but no tenant switching, billing, or isolation logic | Add tenant_id to data models for future-proofing. Do not build tenant management UI. |
| **2FA / MFA** | Deferred to v3.0+ per PROJECT.md. Internal tool, not internet-facing. Low security risk | Simple email/password auth via NextAuth.js. Revisit when external users are added. |
| **Dark mode** | Deferred to v3.0+ per PROJECT.md. Nice-to-have, not needed for internal B2B tool | Build with CSS variables so dark mode can be added later without refactor. |
| **Multi-language (DE/EN)** | Deferred to v3.0+ per PROJECT.md. FTAG works in German only | Hardcode German UI strings. Use a pattern (e.g., constants file) that can be swapped for i18n later. |
| **PDF export of results** | Deferred to v3.0+ per PROJECT.md. Excel is the standard deliverable | Excel download only. PDF adds complexity (layout engine, pagination) for low value. |
| **Real-time collaboration** | Sales team works individually on tenders. No concurrent editing need | Single-user project ownership with read-only sharing. |
| **Automatic pricing** | Too risky per PROJECT.md. Pricing requires business context, customer relationships, volume discounts | Generate match/gap Excel. Sales fills in prices manually. |
| **Mobile-optimized layout** | PROJECT.md: web-only, desktop users. Mobile layout for data-dense tables is poor UX anyway | Desktop-first responsive. Readable on tablet but not optimized for phone. |
| **Notification system (email/push)** | Over-engineering for 4 internal users. They check the tool directly | Activity feed on dashboard is sufficient. No email notifications. |
| **Custom dashboard widgets / drag-to-rearrange** | Complex to build, minimal value for fixed use case. Dashboard layout is predictable and consistent | Fixed dashboard layout with the 4-6 most useful cards. |
| **File preview (PDF/Word viewer in browser)** | Complex to implement well. Users have local apps for viewing source documents | Download button for source files. Users open in their native apps. |
| **AI chatbot / conversational interface** | The analysis is structured and repeatable. A wizard is better than freeform chat for this workflow | 5-step wizard with clear inputs and outputs. |

## Feature Dependencies

```
Authentication (NextAuth.js + Prisma)
  |
  +---> Role-based route protection (middleware)
  |       |
  |       +---> Admin Panel (Admin role required)
  |       |       |
  |       |       +---> User Management (CRUD)
  |       |       +---> Audit Log (view)
  |       |       +---> System Settings
  |       |       +---> API Key Management
  |       |
  |       +---> Dashboard (all roles, filtered by permissions)
  |               |
  |               +---> Status Cards (KPIs)
  |               +---> Recent Activity Feed
  |               +---> Quick Actions
  |
  +---> Project Management
  |       |
  |       +---> Project CRUD
  |       +---> Project Sharing (between users)
  |       +---> Project Archiving
  |       +---> Project History
  |
  +---> Product Catalog Management
  |       |
  |       +---> Catalog Upload (Excel)
  |       +---> Catalog CRUD (browse/search/edit)
  |       +---> Catalog Versioning
  |
  +---> Analysis Wizard (5 steps)
          |
          Step 1: File Upload --> Vercel Blob Storage
          Step 2: Catalog Selection --> Catalog Management
          Step 3: Configuration --> Analysis parameters
          Step 4: Analysis Start --> FastAPI AI Pipeline (existing)
          Step 5: Results --> Results View
                    |
                    +---> Results Table (sort/filter)
                    +---> Match Detail Expansion
                    +---> Gap Analysis Drill-down
                    +---> Excel Download
```

Key dependency chains:
- Auth MUST come first -- every other feature depends on knowing who the user is
- Database schema (Prisma) MUST come before any CRUD feature
- Project model MUST exist before Analysis Wizard (analyses belong to projects)
- Catalog Management MUST exist before Wizard Step 2 (wizard selects a catalog)
- FastAPI integration MUST work before Wizard Steps 4-5 (analysis execution + results)
- Dashboard is a consumer of all other data -- build last or incrementally

## MVP Recommendation

**Phase 1 -- Auth + Data Foundation:**
1. NextAuth.js authentication (email/password, 4 roles)
2. Prisma schema (Users, Projects, Catalogs, Analyses)
3. Role-based middleware protection
4. Basic layout shell with Red/White design system

**Phase 2 -- Core Workflows:**
5. Project Management (CRUD, list, search)
6. Product Catalog Management (upload, browse, search)
7. Analysis Wizard (5 steps with validation)
8. FastAPI pipeline integration (proxy calls from Next.js to existing backend)

**Phase 3 -- Results + Dashboard:**
9. Results View (table, filters, detail expansion, Excel download)
10. Gap analysis drill-down in results
11. Dashboard with status cards and activity feed
12. Confidence color coding throughout

**Phase 4 -- Admin + Polish:**
13. Admin user management
14. Audit log
15. System settings panel
16. Catalog versioning
17. Project sharing and archiving
18. Keyboard shortcuts

**Defer to v3.0+:**
- Multi-tenancy, 2FA, dark mode, i18n, PDF export, mobile optimization

## Complexity Budget

| Feature Group | Estimated Effort | Risk | Notes |
|---------------|-----------------|------|-------|
| Auth + RBAC | 3-4 days | Low | Well-documented NextAuth.js + Prisma pattern |
| Design System (Red/White) | 2-3 days | Low | Tailwind config + shadcn/ui theme customization |
| Layout Shell + Navigation | 2-3 days | Low | App Router layouts, sidebar, breadcrumbs |
| Project Management | 3-4 days | Low | Standard CRUD with Prisma |
| Catalog Management | 4-5 days | Medium | Excel upload parsing, search, versioning adds complexity |
| Analysis Wizard (5 steps) | 5-7 days | Medium | State management across steps, file upload, SSE integration |
| FastAPI Integration | 3-4 days | Medium | Proxy layer, error handling, SSE forwarding from Python to Next.js |
| Results View | 4-5 days | Medium | Data-dense table, filters, expandable rows, color coding |
| Dashboard | 3-4 days | Low | Aggregate queries, card components, activity feed |
| Admin Panel | 3-4 days | Low | User CRUD, settings form, audit log table |
| Catalog Versioning | 2-3 days | Medium | Version tracking, rollback logic, migration path |
| Project Sharing + Archive | 2-3 days | Low | Permission model, soft-delete |

**Total estimated: 36-49 days for full v2.0 SaaS platform**

## Role Permission Matrix

| Feature | Admin | Manager | Analyst | Viewer |
|---------|-------|---------|---------|--------|
| Dashboard | Full stats | Team stats | Own stats | Own stats |
| Create Project | Yes | Yes | Yes | No |
| Run Analysis | Yes | Yes | Yes | No |
| View Results | All | Team | Own | Shared only |
| Download Excel | Yes | Yes | Yes | Yes |
| Manage Catalog | Yes | Yes | No | No |
| Upload Catalog Version | Yes | Yes | No | No |
| User Management | Yes | No | No | No |
| System Settings | Yes | No | No | No |
| Audit Log | Yes | View only | No | No |
| Archive Project | Yes | Yes | Own only | No |
| Share Project | Yes | Yes | Own only | No |

## Sources

- [Next.js SaaS Dashboard Best Practices](https://www.ksolves.com/blog/next-js/best-practices-for-saas-dashboards)
- [Why Use Next.js for SaaS - 2026 Guide](https://makerkit.dev/blog/tutorials/why-you-should-use-nextjs-saas)
- [Auth.js Role-Based Access Control](https://authjs.dev/guides/role-based-access-control)
- [Next.js Authentication Guide](https://nextjs.org/docs/app/guides/authentication)
- [RBAC in Next.js with NextAuth](https://medium.com/@mesutas.dev/role-based-access-control-in-next-js-with-nextauth-b438fe59eeeb)
- [Middleware for RBAC in Next.js 15 App Router](https://www.jigz.dev/blogs/how-to-use-middleware-for-role-based-access-control-in-next-js-15-app-router)
- [Multi-Step Form with Next.js + React Hook Form + Zod](https://kodaschool.com/blog/build-a-multistep-form-in-next-js-powered-by-react-hook-form-and-zod)
- [Multi-Step Forms in SaaS Kits](https://makerkit.dev/docs/next-supabase-turbo/components/multi-step-forms)
- [Audit Trail for NextAuth.js](https://pangea.cloud/blog/integrate-an-audit-trail-for-nextauthjs-in-a-few-lines-of-code/)
- [Salesforce Versioning and Lifecycle Management](https://trailhead.salesforce.com/content/learn/modules/industries-epc-foundations/explore-versioning-and-lifecycle-management)
- [SaaS Product Catalog Strategy - Zuora](https://www.zuora.com/guides/saas-product-catalog-strategy/)
- [Vercel SaaS Starter Template](https://vercel.com/templates/next.js/next-js-saas-starter)
- Existing v1.0 codebase analysis (HIGH confidence -- direct code review)
- PROJECT.md requirements and constraints (HIGH confidence -- project specification)
