# Phase 18: Fix Cross-Phase Integration Gaps - Research

**Researched:** 2026-03-11
**Domain:** Next.js / FastAPI cross-phase wiring (catalog selection, routing, auth redirects)
**Confidence:** HIGH

## Summary

Phase 18 addresses three specific integration gaps identified in the v2.0 re-audit. All three are well-scoped, narrow fixes -- no new features, no new libraries, no architectural changes. The codebase is fully understood from direct source inspection.

**Gap 1 (ANLZ-02):** The wizard's `handleStartAnalysis` in `client.tsx` sends `project_id` to `/api/analyze/project` but does NOT send `state.catalogId`. The Python `AnalyzeProjectRequest` model has no `catalog_id` field. The `fast_matcher.py::match_all()` and `catalog_index.py::get_catalog_index()` always load from the hardcoded `data/produktuebersicht.xlsx` file path. The fix requires: (a) adding `catalog_id` to the request body, (b) extending Python to accept it and load the appropriate catalog, and (c) connecting to the `CatalogVersion.blobUrl` stored in Prisma.

**Gap 2 (DASH-04):** The dashboard "Neue Analyse starten" button links to `/neue-analyse`, which currently shows a placeholder ("Analyse-Wizard wird in Phase 13 implementiert"). The actual wizard lives at `/projekte/[id]/analyse`. The fix must either redirect `/neue-analyse` to `/projekte` with analysis intent, or render a project picker on the `/neue-analyse` page itself.

**Gap 3 (AUTH-05):** Three project pages use `redirect('/auth/login')` instead of the correct `redirect('/login')`. The login page lives at `(auth)/login/page.tsx` which maps to `/login`. The `(app)/layout.tsx` and `proxy.ts` already use the correct `/login` path. Only `projekte/page.tsx`, `projekte/[id]/page.tsx`, and `projekte/[id]/analyse/page.tsx` have the wrong path.

**Primary recommendation:** Three independent, small fixes. Each can be a separate plan task. No new dependencies needed.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ANLZ-02 | Schritt 2 -- Produktkatalog auswaehlen oder neu hochladen | Catalog selection UI exists (StepCatalog). Gap is forwarding catalogId to Python and having Python use the specified catalog for matching. |
| DASH-04 | Schnellzugriff-Button "Neue Analyse starten" | Button exists on dashboard, links to `/neue-analyse`. Gap is that `/neue-analyse` page is a placeholder instead of routing to the wizard. |
| AUTH-05 | Routen und API-Endpoints sind rollenbasiert geschuetzt | Role-based protection exists. Gap is 3 pages using wrong redirect path `/auth/login` instead of `/login`. |
</phase_requirements>

## Standard Stack

No new libraries needed. All fixes use existing stack:

### Core (already installed)
| Library | Purpose | Relevance |
|---------|---------|-----------|
| Next.js 16 (App Router) | Frontend framework | Routing, redirects, server components |
| FastAPI | Python backend | API endpoint changes |
| Prisma 7 | Database ORM | Catalog version lookup (blobUrl) |
| Better Auth | Authentication | Session checks, permission checks |

### No New Dependencies
This phase adds zero new packages. All fixes are wiring changes within existing code.

## Architecture Patterns

### Current Data Flow (Analysis)
```
Dashboard "Neue Analyse" button
  -> /neue-analyse (BROKEN: placeholder page)

Wizard Step 2 (StepCatalog)
  -> user selects catalogId
  -> state.catalogId is set

Wizard Step 3 -> handleStartAnalysis()
  -> prepareFilesForPython(projectId, fileIds)  [server action]
  -> createAnalysis(projectId)                   [server action]
  -> fetch('/api/backend/analyze/project', { project_id })  [BFF proxy]
  -> Python /api/analyze/project                  [NO catalogId sent]
  -> fast_match_all(positions)                    [hardcoded catalog]
```

### Required Data Flow (After Fix)
```
Dashboard "Neue Analyse" button
  -> /projekte (with analysis intent, or project picker on /neue-analyse)

Wizard Step 3 -> handleStartAnalysis()
  -> fetch('/api/backend/analyze/project', { project_id, catalog_id })
  -> Python /api/analyze/project receives catalog_id
  -> Downloads catalog from blob URL (or uses default if none specified)
  -> fast_match_all(positions) uses specified catalog
```

### Files That Need Changes

**Gap 1 (ANLZ-02 - Catalog forwarding):**
1. `frontend/src/app/(app)/projekte/[id]/analyse/client.tsx` -- add `catalog_id` to fetch body (line 215)
2. `backend/routers/analyze.py` -- add `catalog_id: Optional[str] = None` to `AnalyzeProjectRequest`, pass to `_run_project_analysis`
3. `backend/services/catalog_index.py` -- add function to load catalog from blob URL or file path
4. `backend/services/fast_matcher.py` -- accept optional catalog index parameter in `match_all()`

**Gap 2 (DASH-04 - Neue Analyse routing):**
1. `frontend/src/app/(app)/neue-analyse/page.tsx` -- replace placeholder with project picker or redirect
2. `frontend/src/lib/hooks/use-keyboard-shortcuts.ts` -- update shortcut target (currently `/neue-analyse`)
3. `frontend/src/components/layout/sidebar.tsx` -- update nav item href (currently `/neue-analyse`)

**Gap 3 (AUTH-05 - Login redirect path):**
1. `frontend/src/app/(app)/projekte/page.tsx` -- line 16: change `/auth/login` to `/login`
2. `frontend/src/app/(app)/projekte/[id]/page.tsx` -- line 15: change `/auth/login` to `/login`
3. `frontend/src/app/(app)/projekte/[id]/analyse/page.tsx` -- line 17: change `/auth/login` to `/login`

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Catalog file download | Custom HTTP client | `httpx` (already used in `catalog.py`) | Already has `_download_blob()` helper in `backend/routers/catalog.py` |
| Project listing for neue-analyse | New API endpoint | Prisma query in server component | Same pattern as `projekte/page.tsx` |
| Catalog cache per request | Per-request catalog loading | `lru_cache` with invalidation | Already patterned in `catalog_index.py` |

## Common Pitfalls

### Pitfall 1: Catalog Index Cache Invalidation
**What goes wrong:** `get_catalog_index()` uses `@lru_cache(maxsize=1)` -- it caches a single catalog forever. If we load different catalogs per-request, the cache will return the wrong one.
**Why it happens:** The current design assumes a single global catalog.
**How to avoid:** For per-catalog loading, either: (a) bypass the cache and load directly, (b) use a dict-keyed cache by catalog_id, or (c) accept the default catalog for `None` and only download+parse for non-default catalogs.
**Recommended approach:** Add a `load_catalog_from_bytes(excel_bytes)` function that builds a CatalogIndex without caching. Reserve the cached `get_catalog_index()` for the default catalog. This avoids breaking existing behavior.

### Pitfall 2: Neue Analyse Needs a Project Context
**What goes wrong:** The wizard at `/projekte/[id]/analyse` requires a project ID. A standalone `/neue-analyse` page cannot run the wizard without selecting/creating a project first.
**Why it happens:** The analysis wizard is project-scoped by design (PROJ-02: "Mehrere Analysen pro Projekt mit Historie").
**How to avoid:** The `/neue-analyse` page should redirect to `/projekte` with a search param (e.g., `?intent=analyse`) so the user picks a project, or it should render a simple project picker that links to `/projekte/[id]/analyse`.
**Recommended approach:** Render a project picker (list user's active projects with a "Start Analyse" link to each project's wizard). This gives the user a smooth path from dashboard to analysis.

### Pitfall 3: Auth Redirect Path Mismatch
**What goes wrong:** `redirect('/auth/login')` results in a 404 because no page exists at `/auth/login`. The login page is at `(auth)/login/page.tsx` which maps to URL `/login`.
**Why it happens:** The `(auth)` route group is a Next.js layout group -- the parenthesized segment is not part of the URL.
**How to avoid:** Simple string replacement. Verify by checking all files in `(app)` for `/auth/login` references.

### Pitfall 4: BFF Proxy Body Passthrough
**What goes wrong:** The BFF proxy at `api/backend/[...path]/route.ts` passes the request body as-is to Python. If we add `catalog_id` to the JSON body in the client fetch, it will automatically pass through.
**Why it happens:** The proxy uses `request.arrayBuffer()` for the body -- transparent pass-through.
**How to avoid:** No special handling needed. Just add the field to the client-side `JSON.stringify()` call.

## Code Examples

### Fix 1: Forward catalogId in handleStartAnalysis (client.tsx)
```typescript
// In handleStartAnalysis, change the fetch body:
body: JSON.stringify({
  project_id: prepareResult.pythonProjectId,
  catalog_id: state.catalogId,  // NEW: forward selected catalog
}),
```

### Fix 2: Accept catalog_id in Python (analyze.py)
```python
class AnalyzeProjectRequest(BaseModel):
    project_id: str
    catalog_id: Optional[str] = None  # NEW: Prisma catalog ID
    file_overrides: dict = {}
```

### Fix 3: Load catalog from blob URL (catalog_index.py)
```python
def load_catalog_from_blob_url(blob_url: str) -> CatalogIndex:
    """Download catalog Excel from blob URL and build index."""
    import httpx
    response = httpx.get(blob_url, timeout=30.0)
    response.raise_for_status()
    excel_bytes = response.content
    return load_catalog_from_bytes(excel_bytes)

def load_catalog_from_bytes(excel_bytes: bytes) -> CatalogIndex:
    """Build a CatalogIndex from Excel bytes (no caching)."""
    import io
    df = pd.read_excel(io.BytesIO(excel_bytes), sheet_name=0, header=CATALOG_HEADER_ROW)
    # ... same build logic as get_catalog_index() ...
```

### Fix 4: Auth redirect correction
```typescript
// Before (WRONG):
if (!session) redirect('/auth/login');

// After (CORRECT):
if (!session) redirect('/login');
```

### Fix 5: Neue Analyse project picker
```typescript
// frontend/src/app/(app)/neue-analyse/page.tsx
export default async function NeueAnalysePage() {
  // ... auth checks ...
  const projects = await prisma.project.findMany({
    where: { ownerId: userId, status: { not: 'archived' } },
    orderBy: { updatedAt: 'desc' },
  });

  return (
    <div>
      <h1>Neue Analyse starten</h1>
      <p>Waehlen Sie ein Projekt fuer die Analyse:</p>
      {projects.map(p => (
        <Link key={p.id} href={`/projekte/${p.id}/analyse`}>
          {p.name}
        </Link>
      ))}
    </div>
  );
}
```

## State of the Art

No changes in framework versions. All three fixes use existing patterns already established in the codebase:

| Pattern | Established In | Reuse For |
|---------|---------------|-----------|
| Server component auth check + redirect | `(app)/layout.tsx` | Neue Analyse page auth |
| Prisma query in server component | `projekte/page.tsx` | Project picker |
| BFF proxy transparent pass-through | `api/backend/[...path]/route.ts` | catalog_id forwarding |
| `httpx` blob download | `backend/routers/catalog.py` | Catalog file download |

## Open Questions

1. **Should the Python catalog be cached per catalog_id?**
   - What we know: Current `lru_cache(maxsize=1)` caches only the default catalog. Loading from blob URL each time is expensive (~1-2s per analysis start).
   - Recommendation: For v2.0, accept the small latency. Add a simple dict cache keyed by catalog_id if performance is an issue. The default catalog (no catalog_id) still uses the fast `lru_cache`.

2. **Should `/neue-analyse` sidebar link change?**
   - What we know: Sidebar has "Neue Analyse" linking to `/neue-analyse`. Keyboard shortcut `n` also goes there.
   - Recommendation: Keep the `/neue-analyse` route but make it functional (project picker). No need to change sidebar or shortcuts.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Vitest (via frontend/package.json) |
| Config file | `frontend/vitest.config.ts` (expected) |
| Quick run command | `cd frontend && npx vitest run --reporter=verbose` |
| Full suite command | `cd frontend && npx vitest run` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ANLZ-02 | catalogId forwarded to Python in analyze request body | unit | Manual verification (requires running backend) | No - Wave 0 |
| DASH-04 | /neue-analyse renders project picker with links to wizard | unit | `cd frontend && npx vitest run src/__tests__/dashboard/quick-action.test.tsx` | Yes (needs update) |
| AUTH-05 | All project pages redirect to /login (not /auth/login) | unit | `cd frontend && npx vitest run src/__tests__/auth/route-protection.test.ts` | Yes (needs update) |

### Sampling Rate
- **Per task commit:** `cd frontend && npx vitest run --reporter=verbose`
- **Per wave merge:** `cd frontend && npx vitest run`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] Update `src/__tests__/dashboard/quick-action.test.tsx` -- verify neue-analyse page renders project list
- [ ] Update `src/__tests__/auth/route-protection.test.ts` -- verify `/login` (not `/auth/login`) redirects
- [ ] No new test files needed -- existing test files cover the areas being modified

## Sources

### Primary (HIGH confidence)
- Direct source inspection of all files listed in "Files That Need Changes" section
- `frontend/src/app/(app)/projekte/[id]/analyse/client.tsx` -- wizard state management, handleStartAnalysis
- `backend/routers/analyze.py` -- AnalyzeProjectRequest model, _run_project_analysis function
- `backend/services/catalog_index.py` -- get_catalog_index(), CatalogIndex dataclass
- `backend/services/fast_matcher.py` -- match_all() function signature
- `frontend/src/app/(app)/neue-analyse/page.tsx` -- placeholder content
- `frontend/src/app/(auth)/login/page.tsx` -- confirms login route is `/login`
- `frontend/src/app/(app)/layout.tsx` -- confirms correct `/login` redirect pattern

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no new dependencies, all existing code
- Architecture: HIGH - all files inspected directly, exact line numbers identified
- Pitfalls: HIGH - all edge cases identified from source inspection

**Research date:** 2026-03-11
**Valid until:** 2026-04-11 (stable, internal wiring fixes)
