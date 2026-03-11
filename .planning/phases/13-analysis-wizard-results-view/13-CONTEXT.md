# Phase 13: Analysis Wizard + Results View - Context

**Gathered:** 2026-03-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can run the full AI tender analysis through a guided 5-step wizard and explore results with filtering, detail expansion, and Excel export. The wizard lives within project context and connects to the existing Python analysis backend via SSE/polling. Feedback/correction on matches, dashboard widgets, and catalog management belong to other phases.

</domain>

<decisions>
## Implementation Decisions

### Wizard Flow & Navigation
- Horizontal numbered stepper at top: 5 circles connected by lines (1-Dateien, 2-Katalog, 3-Konfiguration, 4-Analyse, 5-Ergebnisse)
- Current step highlighted in FTAG Red, completed steps show checkmark
- Real-time validation: Weiter button disabled until step is valid, inline field errors as user interacts
- Free navigation back to completed steps via clicking step circles
- Route: `/projekte/[id]/analyse` — wizard lives under project context
- Step 1 pre-selects files already uploaded to the project
- Mobile: compact stepper — only current step number/name with small dots for other steps

### Progress Display (Step 4)
- Progress shown inline in wizard step 4 — stepper remains visible
- Full-width progress bar with stage checklist below:
  - Stages: Dokument lesen, Anforderungen extrahieren, Produkte zuordnen, Ergebnis generieren
  - Each stage: checkmark when done, dot when pending, filled circle when active
  - Counter shown (e.g., "Produkte zuordnen (3/8)")
- Zurueck button disabled during analysis
- Cancel button ("Analyse abbrechen") with confirmation dialog sends cancel signal to Python backend
- On failure: navigate back to step 3 (configuration) with error toast
- On success: auto-advance to step 5 after brief "Analyse abgeschlossen" message (1-2 seconds)

### Results Table (Step 5)
- 6 columns: Nr | Anforderung | Position | Zugeordnetes Produkt | Artikelnr | Konfidenz
- Confidence shown as colored badge: green (>= 90%), yellow (70-89%), red (< 70% or Gap)
- Default thresholds: 90/70 split — user can adjust in wizard step 3
- Filter bar above table: text search input + confidence dropdown (Alle/Hoch/Mittel/Niedrig/Gap)
- Filter summary chips showing count per confidence level
- Sortable columns via clickable column headers
- Excel download button ("Excel herunterladen") top-right of results view, always visible
- Downloads full 4-sheet Excel file identical to v1.0 format

### Detail Expansion
- Inline accordion: clicking a row expands detail section below, pushing other rows down
- Expanded detail shows:
  1. AI-Begruendung (AI reasoning text)
  2. 6-dimension confidence breakdown as horizontal progress bars (colored green/yellow/red per value):
     - Tuertyp, Material, Brandschutz, Masse, Ausfuehrung, Zubehoer
  3. Two-column comparison card: Anforderung (left) vs Produkt (right)
     - Matching fields aligned on same row
     - Match indicator per row: checkmark (match), warning (mismatch)
- For Gap rows (no product match): show AI explanation + 2-3 closest rejected products with rejection reason
- Click row again to collapse

### Claude's Discretion
- Exact wizard transition animations
- Step 3 configuration layout (threshold sliders, validation pass count)
- Step 1 file selection UI (checkboxes on existing files vs re-upload)
- Step 2 catalog selection UI (dropdown vs card picker)
- Table pagination strategy (virtual scroll vs pagination vs load-all)
- Comparison card field mapping logic (how to align requirement fields to product fields)
- shadcn/ui component additions needed (Table, Tabs, Progress, Badge, Collapsible, etc.)

</decisions>

<specifics>
## Specific Ideas

- Wizard should feel like a checkout flow — clear, guided, no confusion about what comes next
- Progress display during analysis should show the user "something is happening" at all times — no frozen states
- The comparison view is key for the customer: they need to see at a glance whether the AI matched correctly
- Gap rows are important — the customer needs to understand WHY no match was found, not just that there is a gap

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/src/lib/sse-client.ts`: SSE connection with 3-retry + polling fallback already implemented — use directly for step 4 progress
- `frontend/src/components/upload/file-dropzone.tsx`: FileDropzone with Vercel Blob upload — reuse or adapt for step 1
- `frontend/src/components/upload/file-list.tsx`: File list component — reuse for showing project files in step 1
- `frontend/src/components/ui/card.tsx`: shadcn Card component — use for wizard step content containers
- `frontend/src/components/ui/button.tsx`: shadcn Button — use for navigation (Zurueck/Weiter)
- `frontend/src/components/ui/dialog.tsx`: shadcn Dialog — use for cancel confirmation
- `frontend/src/app/(app)/neue-analyse/page.tsx`: Placeholder page with permission check — replace with wizard or redirect to project route

### Established Patterns
- Server components with client component split (page.tsx server + client.tsx client) — Phase 12 pattern
- Server Actions for data mutations (project-actions.ts, file-actions.ts)
- Permission check via `auth.api.userHasPermission` with `analysis: ["create"]` — already in neue-analyse page
- German language throughout UI (labels, errors, toasts)
- shadcn/ui v4 with Tailwind CSS 4 for all components

### Integration Points
- Python backend: POST /api/analyze (start job), GET /api/analyze/status/{job_id} (poll), GET /api/analyze/stream/{job_id} (SSE)
- BFF proxy: /api/backend/[...path] forwards to Python with 300s timeout for analysis endpoints
- SSE token: /api/backend/sse-token issues short-lived token for direct Python SSE connection
- Prisma models: Project, ProjectFile — step 1 reads project files from DB
- Result generator: backend/services/result_generator.py creates Excel with 4-sheet format

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 13-analysis-wizard-results-view*
*Context gathered: 2026-03-11*
