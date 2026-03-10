# Phase 9: Frontend V2 Offer & Feedback Wiring - Research

**Researched:** 2026-03-10
**Domain:** React frontend wiring to v2 backend API (offer generation, download, feedback)
**Confidence:** HIGH

## Summary

Phase 9 wires the React frontend to consume v2 pipeline responses and call v2 backend endpoints for offer generation and feedback. The backend endpoints already exist and are fully implemented: `POST /api/offer/generate` (takes analysis_id), `GET /api/offer/status/{job_id}`, `GET /api/offer/{id}/download`, and `POST /api/v2/feedback`. The frontend code (AnalysePage.jsx, api.js, CorrectionModal.jsx, ResultsPanel) needs modification to use v2 data shapes and call the correct endpoints.

The v2 analysis response returns a fundamentally different structure from v1: `positionen` (array of ExtractedDoorPosition), `match_results` (per-position MatchResult with bester_match, dimension_scores), `adversarial_results` (per-position AdversarialResult with adjusted_confidence, per_dimension_cot), `gap_results` (per-position GapReport with gaps array, alternativen), and crucially `analysis_id` (8-char UUID for offer generation). The frontend currently reads `result.requirements` and `result.matching` (v1 shape) and must be adapted to read v2 keys and build the display mapping from the new structure.

The single-file workflow also needs v2 wiring -- currently it uses `api.uploadFile` + `api.startAnalysis` (v1 endpoints). Per CONTEXT.md decisions, a new `POST /api/v2/upload/single` backend endpoint is needed, or the existing `POST /api/v2/upload` can accept a single file (it already does -- the endpoint accepts `list[UploadFile]` and works with one file). The frontend needs `uploadSingleV2` that wraps a single file into the folder upload flow.

**Primary recommendation:** Map v2 response keys to the existing ResultsPanel display structure using a transformer function, wire v2 offer/download endpoints in api.js, and extend CorrectionModal to build v2 feedback payloads with dimensional context.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Keep results table simple -- same columns as v1 (Pos, Beschreibung, Menge, Brandschutz, FTAG Produkt, Kategorie, Begruendung). V2 details live in the detail modal + Excel only
- Extend the detail modal (PositionDetailModal) with adversarial result section (adjusted confidence, key challenges found) and gap items with severity badges
- Use dual labels for status grouping: "Erfuellbar (Bestaetigt)" / "Teilweise (Unsicher)" / "Nicht erfuellbar (Abgelehnt)"
- Same 4 stat cards (Gesamt, Erfuellbar, Teilweise, Nicht erfuellbar) + match rate bar, mapped from v2 counts
- Single "Excel herunterladen" button -- same pattern as now, 4-sheet structure is internal to the file
- Excel generation uses inline processing step (step 4 "Machbarkeitsanalyse erstellen") with progress polling, then results panel shows download button
- Add dimensional confidence breakdown in CorrectionModal (small summary: Masse: 95%, Brandschutz: 60%, etc.) above the product search
- Always send corrections to v2 feedback endpoint (POST /api/v2/feedback) with v2 schema (positions_nr, original_produkt_id, corrected_produkt_id)
- Include adversarial context in feedback payload (dimensional scores, which dimensions failed) for richer learning loop (MATC-09)
- Everything switches to v2 -- both single-file and folder uploads use v2 pipeline
- New single-file v2 endpoint: POST /api/v2/upload/single that accepts one file and returns tender_id
- Remove v1 API functions from api.js when v2 replacements are in place (uploadFile, startAnalysis, generateResult, createSSE, getJobStatus)
- runSingleWorkflow and runFolderWorkflow both use v2 endpoints

### Claude's Discretion
- How to map v2 result structure to the existing ResultsPanel sections (matched/partial/unmatched arrays)
- Exact layout of dimensional scores in CorrectionModal
- How to build the v2 feedback payload from available position + match data
- Whether to merge runSingleWorkflow and runFolderWorkflow into one function or keep separate

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| EXEL-01 | Excel Sheet 1 "Uebersicht" -- all positions with match status (green/yellow/red) | Backend `generate_v2_excel` already creates this sheet. Frontend calls `POST /api/offer/generate` with `analysis_id` |
| EXEL-02 | Excel Sheet 2 "Details" -- position-product with confidence, dimensional breakdown, reasoning | Backend sheet writer exists. Frontend just triggers generation via `analysis_id` |
| EXEL-03 | Excel Sheet 3 "Gap-Analyse" -- all non-matches with reasons, deviations, severity, alternatives | Backend `_write_gap_analyse` exists. Frontend triggers via same offer endpoint |
| EXEL-04 | Excel Sheet 4 "Executive Summary" -- statistics, summary, recommendations | Backend `_write_executive_summary` with Claude Sonnet call exists |
| EXEL-05 | Color coding: Green 95%+, Yellow 60-95%, Red <60% | Backend `_confidence_to_status` already implements this. Frontend shows same colors in CorrectionModal dimensional breakdown |
| EXEL-06 | Each decision cell contains reasoning (WHY) | Backend adds CoT as cell comments via `_add_comment`. No frontend work needed |
| APII-04 | POST /api/offer/generate creates 4-sheet Excel | Endpoint exists in `backend/routers/offer.py`. Frontend needs `generateV2Offer(analysisId)` in api.js |
| APII-05 | GET /api/offer/{id}/download delivers Excel file | Endpoint exists. Frontend needs `downloadV2Result(resultId)` in api.js |
| MATC-09 | System integrates feedback/corrections from earlier analyses as few-shot examples | V2 feedback store (`FeedbackStoreV2`) with TF-IDF retrieval exists. Frontend needs to send corrections to `POST /api/v2/feedback` with v2 schema |
| GAPA-05 | System suggests alternative products that could close the gap | Backend `GapReport.alternativen` field exists. Frontend PositionDetailModal needs to display alternatives |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React | 18.x | UI framework | Already in project |
| Vite | 6.x | Dev server + bundler | Already in project |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| CSS Modules | built-in | Component styling | Already used throughout (*.module.css) |

### Alternatives Considered
None -- this phase is pure wiring with existing stack. No new libraries needed.

## Architecture Patterns

### Recommended Project Structure
```
frontend-react/src/
├── services/
│   └── api.js              # ADD: v2 offer/feedback functions
├── hooks/
│   └── useSSE.js           # REUSE: pollJob with offer status path
├── pages/
│   └── AnalysePage.jsx     # MODIFY: workflows + ResultsPanel + PositionDetailModal
├── components/
│   └── CorrectionModal.jsx # MODIFY: v2 feedback schema + dimensional breakdown
└── utils/
    └── v2ResultMapper.js   # NEW: transform v2 response to display structure
```

### Pattern 1: V2 Result Transformer
**What:** A pure function that transforms the v2 API response shape into the display structure expected by ResultsPanel.
**When to use:** After v2 analysis completes, before setting state.
**Example:**
```javascript
// v2ResultMapper.js
export function mapV2ResultToDisplay(v2Result) {
  const { positionen, match_results, adversarial_results, gap_results, analysis_id } = v2Result

  // Build lookups by positions_nr
  const matchLookup = Object.fromEntries(
    (match_results || []).map(mr => [mr.positions_nr, mr])
  )
  const advLookup = Object.fromEntries(
    (adversarial_results || []).map(ar => [ar.positions_nr, ar])
  )
  const gapLookup = Object.fromEntries(
    (gap_results || []).map(gr => [gr.positions_nr, gr])
  )

  const matched = []
  const partial = []
  const unmatched = []

  for (const pos of positionen) {
    const nr = pos.positions_nr
    const adv = advLookup[nr]
    const match = matchLookup[nr]
    const gaps = gapLookup[nr]

    // Determine confidence from adversarial (preferred) or match
    const confidence = adv
      ? adv.adjusted_confidence
      : (match?.bester_match?.gesamt_konfidenz || 0)

    // Map to display item matching v1 shape for ResultsPanel
    const item = {
      position: nr,
      beschreibung: pos.positions_bezeichnung || pos.tuertyp || '-',
      original_position: pos, // full position data for detail modal
      confidence,
      category: match?.bester_match?.produkt_kategorie || '-',
      reason: adv?.resolution_reasoning || match?.bester_match?.begruendung || '',
      matched_products: match?.bester_match ? [{
        'Tuerblatt / Verglasungsart / Rollkasten': match.bester_match.produkt_name,
        _row_index: null, // v2 uses produkt_id not row_index
        _produkt_id: match.bester_match.produkt_id,
      }] : [],
      // V2-specific data for detail modal + correction modal
      _v2: {
        adversarial: adv,
        match: match,
        gaps: gaps,
        dimension_scores: match?.bester_match?.dimension_scores || [],
      },
      // Gap items for detail modal
      gap_items: gaps?.gaps?.map(g => ({
        field: g.dimension,
        detail: g.abweichung_beschreibung,
        severity: g.schweregrad,
      })) || [],
      // Match criteria for detail modal
      match_criteria: (match?.bester_match?.dimension_scores || []).map(ds => ({
        kriterium: ds.dimension,
        status: ds.score >= 0.95 ? 'ok' : ds.score >= 0.6 ? 'teilweise' : 'fehlt',
        detail: `${(ds.score * 100).toFixed(0)}% - ${ds.begruendung || ''}`,
      })),
    }

    // Classify by adjusted_confidence thresholds
    if (confidence >= 0.95) {
      matched.push(item)
    } else if (confidence >= 0.60) {
      partial.push(item)
    } else {
      unmatched.push(item)
    }
  }

  const total = positionen.length
  return {
    analysis_id,
    requirements: { positionen },
    matching: {
      matched,
      partial,
      unmatched,
      summary: {
        total_positions: total,
        matched_count: matched.length,
        partial_count: partial.length,
        unmatched_count: unmatched.length,
        match_rate: total > 0 ? Math.round((matched.length / total) * 100) : 0,
      },
    },
  }
}
```

### Pattern 2: V2 API Functions
**What:** New api.js exports for v2 offer generation, status polling, download, and feedback.
**When to use:** Called from AnalysePage workflows and CorrectionModal.
**Example:**
```javascript
// In api.js -- new v2 functions

export const uploadSingleV2 = (file) => {
  const form = new FormData()
  form.append('files', file)  // v2 upload accepts list[UploadFile]
  return request('/v2/upload', { method: 'POST', body: form })
}

export const generateV2Offer = (analysisId) =>
  request('/offer/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ analysis_id: analysisId }),
  })

export const getV2OfferStatus = (jobId) =>
  request(`/offer/status/${jobId}`)

export const downloadV2Result = async (resultId, filename) => {
  const token = getToken()
  const res = await fetch(`${API_BASE}/offer/${resultId}/download`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!res.ok) {
    throw new ApiError(
      res.status === 410
        ? 'Ergebnis abgelaufen - bitte erneut generieren.'
        : `Download fehlgeschlagen (HTTP ${res.status})`,
      res.status,
    )
  }
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename || `Machbarkeitsanalyse_${resultId}.xlsx`
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

export const saveV2Feedback = (body) =>
  request('/v2/feedback', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
```

### Pattern 3: V2 Feedback Payload Construction
**What:** Build the v2 feedback request from CorrectionModal item data.
**When to use:** In CorrectionModal.handleSave when v2 data is available.
**Example:**
```javascript
// V2 feedback payload structure matching backend FeedbackRequest schema
const v2Body = {
  positions_nr: item.position || pos.positions_nr,
  requirement_summary: [
    pos.positions_bezeichnung || pos.beschreibung,
    pos.tuertyp,
    pos.brandschutz,
  ].filter(Boolean).join(' | '),
  original_produkt_id: item._v2?.match?.bester_match?.produkt_id || '',
  original_konfidenz: item.confidence || 0,
  corrected_produkt_id: String(selectedProduct._row_index),
  corrected_produkt_name: selectedProduct._summary || '',
  correction_reason: note || 'Manuelle Korrektur',
}
```

### Pattern 4: Single-File V2 Backend Endpoint
**What:** New `POST /api/v2/upload/single` that accepts one file and returns tender_id.
**When to use:** For single-file upload workflow (runSingleWorkflow).
**Example:**
```python
# In upload_v2.py -- add single-file endpoint
@router.post("/upload/single")
async def upload_single_file(file: UploadFile = File(...)):
    """Upload a single file as a new tender session."""
    tender_id = str(uuid.uuid4())
    _tenders[tender_id] = {
        "files": [],
        "status": "uploading",
        "created_at": datetime.now(timezone.utc),
    }
    content = await file.read()
    filename = file.filename or "unknown"
    result: ParseResult = parse_document(content, filename)
    _tenders[tender_id]["files"].append(result)
    return {
        "tender_id": tender_id,
        "filename": filename,
        "format": result.format,
        "total_files": 1,
    }
```

**Note:** Alternatively, the existing `POST /api/v2/upload` already accepts a single file in the list, so the frontend can just wrap the single file and use the folder endpoint. The CONTEXT.md specifies a dedicated endpoint, so implement it for cleaner API semantics.

### Anti-Patterns to Avoid
- **Dual data flows:** Do not keep separate v1 and v2 data paths in the frontend. The transformer function should produce one unified structure.
- **Inline data transformation in JSX:** Move all v2-to-display mapping into the transformer utility, not scattered across components.
- **Forgetting analysis_id:** The v2 offer generation requires `analysis_id` from the v2 response. Store it alongside analysis state, not just the mapped display data.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Blob download | Custom download logic | Existing `downloadResult` pattern adapted for v2 URL | Proven pattern already handles auth, error states, filename |
| Job polling | Custom polling loop | Existing `useSSE.pollJob` with `/offer/status/` path | Already handles SSE + HTTP fallback, timeouts |
| Product search | New search UI | Existing CorrectionModal search with `searchProducts` | Already has debounce, selection, display |

## Common Pitfalls

### Pitfall 1: V2 Response Key Mismatch
**What goes wrong:** Frontend reads `result.requirements.positionen` (v1 nesting) but v2 returns `result.positionen` at top level.
**Why it happens:** V1 response wraps everything under `requirements` and `matching` keys. V2 returns flat top-level keys.
**How to avoid:** Use the transformer function. Never access v2 response keys directly in components -- always go through `mapV2ResultToDisplay()`.
**Warning signs:** Empty results table after analysis completes, undefined errors in console.

### Pitfall 2: Offer Generation Using Wrong Endpoint
**What goes wrong:** Frontend calls `api.generateResult(result.requirements, result.matching)` (v1 endpoint) instead of `api.generateV2Offer(result.analysis_id)` (v2 endpoint).
**Why it happens:** Copy-paste from existing workflow code.
**How to avoid:** V2 offer generation takes ONLY `analysis_id`. The backend looks up stored Pydantic objects. Never send raw data to the v2 offer endpoint.
**Warning signs:** 422 validation error from backend, or generating old 2-sheet Excel instead of new 4-sheet.

### Pitfall 3: Download URL Path Mismatch
**What goes wrong:** Frontend uses `/result/{id}/download` (v1) instead of `/offer/{id}/download` (v2).
**Why it happens:** V1 and v2 have different URL prefixes for download.
**How to avoid:** V2 download always uses `/offer/{id}/download`. The result_id from v2 offer generation IS the analysis_id.
**Warning signs:** 404 on download, or getting v1 2-sheet Excel.

### Pitfall 4: Feedback Schema Mismatch
**What goes wrong:** Frontend sends v1 feedback body (requirement_text, wrong_product, correct_product) to v2 endpoint.
**Why it happens:** CorrectionModal.handleSave has hardcoded v1 payload shape.
**How to avoid:** Detect v2 context via `item._v2` presence and build v2 payload with `positions_nr`, `original_produkt_id`, `corrected_produkt_id`, `correction_reason`.
**Warning signs:** 422 validation error from `/api/v2/feedback`.

### Pitfall 5: Status Polling Path for Offer Generation
**What goes wrong:** `pollJob` uses default `/analyze/status/` path for offer polling.
**Why it happens:** Developer forgets to pass the correct status path.
**How to avoid:** Pass `/offer/status/` as the `statusPath` parameter to `pollJob` for offer generation polling. This is NOT a v2 prefixed path -- the offer endpoints are under `/api/offer/` not `/api/v2/offer/`.
**Warning signs:** 404 errors during offer status polling.

### Pitfall 6: V2 Upload Already Works with Single Files
**What goes wrong:** Creating unnecessarily complex single-file upload logic.
**Why it happens:** Not realizing `POST /api/v2/upload` already accepts `list[UploadFile]` with a single file.
**How to avoid:** The dedicated `/api/v2/upload/single` endpoint is for API cleanliness per CONTEXT.md decision, but the implementation is trivial -- just wrap the multi-file endpoint logic.

## Code Examples

### V2 Response Shape (from analyze_v2.py)
```javascript
// What the v2 analysis SSE 'completed' event returns:
{
  "tender_id": "uuid...",
  "status": "completed",
  "positionen": [
    {
      "positions_nr": "T1.01",
      "positions_bezeichnung": "Eingangstuere EG",
      "tuertyp": "Innentuer",
      "brandschutz": "EI30",
      "schallschutz": "32 dB",
      "breite": 900,
      "hoehe": 2100,
      "menge": 1,
      "quellen": { ... },
      // ... more extracted fields
    }
  ],
  "match_results": [
    {
      "positions_nr": "T1.01",
      "hat_match": true,
      "bester_match": {
        "produkt_id": "42",
        "produkt_name": "Frank T30-1",
        "produkt_kategorie": "Brandschutztueren",
        "gesamt_konfidenz": 0.92,
        "begruendung": "...",
        "dimension_scores": [
          { "dimension": "Masse", "score": 0.98, "begruendung": "..." },
          { "dimension": "Brandschutz", "score": 0.95, "begruendung": "..." },
          // ... per dimension
        ]
      },
      "alternativen": [...]
    }
  ],
  "adversarial_results": [
    {
      "positions_nr": "T1.01",
      "validation_status": "bestaetigt",  // bestaetigt | unsicher | abgelehnt
      "adjusted_confidence": 0.89,
      "debate": [...],
      "resolution_reasoning": "...",
      "per_dimension_cot": [
        { "dimension": "Masse", "score": 0.96, "reasoning": "..." },
        { "dimension": "Brandschutz", "score": 0.60, "reasoning": "..." },
      ]
    }
  ],
  "gap_results": [
    {
      "positions_nr": "T1.01",
      "gaps": [
        {
          "dimension": "Brandschutz",
          "schweregrad": "major",
          "anforderung_wert": "EI60",
          "katalog_wert": "EI30",
          "abweichung_beschreibung": "...",
          "kundenvorschlag": "...",
          "technischer_hinweis": "..."
        }
      ],
      "alternativen": [
        {
          "produkt_id": "55",
          "produkt_name": "Frank T60-1",
          "teilweise_deckung": 0.85
        }
      ]
    }
  ],
  "analysis_id": "a1b2c3d4",  // CRITICAL: needed for offer generation
  "total_positionen": 15,
  "total_matches": 12,
  "total_gaps": 8,
  "plausibility": { ... }
}
```

### V2 Feedback Endpoint Schema (from feedback_v2.py)
```javascript
// POST /api/v2/feedback request body
{
  "positions_nr": "T1.01",
  "requirement_summary": "Eingangstuere EG | Innentuer | EI30",
  "original_produkt_id": "42",
  "original_konfidenz": 0.89,
  "corrected_produkt_id": "55",
  "corrected_produkt_name": "Frank T60-1 | Brandschutztuere | ...",
  "correction_reason": "Brandschutzklasse muss EI60 sein, nicht EI30"
}
```

### Offer Generation Flow
```javascript
// In runFolderWorkflow / runSingleWorkflow:
// 1. Store analysis_id from v2 result
const mapped = mapV2ResultToDisplay(result)
setAnalysis(mapped)
const analysisId = mapped.analysis_id

// 2. Generate v2 offer (step 4)
updateStep('gen', 'running', 'Machbarkeitsanalyse wird erstellt...')
const { job_id: offerJobId } = await api.generateV2Offer(analysisId)
const offerResult = await pollJob(
  offerJobId,
  (p) => setSubtitle(p || 'Ergebnis wird erstellt...'),
  '/offer/status/'  // NOT /v2/ prefix!
)

// 3. Store offer result for download
setOffer({ ...offerResult, result_id: offerResult.result_id || analysisId })

// 4. Download uses: api.downloadV2Result(analysisId)
```

## State of the Art

| Old Approach (v1) | Current Approach (v2) | Impact |
|---|---|---|
| `generateResult(requirements, matching)` sends full data | `generateV2Offer(analysis_id)` sends only ID | Backend looks up stored Pydantic objects, much cleaner |
| 2-sheet Excel (Tuermatrix + GAP) | 4-sheet Excel (Uebersicht + Details + Gap-Analyse + Executive Summary) | Richer output with dimensional breakdown and AI summary |
| `saveFeedback(v1Body)` to `/api/feedback` | `saveV2Feedback(v2Body)` to `/api/v2/feedback` | V2 schema includes produkt_id, konfidenz for TF-IDF retrieval |
| Separate upload paths (single vs folder) | Both use v2 pipeline | Unified analysis experience |
| Confidence from keyword matching | Confidence from adversarial adjusted_confidence | More reliable status classification |

## Open Questions

1. **Merging workflows**
   - What we know: runSingleWorkflow and runFolderWorkflow share 80%+ code after v2 migration (both use v2 upload, v2 analyze, v2 offer)
   - What's unclear: Whether merging into one function improves or hurts readability
   - Recommendation: Keep separate for now -- the upload step differs (single file vs multi-file FormData), but extract shared analysis/offer logic into a helper

2. **Product search row_index vs produkt_id**
   - What we know: V1 CorrectionModal uses `_row_index` to identify products. V2 feedback uses `produkt_id` (string).
   - What's unclear: Whether product search endpoint returns `produkt_id` or only `_row_index`
   - Recommendation: Use `_row_index` as `corrected_produkt_id` (cast to string) since the search endpoint returns `_row_index`. The v2 feedback store accepts string IDs.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (backend), no frontend test framework installed |
| Config file | backend/tests/ directory with conftest.py |
| Quick run command | `cd backend && python -m pytest tests/test_offer.py -x` |
| Full suite command | `cd backend && python -m pytest tests/ -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EXEL-01 | Uebersicht sheet generated | unit | `cd backend && python -m pytest tests/test_v2_excel_output.py -x` | Yes |
| EXEL-02 | Details sheet with dimensions | unit | `cd backend && python -m pytest tests/test_v2_excel_output.py -x` | Yes |
| EXEL-03 | Gap-Analyse sheet | unit | `cd backend && python -m pytest tests/test_v2_excel_output.py -x` | Yes |
| EXEL-04 | Executive Summary sheet | unit | `cd backend && python -m pytest tests/test_v2_excel_output.py -x` | Yes |
| EXEL-05 | Color coding thresholds | unit | `cd backend && python -m pytest tests/test_v2_excel_output.py -x` | Yes |
| EXEL-06 | Reasoning in cell comments | unit | `cd backend && python -m pytest tests/test_v2_excel_output.py -x` | Yes |
| APII-04 | POST /api/offer/generate endpoint | integration | `cd backend && python -m pytest tests/test_offer.py -x` | Partial (v1 only) |
| APII-05 | GET /api/offer/{id}/download | integration | `cd backend && python -m pytest tests/test_offer.py -x` | Partial (v1 only) |
| MATC-09 | V2 feedback integration | integration | `cd backend && python -m pytest tests/test_v2_matching.py -x` | Yes |
| GAPA-05 | Alternative product suggestions | unit | `cd backend && python -m pytest tests/test_v2_gaps.py -x` | Yes |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/test_v2_excel_output.py tests/test_offer.py -x`
- **Per wave merge:** `cd backend && python -m pytest tests/ -x`
- **Phase gate:** Full backend suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_v2_offer_endpoint.py` -- covers APII-04, APII-05 for v2 offer endpoints specifically
- [ ] Frontend tests not available -- manual verification required for UI wiring (no jest/vitest configured)

## Sources

### Primary (HIGH confidence)
- Direct code inspection of `backend/routers/offer.py` -- v2 offer endpoints fully implemented
- Direct code inspection of `backend/v2/routers/feedback_v2.py` -- v2 feedback endpoint and schema
- Direct code inspection of `backend/v2/output/excel_generator.py` -- 4-sheet Excel generator
- Direct code inspection of `backend/v2/routers/analyze_v2.py` -- v2 response shape with analysis_id
- Direct code inspection of `frontend-react/src/services/api.js` -- existing API functions
- Direct code inspection of `frontend-react/src/pages/AnalysePage.jsx` -- current workflow code
- Direct code inspection of `frontend-react/src/components/CorrectionModal.jsx` -- current feedback UI
- Direct code inspection of `frontend-react/src/hooks/useSSE.js` -- SSE polling logic

### Secondary (MEDIUM confidence)
- V2 response structure inferred from analyze_v2.py response dict construction and Pydantic model_dump() calls

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new libraries needed, all existing
- Architecture: HIGH -- all backend endpoints exist, frontend patterns are established
- Pitfalls: HIGH -- identified from direct code comparison of v1 vs v2 shapes

**Research date:** 2026-03-10
**Valid until:** 2026-04-10 (stable -- internal project, no external dependency changes expected)
