# Phase 14: Catalog Management - Research

**Researched:** 2026-03-11
**Domain:** Full-stack catalog CRUD (Next.js 16 + FastAPI + Prisma 7 + Neon Postgres)
**Confidence:** HIGH

## Summary

Phase 14 implements catalog management for the FTAG product catalog. The project already has a working Python-side catalog system (`catalog_index.py` loads `produktuebersicht.xlsx` with 884 products across 318 columns, builds compact text profiles for AI matching) and a basic catalog router (`routers/catalog.py` with `/catalog/info` and `/catalog/upload` endpoints). The frontend has a placeholder page at `/(app)/katalog/page.tsx` and permissions already defined (`catalog: ["read", "update", "upload"]` for manager/admin roles).

The key challenge is bridging three concerns: (1) storing catalog metadata and version history in Prisma/Postgres (the source of truth for the web platform), (2) keeping the Python backend's in-memory catalog index synchronized when catalogs change, and (3) allowing individual product CRUD without requiring full Excel re-upload. The existing BFF proxy pattern (`/api/backend/[...path]`) handles Next.js-to-Python communication, and Vercel Blob handles file storage.

**Primary recommendation:** Add Prisma models for `Catalog` and `CatalogVersion` in Next.js, store catalog Excel files in Vercel Blob, use server actions for CRUD, and extend the Python catalog router with product-level read/search/edit endpoints that operate on the in-memory index.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| KAT-01 | Kataloge hochladen (Excel/CSV) mit Import-Validierung | Vercel Blob for file storage, Python `/catalog/upload` for validation + index rebuild, Prisma `CatalogVersion` for version tracking |
| KAT-02 | Kataloge durchsuchen und filtern | Python catalog_index already has `by_category`, `get_product_detail()`, `get_product_extended()` -- extend with search/filter endpoint; frontend data table with column filters |
| KAT-03 | Katalog-Versionen verwalten (alt vs. neu) | Prisma `CatalogVersion` model with blob URLs, version diff via Python comparing two DataFrames, rollback = re-activate previous version |
| KAT-04 | Einzelne Produkte bearbeiten/hinzufuegen/loeschen | Store product overrides in Postgres (JSON or dedicated table), apply on top of base Excel catalog, invalidate Python cache after changes |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Next.js | 16.1.6 | App Router, server actions, API routes | Already in use |
| Prisma | 7.4.2 | ORM for Postgres (Neon) | Already in use |
| FastAPI | existing | Python catalog endpoints | Already in use |
| Vercel Blob | 2.3.1 | File storage for catalog Excel/CSV | Already used for tender doc uploads |
| pandas | existing | Excel/CSV parsing and validation | Already in `catalog_index.py` |
| openpyxl | existing | Excel read support for pandas | Already in requirements.txt |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| shadcn/ui (base-ui) | v4 | Data tables, dialogs, forms | All UI components |
| lucide-react | 0.577 | Icons | Catalog UI icons |
| sonner | 2.0.7 | Toast notifications | Upload success/error feedback |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Vercel Blob for catalog files | Store catalogs directly in Postgres as bytea | Blob is already used for uploads; bytea would limit file size and slow queries |
| Product overrides in Postgres | Edit Excel directly on Python side | Excel edits are fragile, no audit trail, no multi-user safety |
| CSV import via Python | Parse CSV in Next.js server action | Python already has pandas + validation logic; keep parsing centralized |

## Architecture Patterns

### Recommended Project Structure
```
frontend/src/
  app/(app)/katalog/
    page.tsx                    # Catalog list + upload (server component)
    [catalogId]/
      page.tsx                  # Catalog detail: product browser
      versions/page.tsx         # Version history + comparison
  lib/actions/
    catalog-actions.ts          # Server actions: CRUD for catalogs + products
  components/catalog/
    catalog-upload.tsx           # Upload dropzone + validation results
    catalog-table.tsx            # Product browser with search/filter
    catalog-version-history.tsx  # Version list with compare/rollback
    product-edit-dialog.tsx      # Add/edit product form
    catalog-stats.tsx            # Summary cards (product count, categories)

backend/routers/
  catalog.py                    # Extended: search, products, versions, diff

frontend/prisma/schema.prisma   # New models: Catalog, CatalogVersion, ProductOverride
```

### Pattern 1: Catalog Upload Flow
**What:** Upload Excel/CSV -> validate in Python -> store in Blob -> record in Prisma
**When to use:** KAT-01
**Example:**
```typescript
// Server action: catalog-actions.ts
'use server';
export async function uploadCatalog(formData: FormData) {
  const session = await auth.api.getSession({ headers: await headers() });
  // 1. Permission check: catalog.upload
  // 2. Upload file to Vercel Blob (get blobUrl)
  // 3. POST to Python /api/catalog/validate with blob URL or file bytes
  //    Python validates: row count, required columns, data types
  // 4. If valid, create CatalogVersion in Prisma
  // 5. POST to Python /api/catalog/activate with version info
  //    Python reloads catalog_index
  // 6. Return validation results to frontend
}
```

### Pattern 2: BFF Proxy for Catalog Data
**What:** Frontend fetches product data through Next.js BFF proxy to Python
**When to use:** KAT-02 (browse/search), KAT-03 (version diff)
**Example:**
```typescript
// Client component fetches via BFF proxy
const res = await fetch('/api/backend/catalog/products?search=Rahmentuere&category=Brandschutz&page=1&limit=50');
```

### Pattern 3: Server Actions for Prisma CRUD
**What:** Use Next.js server actions for Catalog/Version metadata in Prisma
**When to use:** KAT-03 (version management), KAT-04 (product edits)
**Example:**
```typescript
// Server action pattern (matches project-actions.ts)
'use server';
export async function rollbackCatalogVersion(catalogId: string, versionId: string) {
  const session = await auth.api.getSession({ headers: await headers() });
  // Permission check: catalog.update
  // Update Catalog.activeVersionId in Prisma
  // POST to Python /api/catalog/activate to reload
  revalidatePath('/katalog');
}
```

### Pattern 4: Product Override Layer
**What:** Individual product edits stored as overrides in Postgres, merged with base catalog at query time
**When to use:** KAT-04
**Example:**
```
Base catalog (Excel in Blob):  884 products
+ ProductOverride records:     +3 added, 5 modified, 1 deleted
= Effective catalog:           886 products (at query time)
```

### Anti-Patterns to Avoid
- **Editing Excel files directly:** Never modify the uploaded Excel; treat it as immutable. Product edits go to Postgres overlay.
- **Storing catalog data row-by-row in Postgres:** The 318-column FTAG catalog is not relational. Keep Excel as source, use Python pandas for parsing.
- **Bypassing the BFF proxy:** All frontend-to-Python calls must go through `/api/backend/[...path]` for auth injection.
- **Full catalog in frontend state:** 884 products x many fields is too large for client-side state. Use server-side pagination.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Excel validation | Custom cell-by-cell validator | pandas read_excel + schema checks | pandas handles encoding, merged cells, date parsing |
| File storage | Local filesystem in production | Vercel Blob | Already used, handles CDN, signed URLs |
| Data table | Custom table with sorting/filtering | shadcn data table pattern with base-ui | Consistent with existing UI |
| CSV parsing | Custom line splitter | pandas read_csv | Handles quoting, encoding, delimiters |
| Version diff | Custom diff algorithm | pandas DataFrame.compare() | Handles column alignment, type coercion |

**Key insight:** The 318-column FTAG catalog with its complex header structure (row 6 is the header) makes custom parsing extremely fragile. Always delegate to pandas.

## Common Pitfalls

### Pitfall 1: Python Cache Invalidation
**What goes wrong:** Upload new catalog, but Python still serves old data from `lru_cache`
**Why it happens:** `get_catalog_index()` uses `@lru_cache(maxsize=1)`, must be explicitly cleared
**How to avoid:** After any catalog change (upload, rollback, product edit), call `invalidate_catalog_cache()` then `get_catalog_index()` to rebuild
**Warning signs:** Product counts don't match after upload; old products still appearing

### Pitfall 2: FTAG Excel Header Row
**What goes wrong:** Parsing fails or returns garbage because header is at row 6, not row 0
**Why it happens:** FTAG catalog has metadata/logo rows above the actual column headers
**How to avoid:** Always use `header=6` (CATALOG_HEADER_ROW constant) when reading FTAG Excel files. Validation must check that expected columns exist at this row.
**Warning signs:** Column names are like "Unnamed: 0", "Unnamed: 1"

### Pitfall 3: Vercel Blob URL Expiration
**What goes wrong:** Stored blob URLs stop working after some time
**Why it happens:** Vercel Blob URLs are permanent by default (not signed URLs), but if using client upload tokens they expire
**How to avoid:** For catalog files, use server-side `put()` from `@vercel/blob` (not client upload). This produces permanent URLs.
**Warning signs:** Version rollback fails with 404 when fetching old catalog file

### Pitfall 4: Large File Upload Through BFF
**What goes wrong:** Catalog upload times out or fails with body size limit
**Why it happens:** Next.js API routes have a 4.5MB body limit by default; FTAG catalog is ~2-5MB Excel
**How to avoid:** Upload catalog file directly to Vercel Blob first (like tender doc upload), then pass blob URL to Python for validation
**Warning signs:** 413 Payload Too Large or timeout errors

### Pitfall 5: Product Override Conflicts
**What goes wrong:** Product edits reference row indices that change when a new catalog version is uploaded
**Why it happens:** Row indices are positional in the DataFrame
**How to avoid:** Use `Kostentraeger` (cost center, column 1) as the stable product identifier, not row index. This is the business key in FTAG catalog.
**Warning signs:** Product edits point to wrong products after catalog re-upload

### Pitfall 6: Prisma Migration on Neon
**What goes wrong:** `prisma migrate dev` hangs on remote Neon DB
**Why it happens:** Known issue documented in Phase 12-01 decisions
**How to avoid:** Create migration SQL manually, apply with `prisma migrate resolve`
**Warning signs:** CLI hangs indefinitely after "Creating migration..."

## Code Examples

### Prisma Schema Extension
```prisma
// Add to schema.prisma
model Catalog {
  id              String           @id @default(cuid())
  name            String
  description     String?
  activeVersionId String?
  createdBy       String
  createdAt       DateTime         @default(now())
  updatedAt       DateTime         @updatedAt
  versions        CatalogVersion[]

  @@map("catalog")
}

model CatalogVersion {
  id           String   @id @default(cuid())
  catalogId    String
  catalog      Catalog  @relation(fields: [catalogId], references: [id], onDelete: Cascade)
  versionNum   Int
  blobUrl      String   // Vercel Blob URL to Excel/CSV file
  fileName     String
  fileSize     Int
  totalProducts Int
  mainProducts  Int
  categories    Int
  uploadedBy   String
  notes        String?
  isActive     Boolean  @default(false)
  validationResult Json? // { errors: [], warnings: [], rowCount: N }
  createdAt    DateTime @default(now())

  @@map("catalog_version")
}

model ProductOverride {
  id          String   @id @default(cuid())
  catalogId   String
  productKey  String   // Kostentraeger (stable business key)
  action      String   // "add" | "edit" | "delete"
  data        Json?    // Full product fields for add/edit
  editedBy    String
  createdAt   DateTime @default(now())

  @@map("product_override")
}
```

### Python Catalog Search Endpoint
```python
# Extend backend/routers/catalog.py
@router.get("/catalog/products")
async def search_products(
    search: str = "",
    category: str = "",
    page: int = 1,
    limit: int = 50,
):
    """Search and filter products in the current catalog."""
    from services.catalog_index import get_catalog_index
    idx = get_catalog_index()

    profiles = idx.all_profiles
    if category:
        profiles = [p for p in profiles if p.category == category]
    if search:
        search_lower = search.lower()
        profiles = [p for p in profiles if search_lower in p.compact_text.lower()]

    total = len(profiles)
    start = (page - 1) * limit
    page_profiles = profiles[start:start + limit]

    return {
        "products": [
            {
                "row_index": p.row_index,
                "category": p.category,
                "summary": p.compact_text,
                "fields": p.key_fields,
            }
            for p in page_profiles
        ],
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit,
    }
```

### Python Catalog Version Diff
```python
@router.post("/catalog/diff")
async def diff_versions(body: dict):
    """Compare two catalog versions by loading their Excel files."""
    import io, pandas as pd

    old_content = await fetch_blob(body["old_blob_url"])
    new_content = await fetch_blob(body["new_blob_url"])

    old_df = pd.read_excel(io.BytesIO(old_content), header=6)
    new_df = pd.read_excel(io.BytesIO(new_content), header=6)

    added = len(new_df) - len(old_df)  # Simplified; real diff is column-aware
    return {
        "old_count": len(old_df),
        "new_count": len(new_df),
        "added": max(0, added),
        "removed": max(0, -added),
    }
```

### Catalog Upload Server Action
```typescript
'use server';
import { put } from '@vercel/blob';
import prisma from '@/lib/prisma';
import { auth } from '@/lib/auth';
import { headers } from 'next/headers';
import { revalidatePath } from 'next/cache';

const PYTHON_BACKEND_URL = process.env.PYTHON_BACKEND_URL || 'http://localhost:8000';
const PYTHON_SERVICE_KEY = process.env.PYTHON_SERVICE_KEY || '';

export async function uploadCatalog(formData: FormData) {
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session) return { error: 'Nicht authentifiziert' };

  const file = formData.get('file') as File;
  if (!file) return { error: 'Keine Datei' };

  // 1. Upload to Vercel Blob
  const blob = await put(`catalogs/${Date.now()}-${file.name}`, file, {
    access: 'public',
  });

  // 2. Validate via Python
  const validateRes = await fetch(
    `${PYTHON_BACKEND_URL}/api/catalog/validate`,
    {
      method: 'POST',
      headers: {
        'X-Service-Key': PYTHON_SERVICE_KEY,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ blob_url: blob.url }),
    }
  );
  const validation = await validateRes.json();

  if (validation.errors?.length > 0) {
    return { error: 'Validierung fehlgeschlagen', validation };
  }

  // 3. Create version in Prisma
  // ... create CatalogVersion record

  revalidatePath('/katalog');
  return { success: true, validation };
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Local file only (`data/produktuebersicht.xlsx`) | Vercel Blob + Prisma metadata | Phase 14 | Enables version history, multi-user |
| `@lru_cache` singleton | Cache with explicit invalidation API | Already exists | Must call `invalidate_catalog_cache()` |
| No version tracking | CatalogVersion model in Prisma | Phase 14 | Enables rollback and comparison |
| Direct Python upload | Blob upload + Python validation | Phase 14 | Handles file size limits, CDN caching |

**Deprecated/outdated:**
- Direct file write to `data/` directory should only be used as local dev fallback, not production path
- `DEFAULT_CATALOG_ID = 'ftag-default'` hardcoded in step-catalog.tsx needs to resolve to an actual Prisma Catalog record

## Open Questions

1. **CSV Support Depth**
   - What we know: KAT-01 says "Excel/CSV" upload. pandas handles both via `read_excel` / `read_csv`.
   - What's unclear: Does FTAG ever provide catalogs as CSV? The current catalog is .xlsx with complex structure.
   - Recommendation: Support CSV upload but validate it has the same column structure. Primary focus on Excel.

2. **Product Override Granularity**
   - What we know: FTAG catalog has 318 columns per product. Product edits need to be practical.
   - What's unclear: Which fields should be editable? Editing all 318 columns via a form is impractical.
   - Recommendation: Focus on key fields visible in the product browser (category, door type, fire class, dimensions). Store full JSON override but expose only ~15 fields in the edit form.

3. **Catalog Reload Trigger to Python**
   - What we know: STATE.md lists "Catalog reload trigger mechanism -- define in Phase 14 planning" as a concern.
   - What's unclear: When Prisma records a new active version, how does Python learn about it?
   - Recommendation: Explicit HTTP call from server action to Python endpoint `/api/catalog/activate` with blob URL. Python downloads, validates, and rebuilds index. Simpler than webhooks or polling.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Vitest 4.0.18 + Testing Library React 16.3.2 |
| Config file | `frontend/vitest.config.ts` |
| Quick run command | `cd frontend && npx vitest run --reporter=verbose` |
| Full suite command | `cd frontend && npx vitest run` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| KAT-01 | Upload catalog with validation results | unit | `cd frontend && npx vitest run src/__tests__/catalog/catalog-upload.test.tsx -x` | No - Wave 0 |
| KAT-02 | Browse and search products with filtering | unit | `cd frontend && npx vitest run src/__tests__/catalog/catalog-browse.test.tsx -x` | No - Wave 0 |
| KAT-03 | Version history, compare, rollback | unit | `cd frontend && npx vitest run src/__tests__/catalog/catalog-versions.test.tsx -x` | No - Wave 0 |
| KAT-04 | Add, edit, delete individual products | unit | `cd frontend && npx vitest run src/__tests__/catalog/product-edit.test.tsx -x` | No - Wave 0 |

### Sampling Rate
- **Per task commit:** `cd frontend && npx vitest run src/__tests__/catalog/ -x`
- **Per wave merge:** `cd frontend && npx vitest run`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `frontend/src/__tests__/catalog/catalog-upload.test.tsx` -- covers KAT-01
- [ ] `frontend/src/__tests__/catalog/catalog-browse.test.tsx` -- covers KAT-02
- [ ] `frontend/src/__tests__/catalog/catalog-versions.test.tsx` -- covers KAT-03
- [ ] `frontend/src/__tests__/catalog/product-edit.test.tsx` -- covers KAT-04

## Sources

### Primary (HIGH confidence)
- Project codebase: `backend/services/catalog_index.py` -- existing catalog loading, 318-column structure, lru_cache pattern
- Project codebase: `backend/routers/catalog.py` -- existing upload/info endpoints with backup logic
- Project codebase: `frontend/prisma/schema.prisma` -- current Prisma models (no catalog models yet)
- Project codebase: `frontend/src/lib/permissions.ts` -- catalog permissions already defined (read, update, upload)
- Project codebase: `frontend/src/components/analysis/step-catalog.tsx` -- current placeholder using `ftag-default`
- Project codebase: `frontend/src/app/api/backend/[...path]/route.ts` -- BFF proxy pattern
- Project codebase: `frontend/src/lib/actions/project-actions.ts` -- server action patterns

### Secondary (MEDIUM confidence)
- STATE.md decisions: "Catalog reload trigger mechanism -- define in Phase 14 planning"
- Phase 12-01 decision: "Created migration SQL manually (prisma migrate dev hangs on remote Neon DB)"
- Phase 13-01 decision: "Default catalog ID is 'ftag-default' string constant; upload disabled until Phase 14"

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all libraries already in project, no new dependencies needed
- Architecture: HIGH - follows established BFF proxy + server action patterns from phases 11-13
- Pitfalls: HIGH - identified from actual codebase (cache invalidation, header row, migration issues)

**Research date:** 2026-03-11
**Valid until:** 2026-04-11 (stable -- no external dependency changes expected)
