# Phase 16: Fix Analysis-to-Python File Bridge - Research

**Researched:** 2026-03-11
**Domain:** Cross-system integration (Next.js server actions -> Python/FastAPI)
**Confidence:** HIGH

## Summary

Phase 16 is a targeted bug-fix phase addressing three specific integration failures identified in the v2.0 milestone audit. All three issues are in the Next.js frontend code calling the Python backend incorrectly. The Python backend endpoints and auth middleware are correct and do not need changes.

The three issues are: (1) `prepareFilesForPython` calls a non-existent endpoint `/api/upload/project` instead of `/api/upload/folder`, (2) the same function sends `X-API-Key` header instead of `X-Service-Key`, and (3) `handleCancelConfirm` calls a non-existent cancel endpoint. All three are simple code fixes -- no architectural changes, no new libraries, no new patterns needed.

**Primary recommendation:** Fix the three broken references in `analysis-actions.ts` and `step-progress.tsx`. No new dependencies or architectural changes required.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ANLZ-04 | Schritt 4 -- Analyse starten mit Echtzeit-Fortschrittsbalken (SSE direkt zu Python) | All three fixes enable the analysis flow to execute end-to-end: correct endpoint, correct auth header, and graceful cancel handling |
</phase_requirements>

## Standard Stack

No new libraries needed. This phase modifies existing code only.

### Existing Code Locations (to modify)

| File | Line(s) | Issue |
|------|---------|-------|
| `frontend/src/lib/actions/analysis-actions.ts` | 50 | Wrong endpoint: `/api/upload/project` should be `/api/upload/folder` |
| `frontend/src/lib/actions/analysis-actions.ts` | 53 | Wrong header: `X-API-Key` should be `X-Service-Key` |
| `frontend/src/components/analysis/step-progress.tsx` | 135 | Calls non-existent cancel endpoint |

### Python Backend (NO changes needed)

| Endpoint | File | Status |
|----------|------|--------|
| `POST /api/upload/folder` | `backend/routers/upload.py:204` | Exists, works correctly |
| `POST /api/analyze/project` | `backend/routers/analyze.py:244` | Exists, works correctly |
| Service key middleware | `backend/services/service_auth.py:32` | Validates `X-Service-Key` header correctly |

## Architecture Patterns

### The File Bridge Flow (current, broken)

```
1. User clicks "Analyse starten" in wizard step 3
2. handleStartAnalysis() in client.tsx
3. -> prepareFilesForPython() server action
   3a. Fetches files from Vercel Blob (downloadUrl)
   3b. Builds FormData with files + project_id
   3c. POSTs to Python backend  <-- BROKEN: wrong endpoint + wrong header
4. -> createAnalysis() server action (Prisma record)
5. -> fetch('/api/backend/analyze/project') via BFF proxy <-- This works correctly
6. StepProgress connects via SSE for real-time updates
7. Cancel button tries to call cancel endpoint <-- BROKEN: endpoint doesn't exist
```

### The File Bridge Flow (fixed)

```
1-2. Same as above
3. -> prepareFilesForPython() server action
   3a. Fetches files from Vercel Blob (downloadUrl)
   3b. Builds FormData with files (field name: 'files')
   3c. POSTs to PYTHON_BACKEND_URL/api/upload/folder with X-Service-Key header
4-6. Same as above (already work)
7. Cancel button closes SSE connection + calls onCancel (no backend call)
```

### Key Insight: Direct vs BFF Proxy

`prepareFilesForPython` is a **server action** (runs on Next.js server, not browser). It calls Python **directly** using `PYTHON_BACKEND_URL`, bypassing the BFF proxy. This is correct -- server-to-server calls should be direct. But it must use the same auth header (`X-Service-Key`) that the BFF proxy uses.

The BFF proxy at `frontend/src/app/api/backend/[...path]/route.ts` correctly sets `X-Service-Key` (line 38). The server action should match this pattern.

### Cancel Endpoint Analysis

Python `analyze.py` has NO cancel endpoint. The available routes are:
- `POST /api/analyze` -- single file analysis
- `POST /api/analyze/project` -- project analysis
- `GET /api/analyze/status/{job_id}` -- poll status
- `GET /api/analyze/stream/{job_id}` -- SSE stream

The cancel button in `step-progress.tsx` currently calls `POST /api/backend/analyze/cancel/${jobId}` which:
1. Goes through the BFF proxy to `POST /api/analyze/cancel/${jobId}` on Python
2. Python has no such route -- returns 404
3. The error is silently caught (try/catch with empty catch)
4. `onCancel()` is still called, so the UI handles it correctly

**Recommendation:** Remove the backend cancel call entirely. The current behavior already works from the user's perspective (SSE connection is closed, wizard returns to step 3). The Python background thread will complete and its result will simply not be consumed. Adding a proper cancel endpoint is tracked as tech debt in the audit but is out of scope for this phase.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cancel endpoint | A new Python cancel route | Remove the call; close SSE only | Python runs analysis in a background thread with no cancellation mechanism; adding one requires refactoring job_store |
| File upload validation | Custom request format checking | Trust Python's existing validation | `upload_folder` already validates file types, sizes, counts |

## Common Pitfalls

### Pitfall 1: FormData field name mismatch
**What goes wrong:** Python's `upload_folder` expects files under the field name `files` (parameter: `files: List[UploadFile] = File(...)`). The current code correctly uses `formData.append('files', blob, file.name)` -- this is fine.
**How to avoid:** Do not change the FormData field name when fixing the endpoint URL.

### Pitfall 2: project_id not passed to upload/folder
**What goes wrong:** Python's `/upload/folder` does NOT accept a `project_id` parameter. It generates its own `project_id` (UUID[:12]). The current code appends `project_id` to FormData, but Python ignores it. The Python-generated `project_id` is used for caching, and `POST /api/analyze/project` uses this Python `project_id`.
**Critical flow detail:** Looking at the wizard flow more carefully:
- `prepareFilesForPython` sends files to Python and gets back a Python `project_id`
- Then `fetch('/api/backend/analyze/project')` sends `{ project_id: project.id }` where `project.id` is the **Prisma** project ID
- But Python's `analyze_project` looks up `get_project(request.project_id)` which expects the **Python** project ID from `upload_folder`

**This is a data flow mismatch that needs careful handling.** The current code sends the Prisma project ID to `analyze/project`, but Python expects the project ID it generated during `upload/folder`. The fix must either:
1. Capture Python's returned `project_id` from `upload/folder` and use it in the `analyze/project` call, OR
2. Pass the Prisma `project_id` to `upload/folder` via a query param or form field and make Python use it

**Recommendation:** Option 1 is simpler and requires no Python changes. `prepareFilesForPython` should return the Python `project_id`, and `handleStartAnalysis` should use it for the `analyze/project` call.

### Pitfall 3: upload/folder response vs what's expected
**What goes wrong:** The `prepareFilesForPython` function currently returns `{ success: true }` and discards the response body. After the fix, it must return the Python `project_id` from the response.
**How to avoid:** Update the return type to include `pythonProjectId` and extract it from the `FolderUploadResponse`.

### Pitfall 4: Content-Type header with FormData
**What goes wrong:** Setting `Content-Type` manually when sending FormData breaks the multipart boundary. The current code does NOT set Content-Type (only sets `X-API-Key`), which is correct -- `fetch()` auto-sets the `Content-Type: multipart/form-data` with boundary.
**How to avoid:** When fixing the header from `X-API-Key` to `X-Service-Key`, do NOT add a Content-Type header.

## Code Examples

### Fix 1: Correct endpoint and auth header in prepareFilesForPython

```typescript
// File: frontend/src/lib/actions/analysis-actions.ts
// BEFORE (broken):
const uploadResponse = await fetch(
  `${PYTHON_BACKEND_URL}/api/upload/project`,
  {
    method: 'POST',
    headers: {
      'X-API-Key': PYTHON_SERVICE_KEY,
    },
    body: formData,
  }
);

// AFTER (fixed):
const uploadResponse = await fetch(
  `${PYTHON_BACKEND_URL}/api/upload/folder`,
  {
    method: 'POST',
    headers: {
      'X-Service-Key': PYTHON_SERVICE_KEY,
    },
    body: formData,
  }
);
```

### Fix 2: Return Python project_id from prepareFilesForPython

```typescript
// BEFORE:
export async function prepareFilesForPython(
  projectId: string,
  fileIds: string[]
): Promise<{ success: true } | { error: string }> {
  // ... upload logic ...
  if (!uploadResponse.ok) { /* error */ }
  return { success: true };
}

// AFTER:
export async function prepareFilesForPython(
  projectId: string,
  fileIds: string[]
): Promise<{ success: true; pythonProjectId: string } | { error: string }> {
  // ... upload logic (with fixed endpoint/header) ...
  if (!uploadResponse.ok) { /* error */ }
  const uploadData = await uploadResponse.json();
  return { success: true, pythonProjectId: uploadData.project_id };
}
```

### Fix 3: Use Python project_id in handleStartAnalysis

```typescript
// In client.tsx handleStartAnalysis:
// BEFORE:
const response = await fetch('/api/backend/analyze/project', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ project_id: project.id }),  // Prisma ID -- wrong!
});

// AFTER:
const response = await fetch('/api/backend/analyze/project', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ project_id: prepareResult.pythonProjectId }),  // Python ID -- correct
});
```

### Fix 4: Remove cancel endpoint call in step-progress.tsx

```typescript
// BEFORE:
async function handleCancelConfirm() {
  setCancelDialogOpen(false);
  connectionRef.current?.close();
  connectionRef.current = null;
  if (jobId) {
    try {
      await fetch(`/api/backend/analyze/cancel/${jobId}`, { method: 'POST' });
    } catch {
      // Best effort cancel
    }
  }
  onCancel();
}

// AFTER:
async function handleCancelConfirm() {
  setCancelDialogOpen(false);
  connectionRef.current?.close();
  connectionRef.current = null;
  // No backend cancel endpoint exists -- closing SSE connection is sufficient.
  // Python background thread will complete but result is not consumed.
  onCancel();
}
```

## State of the Art

No technology changes. This is purely a bug-fix phase correcting integration mismatches.

| Old (Broken) | New (Fixed) | Impact |
|--------------|-------------|--------|
| `/api/upload/project` | `/api/upload/folder` | Endpoint actually exists on Python |
| `X-API-Key` header | `X-Service-Key` header | service_key_middleware accepts the request |
| Send Prisma project_id to analyze | Send Python project_id to analyze | Python can find the project in its cache |
| Call non-existent cancel endpoint | No backend cancel call | No silent 404 errors |

## Open Questions

1. **FormData `project_id` field**
   - What we know: Current code appends `project_id` to FormData. Python's `upload_folder` does not read this field (it auto-generates one).
   - What's unclear: Should we remove the `project_id` from FormData or leave it (harmless extra field)?
   - Recommendation: Remove it to keep the request clean and avoid confusion.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Vitest (via frontend/package.json) |
| Config file | `frontend/vitest.config.ts` |
| Quick run command | `cd frontend && npx vitest run --reporter=verbose` |
| Full suite command | `cd frontend && npx vitest run` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ANLZ-04-a | prepareFilesForPython calls /upload/folder with X-Service-Key | unit (mock fetch) | `cd frontend && npx vitest run src/__tests__/analysis/file-bridge.test.ts -x` | No -- Wave 0 |
| ANLZ-04-b | handleCancelConfirm does not call non-existent cancel endpoint | unit | `cd frontend && npx vitest run src/__tests__/analysis/step-progress.test.tsx -x` | Yes (needs update) |
| ANLZ-04-c | handleStartAnalysis passes Python project_id to analyze/project | unit (mock fetch) | `cd frontend && npx vitest run src/__tests__/analysis/file-bridge.test.ts -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `cd frontend && npx vitest run src/__tests__/analysis/ -x`
- **Per wave merge:** `cd frontend && npx vitest run`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `frontend/src/__tests__/analysis/file-bridge.test.ts` -- covers ANLZ-04-a, ANLZ-04-c (test prepareFilesForPython endpoint/header/response)
- [ ] Update `frontend/src/__tests__/analysis/step-progress.test.tsx` -- verify cancel does not call backend

## Sources

### Primary (HIGH confidence)
- Direct code inspection of `frontend/src/lib/actions/analysis-actions.ts` -- confirmed wrong endpoint (line 50) and wrong header (line 53)
- Direct code inspection of `backend/routers/upload.py` -- confirmed `/upload/folder` exists (line 204), `/upload/project` does not
- Direct code inspection of `backend/services/service_auth.py` -- confirmed middleware checks `x-service-key` header (line 71)
- Direct code inspection of `backend/routers/analyze.py` -- confirmed no cancel endpoint exists, `analyze/project` expects Python project_id
- Direct code inspection of `frontend/src/app/api/backend/[...path]/route.ts` -- confirmed BFF proxy correctly uses `X-Service-Key` (line 38)
- Direct code inspection of `frontend/src/components/analysis/step-progress.tsx` -- confirmed cancel calls non-existent endpoint (line 135)
- Direct code inspection of `frontend/src/app/(app)/projekte/[id]/analyse/client.tsx` -- confirmed `handleStartAnalysis` sends Prisma project_id to analyze/project (line 213)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no new libraries, pure bug fixes in known codebase
- Architecture: HIGH - all code paths traced end-to-end via direct inspection
- Pitfalls: HIGH - project_id mismatch (Pitfall 2) is a critical finding discovered during research that goes beyond the audit's original three issues

**Research date:** 2026-03-11
**Valid until:** indefinite (bug-fix findings, not library versions)
