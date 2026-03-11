# Phase 13: Analysis Wizard + Results View - Research

**Researched:** 2026-03-11
**Domain:** Multi-step wizard UI, SSE real-time progress, results table with detail expansion, Excel export
**Confidence:** HIGH

## Summary

Phase 13 connects the existing Next.js frontend to the Python analysis backend through a 5-step wizard. The key integration points are already built: the SSE client (`sse-client.ts`), the BFF proxy (`/api/backend/[...path]`), the Python analysis endpoints (`POST /api/analyze/project`, `GET /api/analyze/status/{job_id}`, `GET /api/analyze/stream/{job_id}`), and the result generator (`POST /api/result/generate`, `GET /api/result/{id}/download`). The Prisma `Analysis` model exists with a `result: Json?` field for storing analysis results.

The wizard is primarily a frontend composition task using existing shadcn/ui components plus a few new ones (Progress, Table, Collapsible, Badge, Slider). The backend already returns all data needed: each match entry includes `confidence` (0-1), `status` (matched/partial/unmatched), `gap_items`, `matched_products`, `original_position`, `category`, and `reason`. The 6-dimension confidence breakdown referenced in CONTEXT.md maps to the scoring dimensions in `fast_matcher.py` (Brandschutz, Schallschutz, Einbruchschutz, Masse/Dimensions, Tuertyp/Ausfuehrung, Zubehoer).

**Primary recommendation:** Build the wizard as a single client component with internal step state at route `/projekte/[id]/analyse`. Reuse the existing `connectToAnalysis` SSE function for step 4 progress. Store analysis results in the Prisma `Analysis.result` JSON field so results persist across page reloads. For Excel download, call the existing `/api/result/generate` + `/api/result/{id}/download` endpoints through the BFF proxy.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Horizontal numbered stepper at top: 5 circles connected by lines (1-Dateien, 2-Katalog, 3-Konfiguration, 4-Analyse, 5-Ergebnisse)
- Current step highlighted in FTAG Red, completed steps show checkmark
- Real-time validation: Weiter button disabled until step is valid, inline field errors as user interacts
- Free navigation back to completed steps via clicking step circles
- Route: `/projekte/[id]/analyse` -- wizard lives under project context
- Step 1 pre-selects files already uploaded to the project
- Mobile: compact stepper -- only current step number/name with small dots for other steps
- Progress shown inline in wizard step 4 -- stepper remains visible
- Full-width progress bar with stage checklist below (4 stages: Dokument lesen, Anforderungen extrahieren, Produkte zuordnen, Ergebnis generieren)
- Each stage: checkmark when done, dot when pending, filled circle when active
- Counter shown (e.g., "Produkte zuordnen (3/8)")
- Zurueck button disabled during analysis; Cancel button with confirmation dialog
- On failure: navigate back to step 3 with error toast; On success: auto-advance to step 5
- Results table: 6 columns (Nr | Anforderung | Position | Zugeordnetes Produkt | Artikelnr | Konfidenz)
- Confidence badge colors: green (>= 90%), yellow (70-89%), red (< 70% or Gap)
- Default thresholds: 90/70 split -- user can adjust in wizard step 3
- Filter bar: text search + confidence dropdown (Alle/Hoch/Mittel/Niedrig/Gap)
- Filter summary chips showing count per confidence level
- Sortable columns via clickable column headers
- Excel download button top-right, always visible, downloads full 4-sheet Excel
- Inline accordion for detail expansion: AI reasoning, 6-dimension bars, two-column comparison
- For Gap rows: AI explanation + 2-3 closest rejected products with rejection reason

### Claude's Discretion
- Exact wizard transition animations
- Step 3 configuration layout (threshold sliders, validation pass count)
- Step 1 file selection UI (checkboxes on existing files vs re-upload)
- Step 2 catalog selection UI (dropdown vs card picker)
- Table pagination strategy (virtual scroll vs pagination vs load-all)
- Comparison card field mapping logic
- shadcn/ui component additions needed

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ANLZ-02 | Schritt 2 -- Produktkatalog auswaehlen oder neu hochladen | Step 2 of wizard; Python `GET /api/products` returns catalog info; catalog selection stored as wizard state |
| ANLZ-03 | Schritt 3 -- Schwellenwerte und Validierungsdurchlaeufe konfigurieren | Step 3 of wizard; thresholds are client-side config passed to results view for color coding; validation passes could trigger multiple analysis rounds |
| ANLZ-04 | Schritt 4 -- Analyse starten mit Echtzeit-Fortschrittsbalken (SSE direkt zu Python) | Existing `connectToAnalysis` SSE client + Python SSE stream endpoint; job_store progress messages map to stage checklist |
| ANLZ-05 | Schritt 5 -- Ergebnis-Ansicht mit Tabs (Matches/Gaps/Zusammenfassung) | CONTEXT.md decided on single table with filter instead of tabs; matching result data has matched/partial/unmatched arrays |
| RSLT-01 | Tabellarische Darstellung aller Anforderungen mit Filter und Sortierung | Client-side table with sorting + filtering; data from `matching.matched + partial + unmatched` arrays |
| RSLT-02 | Aufklappbare Detail-Ansicht pro Anforderung (AI-Begruendung, Dimensionen) | Each entry has `reason`, `gap_items`, `matched_products`, `original_position`; 6-dimension breakdown derived from scoring |
| RSLT-03 | Vergleichsansicht: Anforderung links vs. Produkt rechts | `original_position` (requirement) vs `matched_products[0]` (product) side-by-side |
| RSLT-04 | Excel-Export (vollstaendige Ergebnis-Excel wie v1.0) | `POST /api/result/generate` + `GET /api/result/{id}/download` via BFF proxy |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Next.js | 16.1.6 | App Router, server/client components | Already installed, project standard |
| React | 19.2.3 | UI rendering | Already installed |
| shadcn/ui | v4 | Component library (Tailwind 4) | Project standard, CLI available |
| Tailwind CSS | 4.x | Styling | Project standard, CSS-first @theme |
| Prisma | 7.4.2 | Database ORM | Already installed, Analysis model exists |
| lucide-react | 0.577 | Icons | Already installed |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| sonner | 2.0.7 | Toast notifications | Error/success toasts (already installed) |

### shadcn/ui Components to Add
| Component | Purpose | Install Command |
|-----------|---------|----------------|
| progress | Progress bar for step 4 | `npx shadcn@latest add progress` |
| table | Results table in step 5 | `npx shadcn@latest add table` |
| collapsible | Expandable detail rows | `npx shadcn@latest add collapsible` |
| badge | Confidence level badges | `npx shadcn@latest add badge` |
| slider | Threshold configuration in step 3 | `npx shadcn@latest add slider` |
| select | Dropdown filters, catalog selection | `npx shadcn@latest add select` |
| checkbox | File selection in step 1 | `npx shadcn@latest add checkbox` |
| separator | Visual dividers between sections | `npx shadcn@latest add separator` |

**Installation:**
```bash
cd frontend && npx shadcn@latest add progress table collapsible badge slider select checkbox separator
```

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom table | @tanstack/react-table | Adds dependency; plain HTML table + sorting state is sufficient for < 200 rows |
| Virtual scroll | react-window | Only needed if > 500 rows; typical analysis has 20-100 positions |
| Custom stepper | Existing library | No good shadcn stepper exists; custom stepper is simple (5 circles + lines) |

## Architecture Patterns

### Recommended Project Structure
```
frontend/src/
├── app/(app)/projekte/[id]/analyse/
│   ├── page.tsx                    # Server component: auth, project data fetch
│   └── client.tsx                  # Client component: wizard state machine
├── components/analysis/
│   ├── wizard-stepper.tsx          # Horizontal 5-step stepper
│   ├── step-files.tsx              # Step 1: file selection
│   ├── step-catalog.tsx            # Step 2: catalog selection
│   ├── step-config.tsx             # Step 3: threshold configuration
│   ├── step-progress.tsx           # Step 4: analysis progress
│   ├── step-results.tsx            # Step 5: results table + filters
│   ├── result-detail.tsx           # Expandable detail (accordion content)
│   ├── confidence-badge.tsx        # Green/yellow/red badge
│   ├── dimension-bars.tsx          # 6-dimension horizontal bars
│   └── comparison-card.tsx         # Side-by-side requirement vs product
├── lib/actions/
│   └── analysis-actions.ts         # Server Actions: create/update Analysis record
```

### Pattern 1: Wizard State Machine
**What:** Single client component manages step navigation, validation, and data flow between steps.
**When to use:** Multi-step forms where steps share data.
**Example:**
```typescript
// Wizard state managed with useReducer for predictable transitions
type WizardState = {
  currentStep: number; // 1-5
  completedSteps: Set<number>;
  selectedFileIds: string[];
  catalogId: string | null;
  config: { highThreshold: number; lowThreshold: number; validationPasses: number };
  jobId: string | null;
  analysisResult: AnalysisResult | null;
};

type WizardAction =
  | { type: 'NEXT_STEP' }
  | { type: 'PREV_STEP' }
  | { type: 'GO_TO_STEP'; step: number }
  | { type: 'SET_FILES'; fileIds: string[] }
  | { type: 'SET_CATALOG'; catalogId: string }
  | { type: 'SET_CONFIG'; config: WizardState['config'] }
  | { type: 'SET_JOB'; jobId: string }
  | { type: 'SET_RESULT'; result: AnalysisResult }
  | { type: 'ANALYSIS_FAILED' };
```

### Pattern 2: Server Component + Client Component Split
**What:** page.tsx (server) fetches project data + auth, passes to client.tsx (client) for interactivity.
**When to use:** All new pages (established Phase 12 pattern).
**Example:**
```typescript
// page.tsx (server)
export default async function AnalysePage({ params }: { params: Promise<{ id: string }> }) {
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session) redirect('/auth/login');
  const { id } = await params;

  const project = await prisma.project.findUnique({
    where: { id },
    include: { files: true },
  });
  if (!project) notFound();

  return <AnalyseWizardClient project={project} />;
}
```

### Pattern 3: SSE Progress Mapping
**What:** Map Python job progress strings to structured stage progress for the UI.
**When to use:** Step 4 progress display.
**Example:**
```typescript
// Map backend progress text to structured stages
const STAGES = [
  { key: 'parse', label: 'Dokument lesen', pattern: /Excel-Türlisten|PDF-Spezifikationen|Dokumente werden/ },
  { key: 'extract', label: 'Anforderungen extrahieren', pattern: /Projektmetadaten|KI analysiert|Anforderungen/ },
  { key: 'match', label: 'Produkte zuordnen', pattern: /Matching|Positionen|Dedupliziert/ },
  { key: 'generate', label: 'Ergebnis generieren', pattern: /Ergebnisse werden|Fertig/ },
];

function mapProgressToStage(progressText: string): { activeStage: number; counter?: string } {
  for (let i = STAGES.length - 1; i >= 0; i--) {
    if (STAGES[i].pattern.test(progressText)) {
      // Extract counter like "3/8" from progress text
      const counterMatch = progressText.match(/(\d+)\/(\d+)/);
      return { activeStage: i, counter: counterMatch?.[0] };
    }
  }
  return { activeStage: 0 };
}
```

### Pattern 4: Analysis Result Persistence
**What:** Save analysis result to Prisma `Analysis.result` (JSON field) so results survive page reloads.
**When to use:** When analysis completes successfully in step 4.
**Example:**
```typescript
// Server Action: save analysis result
'use server';
export async function saveAnalysisResult(projectId: string, jobResult: unknown) {
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session) throw new Error('Nicht authentifiziert');

  const analysis = await prisma.analysis.create({
    data: {
      projectId,
      status: 'completed',
      result: jobResult as Prisma.JsonValue,
      startedAt: new Date(),
      endedAt: new Date(),
      startedBy: session.user.id,
    },
  });

  revalidatePath(`/projekte/${projectId}`);
  return analysis.id;
}
```

### Anti-Patterns to Avoid
- **Don't store wizard state in URL params:** Too complex for 5 steps of data; use React state (useReducer). URL only needs the project ID.
- **Don't call Python backend directly from browser for non-SSE requests:** Always go through BFF proxy. Only SSE uses direct connection (with token auth).
- **Don't build custom progress bar from scratch:** Use shadcn Progress component with dynamic value.
- **Don't fetch full analysis result on every poll:** The SSE/polling only returns progress text during analysis. The full result comes once at status=completed.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Horizontal stepper | Complex stepper with animation library | Simple CSS circles + connecting lines | Only 5 fixed steps; pure Tailwind is simpler than any library |
| Progress bar | Custom animated bar | shadcn Progress component | Handles accessibility, animation built-in |
| Table sorting | Custom sort implementation | Simple `Array.sort()` + state | < 200 rows, no need for virtualization |
| Excel generation | Frontend Excel builder | Existing Python `result_generator.py` via BFF | Already produces the exact 4-sheet format needed |
| SSE connection | New EventSource wrapper | Existing `connectToAnalysis()` in `sse-client.ts` | Already handles retry + polling fallback |

## Common Pitfalls

### Pitfall 1: SSE Progress Text Parsing Fragility
**What goes wrong:** Python progress messages change format, breaking stage mapping.
**Why it happens:** Progress text is free-form strings from `update_job(job_id, progress="...")`.
**How to avoid:** Use regex patterns that match keywords (not exact strings). Fall back to "active" stage 0 for unrecognized messages. Log unmatched progress texts.
**Warning signs:** Progress bar stuck on first stage despite analysis running.

### Pitfall 2: Race Condition Between Analysis Complete and Result Save
**What goes wrong:** User sees "completed" before result is saved to Prisma.
**Why it happens:** SSE delivers completion event before the Server Action finishes writing to DB.
**How to avoid:** In the SSE onEvent handler: when status=completed, call saveAnalysisResult and only advance to step 5 after the save resolves.
**Warning signs:** Step 5 loads but shows empty results.

### Pitfall 3: Large Analysis Result in JSON Column
**What goes wrong:** Analysis result with 100+ positions and full product details exceeds reasonable JSON size.
**Why it happens:** Each match entry includes full `matched_products` array with product details.
**How to avoid:** Store the full result but only load summary for the table view. Use Prisma `select` to fetch only needed fields. The `result` JSON field in Postgres supports up to 1GB.
**Warning signs:** Slow page loads for projects with many positions.

### Pitfall 4: Confidence Threshold Mismatch
**What goes wrong:** Backend uses `confidence: 0.85` (0-1 scale) but UI shows percentages (85%).
**Why it happens:** Backend `fast_matcher.py` returns `confidence: round(score / 100, 2)` -- already 0-1 scale.
**How to avoid:** Always multiply by 100 for display. Threshold comparison: `confidence * 100 >= highThreshold`.
**Warning signs:** All items showing as "low confidence" despite good matches.

### Pitfall 5: File Selection Stale After Upload
**What goes wrong:** Step 1 shows old file list if user uploaded files during wizard.
**Why it happens:** Server component data is static after initial load.
**How to avoid:** Option A: Pass files as prop, user must exit wizard to upload. Option B: Add refresh mechanism. Recommend Option A for simplicity -- wizard starts after files are ready.
**Warning signs:** Recently uploaded files missing from step 1.

### Pitfall 6: Missing 6-Dimension Breakdown Data
**What goes wrong:** The CONTEXT.md specifies 6-dimension confidence bars (Tuertyp, Material, Brandschutz, Masse, Ausfuehrung, Zubehoer) but the backend doesn't return per-dimension scores.
**Why it happens:** `fast_matcher.py` computes a single aggregate score, not per-dimension breakdowns.
**How to avoid:** Either (a) derive approximate dimension scores from `gap_items` and `missing_info` fields (if a gap mentions "Brandschutz", that dimension is low), or (b) add a lightweight per-dimension score output to fast_matcher. Recommend option (a) for phase 13 to avoid backend changes.
**Warning signs:** All 6 bars showing the same value.

## Code Examples

### Backend Data Shape (from fast_matcher.py)
```typescript
// TypeScript interface matching the Python return value
interface MatchEntry {
  status: 'matched' | 'partial' | 'unmatched';
  confidence: number; // 0-1 scale (e.g., 0.85 = 85%)
  position: string; // Door number / position ID
  beschreibung: string; // Door type description
  menge: number;
  einheit: string;
  matched_products: ProductDetail[]; // Best match + alternatives
  gap_items: string[]; // Human-readable gap explanations
  missing_info: { feld: string; benoetigt: string; vorhanden: string }[];
  reason: string; // Compact product text or "Kein passendes Produkt"
  original_position: Record<string, unknown>; // Raw parsed door data
  category: string; // Product category used for matching
}

interface AnalysisResult {
  matched: MatchEntry[];
  partial: MatchEntry[];
  unmatched: MatchEntry[];
  summary: {
    total_positions: number;
    matched_count: number;
    partial_count: number;
    unmatched_count: number;
    match_rate: number; // Percentage (e.g., 85.7)
  };
}
```

### Confidence Badge Component
```typescript
// Source: CONTEXT.md decision on color thresholds
function ConfidenceBadge({ confidence, highThreshold = 90, lowThreshold = 70 }: {
  confidence: number; // 0-1
  highThreshold?: number;
  lowThreshold?: number;
}) {
  const pct = Math.round(confidence * 100);
  const level = pct >= highThreshold ? 'high' : pct >= lowThreshold ? 'medium' : 'low';
  const styles = {
    high: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
    medium: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
    low: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
  };
  return <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${styles[level]}`}>{pct}%</span>;
}
```

### Deriving 6-Dimension Scores from Gap Data
```typescript
// Approximate per-dimension confidence from gap_items + missing_info
const DIMENSION_PATTERNS: Record<string, RegExp> = {
  tuertyp: /Türtyp|tuertyp|Kategorie/i,
  material: /Material|Oberfläche|oberflaeche/i,
  brandschutz: /Brandschutz|EI\d+|Feuer/i,
  masse: /Masse|Dimension|Breite|Höhe|Lichtmass|zu gross|zu klein/i,
  ausfuehrung: /Ausführung|Flügel|Verglasung|fluegel/i,
  zubehoer: /Zubehör|Schloss|Band|Beschlag|zubehoer/i,
};

function deriveDimensionScores(entry: MatchEntry): Record<string, number> {
  const scores: Record<string, number> = {};
  const baseScore = entry.confidence * 100;

  for (const [dim, pattern] of Object.entries(DIMENSION_PATTERNS)) {
    const hasGap = entry.gap_items.some(g => pattern.test(g)) ||
                   entry.missing_info.some(m => pattern.test(m.feld));
    scores[dim] = hasGap ? Math.min(baseScore * 0.4, 40) : Math.min(baseScore * 1.1, 100);
  }
  return scores;
}
```

### Excel Download Flow
```typescript
// Step 5: Download Excel via BFF proxy
async function downloadExcel(requirements: unknown, matching: unknown) {
  // Step 1: Trigger generation
  const genRes = await fetch('/api/backend/result/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ requirements, matching }),
  });
  const { job_id } = await genRes.json();

  // Step 2: Poll for completion
  let result;
  while (true) {
    const statusRes = await fetch(`/api/backend/result/status/${job_id}`);
    const status = await statusRes.json();
    if (status.status === 'completed') { result = status.result; break; }
    if (status.status === 'failed') throw new Error(status.error);
    await new Promise(r => setTimeout(r, 1000));
  }

  // Step 3: Download file
  const downloadRes = await fetch(`/api/backend/result/${result.result_id}/download`);
  const blob = await downloadRes.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `FTAG_Machbarkeit.xlsx`;
  a.click();
  URL.revokeObjectURL(url);
}
```

### Starting Analysis via BFF Proxy
```typescript
// The analysis is triggered through the BFF proxy, not directly to Python
// For project analysis (multiple files):
async function startAnalysis(projectId: string, fileOverrides: Record<string, string> = {}) {
  const response = await fetch('/api/backend/analyze/project', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ project_id: projectId, file_overrides: fileOverrides }),
  });
  if (!response.ok) throw new Error('Analyse konnte nicht gestartet werden');
  const { job_id } = await response.json();
  return job_id;
}

// Then connect SSE for real-time progress:
const { close } = await connectToAnalysis(jobId, onEvent, onError);
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| v1.0 single-page app | Next.js App Router v2.0 | Phase 10 | Server components, proper routing |
| Direct Python API calls | BFF proxy pattern | Phase 11 | Auth handled server-side, 300s timeout for analysis |
| Polling only | SSE with polling fallback | Phase 11 | Real-time progress updates |
| No data persistence | Prisma Analysis model | Phase 12 | Results survive page reload |

## Open Questions

1. **Backend File Caching for Analysis**
   - What we know: Python `analyze/project` expects files in `project_cache` (in-memory). Files are uploaded to Vercel Blob, not to Python.
   - What's unclear: How do files get from Vercel Blob to Python's memory cache before analysis starts? The v1 flow uploaded directly to Python.
   - Recommendation: Add a pre-analysis step where the BFF downloads files from Vercel Blob URLs and POSTs them to a Python "prepare" endpoint that caches them. Or modify the Python backend to accept Blob URLs and download files itself. This is a critical integration gap that needs a plan task.

2. **Catalog Selection (Step 2)**
   - What we know: v1.0 uses a single hardcoded catalog (`data/produktuebersicht.xlsx`). ANLZ-02 says "Produktkatalog auswaehlen oder neu hochladen."
   - What's unclear: Are there multiple catalogs? Catalog management is Phase 14 (KAT-01 through KAT-04).
   - Recommendation: For Phase 13, show the default catalog as pre-selected with info card. Add a "Katalog hochladen" option that stores it as a project file. Full catalog management deferred to Phase 14.

3. **Validation Passes Configuration (Step 3)**
   - What we know: CONTEXT.md mentions "validation pass count" in step 3 configuration.
   - What's unclear: The backend `fast_matcher.py` doesn't support multiple validation passes. This would require backend changes.
   - Recommendation: Include the UI control in step 3 but default to 1 pass. Mark multi-pass as "coming soon" or implement as re-running the analysis with adjusted thresholds.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Vitest 4.0.18 |
| Config file | `frontend/vitest.config.ts` (needs verification) |
| Quick run command | `cd frontend && npx vitest run --reporter=verbose` |
| Full suite command | `cd frontend && npx vitest run` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ANLZ-02 | Catalog selection step renders and validates | unit | `cd frontend && npx vitest run src/components/analysis/step-catalog.test.tsx -x` | Wave 0 |
| ANLZ-03 | Config step sliders set thresholds correctly | unit | `cd frontend && npx vitest run src/components/analysis/step-config.test.tsx -x` | Wave 0 |
| ANLZ-04 | Progress display maps SSE events to stages | unit | `cd frontend && npx vitest run src/components/analysis/step-progress.test.tsx -x` | Wave 0 |
| ANLZ-05 | Results view renders table with all entries | unit | `cd frontend && npx vitest run src/components/analysis/step-results.test.tsx -x` | Wave 0 |
| RSLT-01 | Table sorting and filtering works correctly | unit | `cd frontend && npx vitest run src/components/analysis/step-results.test.tsx -x` | Wave 0 |
| RSLT-02 | Detail expansion shows reasoning and dimensions | unit | `cd frontend && npx vitest run src/components/analysis/result-detail.test.tsx -x` | Wave 0 |
| RSLT-03 | Comparison card aligns requirement vs product fields | unit | `cd frontend && npx vitest run src/components/analysis/comparison-card.test.tsx -x` | Wave 0 |
| RSLT-04 | Excel download triggers correct API sequence | unit | `cd frontend && npx vitest run src/components/analysis/step-results.test.tsx -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd frontend && npx vitest run --reporter=verbose`
- **Per wave merge:** `cd frontend && npx vitest run`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `frontend/src/components/analysis/step-catalog.test.tsx` -- covers ANLZ-02
- [ ] `frontend/src/components/analysis/step-config.test.tsx` -- covers ANLZ-03
- [ ] `frontend/src/components/analysis/step-progress.test.tsx` -- covers ANLZ-04
- [ ] `frontend/src/components/analysis/step-results.test.tsx` -- covers ANLZ-05, RSLT-01, RSLT-04
- [ ] `frontend/src/components/analysis/result-detail.test.tsx` -- covers RSLT-02
- [ ] `frontend/src/components/analysis/comparison-card.test.tsx` -- covers RSLT-03

## Sources

### Primary (HIGH confidence)
- `backend/services/fast_matcher.py` -- match result data structure (lines 661-704)
- `backend/services/job_store.py` -- Job model, SSE subscription, progress updates
- `backend/routers/analyze.py` -- Analysis endpoints, SSE stream, project analysis flow
- `backend/routers/offer.py` -- Result generation and download endpoints
- `backend/services/result_generator.py` -- Excel generation (2-sheet format)
- `frontend/src/lib/sse-client.ts` -- Existing SSE client with retry + polling
- `frontend/src/app/api/backend/[...path]/route.ts` -- BFF proxy with 300s timeout
- `frontend/prisma/schema.prisma` -- Analysis model with JSON result field
- `frontend/src/app/(app)/projekte/[id]/page.tsx` -- Project detail server component pattern
- `frontend/src/app/(app)/projekte/[id]/client.tsx` -- Project detail client component pattern

### Secondary (MEDIUM confidence)
- shadcn/ui v4 component API -- based on project's existing usage patterns

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already installed and in use
- Architecture: HIGH -- follows established Phase 12 patterns, data shapes verified from source code
- Pitfalls: HIGH -- derived from direct code analysis of integration points
- Backend data shape: HIGH -- verified from fast_matcher.py source code
- 6-dimension breakdown: MEDIUM -- requires derivation from gap_items, not directly provided by backend

**Research date:** 2026-03-11
**Valid until:** 2026-04-11 (stable stack, no external dependencies changing)
