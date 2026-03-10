---
phase: 08-quality-observability-end-to-end
plan: 03
subsystem: ui
tags: [react, sse, frontend, v2-api, eventsource]

# Dependency graph
requires:
  - phase: 08-quality-observability-end-to-end (plan 02)
    provides: v2 backend pipeline with SSE progress streaming
provides:
  - Frontend folder workflow wired to v2 upload + analyze endpoints
  - V2 SSE progress monitoring via pollV2SSE in useSSE hook
  - Position sub-progress bar activated for folder analysis
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns: [v2 SSE routing by status path prefix in useSSE hook]

key-files:
  created: []
  modified:
    - frontend-react/src/services/api.js
    - frontend-react/src/hooks/useSSE.js
    - frontend-react/src/pages/AnalysePage.jsx

key-decisions:
  - "V2 path detection via statusPath.startsWith('/v2/') for SSE routing"
  - "Removed tuerliste_count guard since v2 handles classification internally"

patterns-established:
  - "V2 SSE routing: pollJob detects /v2/ prefix and uses pollV2SSE automatically"

requirements-completed: [QUAL-03, APII-02]

# Metrics
duration: 2min
completed: 2026-03-10
---

# Phase 8 Plan 3: Frontend V2 Wiring Summary

**Folder workflow wired to v2 upload/analyze endpoints with SSE progress and position sub-progress bar**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-10T20:46:09Z
- **Completed:** 2026-03-10T20:48:15Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Added uploadFolderV2 function targeting /v2/upload endpoint
- Added pollV2SSE in useSSE hook for v2 SSE stream monitoring with automatic fallback
- Rewired runFolderWorkflow to call v2 upload -> v2 analyze -> v2 SSE polling
- Position sub-progress bar now activates during folder analysis via structured JSON progress
- Single-file workflow remains unchanged on v1 endpoints

## Task Commits

Each task was committed atomically:

1. **Task 1: Add v2 upload function and wire useSSE for v2 paths** - `4c6cbf3` (feat)
2. **Task 2: Wire runFolderWorkflow to v2 upload + analyze endpoints** - `d9b8f08` (feat)

## Files Created/Modified
- `frontend-react/src/services/api.js` - Added uploadFolderV2 for /v2/upload endpoint
- `frontend-react/src/hooks/useSSE.js` - Added pollV2SSE with v2 SSE routing in pollJob
- `frontend-react/src/pages/AnalysePage.jsx` - Rewired runFolderWorkflow to v2 endpoints

## Decisions Made
- V2 path detection via statusPath.startsWith('/v2/') prefix check -- simple and extensible
- Removed tuerliste_count guard in folder workflow since v2 pipeline handles file classification internally during extraction
- Kept v1 single workflow untouched -- only folder workflow gets the v2 multi-file pipeline

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Both verification gaps from 08-VERIFICATION.md are now closed
- Folder workflow is fully wired to v2 backend pipeline end-to-end
- Structured progress (stage, percent, position counts) flows from backend to frontend

## Self-Check: PASSED

All files exist. All commits verified (4c6cbf3, d9b8f08).

---
*Phase: 08-quality-observability-end-to-end*
*Completed: 2026-03-10*
