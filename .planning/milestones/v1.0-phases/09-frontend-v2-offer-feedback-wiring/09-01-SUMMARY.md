---
phase: 09-frontend-v2-offer-feedback-wiring
plan: 01
subsystem: ui, api
tags: [react, fastapi, v2-pipeline, result-mapper, offer-generation]

requires:
  - phase: 08-quality-observability-e2e
    provides: v2 pipeline with SSE progress, offer endpoints, feedback endpoints
provides:
  - POST /api/v2/upload/single endpoint for single-file v2 upload
  - v2ResultMapper.js transformer for v2 response to display structure
  - v2 API functions in api.js (uploadSingleV2, generateV2Offer, downloadV2Result, saveV2Feedback)
  - Both workflows (single + folder) wired to v2 pipeline end-to-end
affects: [09-frontend-v2-offer-feedback-wiring]

tech-stack:
  added: []
  patterns: [v2 result transformer pattern, shared progress callback extraction]

key-files:
  created:
    - frontend-react/src/utils/v2ResultMapper.js
  modified:
    - backend/v2/routers/upload_v2.py
    - frontend-react/src/services/api.js
    - frontend-react/src/hooks/useSSE.js
    - frontend-react/src/pages/AnalysePage.jsx
    - frontend-react/src/components/CorrectionModal.jsx

key-decisions:
  - "Removed v1 SSE polling (pollSSE) from useSSE.js since createSSE was removed -- pollJob falls through to pollFallback for non-v2 paths"
  - "Extracted shared handleV2Progress callback for DRY progress handling across both workflows"
  - "CorrectionModal switched to v2 feedback schema with positions_nr, produkt_id, konfidenz fields"

patterns-established:
  - "v2ResultMapper pattern: pure transformer function between API response and display state"
  - "Shared progress callback: handleV2Progress extracted as useCallback for both workflows"

requirements-completed: [EXEL-01, EXEL-02, EXEL-03, EXEL-04, EXEL-05, EXEL-06, APII-04, APII-05]

duration: 5min
completed: 2026-03-10
---

# Phase 9 Plan 01: V2 Pipeline Wiring Summary

**V2 single-file upload endpoint, result transformer mapping positionen/match/adversarial/gap to display arrays, and full v2 pipeline wiring for both upload workflows with offer generation via analysis_id**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-10T21:43:45Z
- **Completed:** 2026-03-10T21:49:13Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Both single-file and folder upload workflows now use v2 pipeline end-to-end (upload, analyze, offer generate, download)
- v2ResultMapper correctly classifies positions into matched (>=0.95), partial (>=0.60), unmatched (<0.60) using adversarial adjusted_confidence
- V1 API functions completely removed from api.js (uploadFile, startAnalysis, generateResult, createSSE, etc.)
- Status labels updated to dual format per user decision (Erfuellbar/Bestaetigt, Teilweise/Unsicher, Nicht erfuellbar/Abgelehnt)

## Task Commits

Each task was committed atomically:

1. **Task 1: Backend single-file endpoint + v2ResultMapper + v2 API functions** - `842aa4f` (feat)
2. **Task 2: Rewire AnalysePage workflows to v2 pipeline** - `03f02e0` (feat)

## Files Created/Modified
- `backend/v2/routers/upload_v2.py` - Added POST /upload/single endpoint for single-file v2 upload
- `frontend-react/src/utils/v2ResultMapper.js` - NEW: Pure transformer from v2 API response to ResultsPanel display structure
- `frontend-react/src/services/api.js` - Added v2 functions, removed all v1 functions
- `frontend-react/src/hooks/useSSE.js` - Removed v1 pollSSE, kept v2 SSE + fallback polling
- `frontend-react/src/pages/AnalysePage.jsx` - Both workflows use v2 pipeline, dual status labels, v2 download
- `frontend-react/src/components/CorrectionModal.jsx` - Switched to saveV2Feedback with v2 schema

## Decisions Made
- Removed v1 SSE polling (pollSSE) from useSSE.js since createSSE was removed -- pollJob falls through to pollFallback for non-v2 paths
- Extracted shared handleV2Progress callback for DRY progress handling across both workflows
- Kept getJobStatus in api.js since useSSE.pollFallback needs it for HTTP polling
- CorrectionModal switched to v2 feedback schema in same commit as api.js changes (Rule 3 auto-fix)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Updated CorrectionModal to use v2 feedback API**
- **Found during:** Task 1 (API function removal)
- **Issue:** CorrectionModal imported `saveFeedback` which was removed from api.js
- **Fix:** Switched import to `saveV2Feedback`, rebuilt feedback payload with v2 schema (positions_nr, original_produkt_id, corrected_produkt_id, correction_reason)
- **Files modified:** frontend-react/src/components/CorrectionModal.jsx
- **Verification:** Frontend builds cleanly
- **Committed in:** 842aa4f (Task 1 commit)

**2. [Rule 3 - Blocking] Removed v1 pollSSE from useSSE.js**
- **Found during:** Task 1 (API function removal)
- **Issue:** useSSE.js referenced `api.createSSE` which was removed; pollSSE would fail at runtime
- **Fix:** Removed pollSSE callback and its reference in pollJob; non-v2 paths fall through to pollFallback
- **Files modified:** frontend-react/src/hooks/useSSE.js
- **Verification:** Frontend builds cleanly
- **Committed in:** 842aa4f (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (2 blocking)
**Impact on plan:** Both auto-fixes necessary for build correctness after v1 function removal. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- V2 pipeline fully wired for both upload paths
- CorrectionModal sends v2 feedback schema
- Ready for Plan 02 (if any) to add dimensional confidence breakdown in CorrectionModal and PositionDetailModal adversarial section

---
*Phase: 09-frontend-v2-offer-feedback-wiring*
*Completed: 2026-03-10*
