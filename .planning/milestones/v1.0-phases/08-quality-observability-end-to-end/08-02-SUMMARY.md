---
phase: 08-quality-observability-end-to-end
plan: 02
subsystem: api, frontend, testing
tags: [sse, background-jobs, progress-streaming, async-pipeline, fastapi, react]

requires:
  - phase: 08-quality-observability-end-to-end
    provides: PlausibilityChecker, log_step, AIServiceError, raise_ai_error
  - phase: 07-result-generation
    provides: Full v2 pipeline (extraction, matching, adversarial, gaps)
provides:
  - Async background job execution for v2 analyze endpoint
  - SSE streaming with structured JSON progress events
  - Status polling endpoint for v2 jobs
  - Frontend structured progress parsing with position sub-progress
  - 15 integration tests for endpoint and progress patterns
affects: [end-to-end testing, deployment]

tech-stack:
  added: []
  patterns: [background-thread-with-asyncio-loop, progress-throttling-500ms, structured-json-progress]

key-files:
  created:
    - backend/tests/test_analyze_v2_endpoint.py
    - backend/tests/test_sse_progress.py
  modified:
    - backend/v2/routers/analyze_v2.py
    - backend/v2/extraction/pipeline.py
    - frontend-react/src/pages/AnalysePage.jsx
    - frontend-react/src/services/api.js

key-decisions:
  - "Progress throttle at 500ms to prevent SSE flooding"
  - "Fail-fast via raise_ai_error: no partial results on AI failure"
  - "Extraction progress scaled to 0-30% of total pipeline percent"

patterns-established:
  - "Structured progress JSON: {message, stage, percent, current_position, positions_done, positions_total}"
  - "Background sync wrapper: asyncio.new_event_loop() in thread for async pipeline"
  - "Frontend try/catch JSON.parse for backward-compatible progress parsing"

requirements-completed: [QUAL-03, APII-02, APII-03]

duration: 6min
completed: 2026-03-10
---

# Phase 08 Plan 02: Pipeline Wiring with SSE Progress Summary

**Async background job execution with structured SSE progress streaming, position-level tracking, and fail-fast error handling for the full v2 pipeline**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-10T20:26:16Z
- **Completed:** 2026-03-10T20:32:16Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- POST /api/v2/analyze returns job_id immediately; pipeline runs in background thread with asyncio event loop
- SSE progress events include structured JSON with stage, percent, current_position, positions_done, positions_total
- Fail-fast error handling via raise_ai_error replaces all try/except partial-result patterns
- Plausibility check runs after pipeline completion and result is included in job output
- Frontend parses structured progress JSON and shows position sub-progress bar
- 36 total tests pass (21 from Plan 01 + 15 new)

## Task Commits

Each task was committed atomically:

1. **Task 1: Convert analyze_v2 to background job with progress callbacks** - `f4e1411` (feat)
2. **Task 2: Frontend structured progress + integration tests** - `5533c45` (feat)

## Files Created/Modified
- `backend/v2/routers/analyze_v2.py` - Rewritten: async background job, SSE stream, status poll, fail-fast, plausibility
- `backend/v2/extraction/pipeline.py` - Added on_progress callback param, log_step calls per pass
- `frontend-react/src/pages/AnalysePage.jsx` - Structured progress parsing, position sub-progress bar
- `frontend-react/src/services/api.js` - Added createV2SSE, getV2JobStatus, startV2Analysis
- `backend/tests/test_analyze_v2_endpoint.py` - 6 tests: POST/GET endpoints, job patterns
- `backend/tests/test_sse_progress.py` - 9 tests: structured progress, throttling, plausibility

## Decisions Made
- Progress throttle at 500ms interval to prevent SSE flooding (research Pitfall 2)
- Fail-fast via raise_ai_error on all AI failures: no partial results stored
- Extraction progress scaled to 0-30% of total pipeline percentage
- Frontend uses try/catch JSON.parse for backward-compatible progress parsing (works with both v1 plain strings and v2 JSON)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed ParseResult constructor in test**
- **Found during:** Task 2 (integration tests)
- **Issue:** ParseResult uses `page_count` parameter, not `pages`
- **Fix:** Changed test fixture to use correct parameter name
- **Files modified:** backend/tests/test_analyze_v2_endpoint.py
- **Verification:** All 15 tests pass

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Trivial test fixture fix. No scope creep.

## Issues Encountered
- Test files in backend/tests/ were in .gitignore; used `git add -f` to include them (same pattern as Plan 01)

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Full v2 pipeline is now end-to-end wired with async execution and live progress
- Phase 08 complete: quality validation, structured logging, fail-fast errors, and SSE streaming all integrated
- Ready for production deployment testing

---
*Phase: 08-quality-observability-end-to-end*
*Completed: 2026-03-10*
