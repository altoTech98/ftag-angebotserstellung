# Phase 9: Frontend V2 Offer & Feedback Wiring - Context

**Gathered:** 2026-03-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire the frontend to fully consume v2 pipeline responses (positionen, match_results, adversarial_results, gap_results), generate the 4-sheet Excel via POST /api/offer/generate with analysis_id, download via GET /api/offer/{id}/download, and send corrections to POST /api/v2/feedback with v2 schema. All upload paths (single-file and folder) switch to v2 pipeline.

</domain>

<decisions>
## Implementation Decisions

### V2 Results Display
- Keep results table simple — same columns as v1 (Pos, Beschreibung, Menge, Brandschutz, FTAG Produkt, Kategorie, Begruendung). V2 details live in the detail modal + Excel only
- Extend the detail modal (PositionDetailModal) with adversarial result section (adjusted confidence, key challenges found) and gap items with severity badges
- Use dual labels for status grouping: "Erfuellbar (Bestaetigt)" / "Teilweise (Unsicher)" / "Nicht erfuellbar (Abgelehnt)"
- Same 4 stat cards (Gesamt, Erfuellbar, Teilweise, Nicht erfuellbar) + match rate bar, mapped from v2 counts

### Download Experience
- Single "Excel herunterladen" button — same pattern as now, 4-sheet structure is internal to the file
- Excel generation uses inline processing step (step 4 "Machbarkeitsanalyse erstellen") with progress polling, then results panel shows download button

### Correction Workflow
- Add dimensional confidence breakdown in CorrectionModal (small summary: Masse: 95%, Brandschutz: 60%, etc.) above the product search — helps user understand WHY the match was wrong
- Always send corrections to v2 feedback endpoint (POST /api/v2/feedback) with v2 schema (positions_nr, original_produkt_id, corrected_produkt_id)
- Include adversarial context in feedback payload (dimensional scores, which dimensions failed) for richer learning loop (MATC-09)

### V1/V2 Coexistence
- Everything switches to v2 — both single-file and folder uploads use v2 pipeline
- New single-file v2 endpoint: POST /api/v2/upload/single that accepts one file and returns tender_id
- Remove v1 API functions from api.js when v2 replacements are in place (uploadFile, startAnalysis, generateResult, createSSE, getJobStatus)
- runSingleWorkflow and runFolderWorkflow both use v2 endpoints

### Claude's Discretion
- How to map v2 result structure to the existing ResultsPanel sections (matched/partial/unmatched arrays)
- Exact layout of dimensional scores in CorrectionModal
- How to build the v2 feedback payload from available position + match data
- Whether to merge runSingleWorkflow and runFolderWorkflow into one function or keep separate

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `useSSE.js`: Already has pollV2SSE and pollJob with v2 path detection — reuse for offer polling
- `api.js`: Has uploadFolderV2, startV2Analysis, createV2SSE, getV2JobStatus — extend with v2 offer/feedback functions
- `CorrectionModal.jsx`: Full correction UI with search, selection, note — extend with dimensional breakdown
- `PositionDetailModal`: Shows requirement fields, products, criteria, gaps — extend with adversarial section
- `ResultsPanel`: Table rendering with matched/partial/unmatched sections — adapt data mapping

### Established Patterns
- API functions in api.js follow `export const funcName = (params) => request(path, opts)` pattern
- Download uses blob + URL.createObjectURL + anchor click pattern (api.downloadResult)
- SSE polling with fallback to HTTP polling (useSSE.pollJob)
- Processing steps tracked via updateStep(id, state, status) callback pattern
- CorrectionModal uses debounced search + product selection pattern

### Integration Points
- `AnalysePage.jsx:runFolderWorkflow` — main wiring point: change result consumption + offer generation
- `AnalysePage.jsx:runSingleWorkflow` — switch from v1 to v2 pipeline
- `api.js` — add: generateV2Result, getV2ResultStatus, downloadV2Result, saveV2Feedback, uploadSingleV2
- `CorrectionModal.jsx:handleSave` — switch to v2 feedback schema
- `ResultsPanel` — adapt data mapping from v2 response shape

</code_context>

<specifics>
## Specific Ideas

- V2 offer generation takes analysis_id (not raw requirements + matching data) — simpler API call
- Dimensional scores in correction modal should be color-coded with same traffic light colors as Excel (green 95%+, yellow 60-95%, red <60%)
- When removing v1 functions, also clean up v1 SSE creation (createSSE) since pollSSE in useSSE.js only wraps it

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 09-frontend-v2-offer-feedback-wiring*
*Context gathered: 2026-03-10*
