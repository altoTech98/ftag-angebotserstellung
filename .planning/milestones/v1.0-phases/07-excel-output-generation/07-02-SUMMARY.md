---
phase: 07-excel-output-generation
plan: 02
subsystem: api
tags: [fastapi, anthropic, structured-output, excel, offer-endpoint, background-job]

requires:
  - phase: 07-excel-output-generation
    provides: generate_v2_excel() function, _analysis_results storage dict
provides:
  - V2 offer generate endpoint (POST /api/offer/generate)
  - V2 offer download endpoint (GET /api/offer/{id}/download)
  - V2 offer status endpoint (GET /api/offer/status/{job_id})
  - Claude Sonnet Executive Summary generation with fallback
affects: [08-frontend-integration, frontend-react]

tech-stack:
  added: []
  patterns: [lazy-import-guard, structured-output-api, background-thread-generation, cache-with-ttl]

key-files:
  created: []
  modified:
    - backend/routers/offer.py
    - backend/tests/test_v2_excel_output.py

key-decisions:
  - "Lazy try/except import for anthropic SDK (graceful degradation when unavailable)"
  - "ExecutiveSummaryResponse Pydantic model for Claude messages.parse() structured output"
  - "Statistics-only fallback summary when Claude API fails or SDK unavailable"
  - "v2_result_{analysis_id}_xlsx cache key pattern with 3600s TTL"

patterns-established:
  - "V2 offer endpoint pattern: generate -> status -> download with background thread"
  - "Filename format: Machbarkeitsanalyse_{YYYYMMDD}_{analysis_id}.xlsx"
  - "Executive Summary via Claude Sonnet structured output with German system prompt"

requirements-completed: [APII-04, APII-05]

duration: 4min
completed: 2026-03-10
---

# Phase 7 Plan 2: API Endpoint Wiring Summary

**V2 offer API endpoints (generate/status/download) with Claude Sonnet Executive Summary and background thread generation**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-10T19:54:16Z
- **Completed:** 2026-03-10T19:58:30Z
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files modified:** 2

## Accomplishments
- POST /api/offer/generate accepts analysis_id, creates background job, runs Excel generation
- Executive Summary generated via Claude Sonnet messages.parse() with ExecutiveSummaryResponse structured output
- Graceful fallback to statistics-only summary when Claude API unavailable or fails
- GET /api/offer/{id}/download serves cached xlsx with Machbarkeitsanalyse_{date}_{id}.xlsx filename
- GET /api/offer/status/{job_id} polls background generation job status
- Excel bytes cached with 1-hour TTL in offer_cache
- 7 new integration tests (23 total: 16 unit + 7 integration)
- Existing v1 endpoints (result/generate, result/download, result/status) unchanged

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Failing integration tests** - `0c703af` (test)
2. **Task 1 GREEN: V2 offer endpoints implementation** - `a7f8e47` (feat)

## Files Created/Modified
- `backend/routers/offer.py` - Extended with v2 offer/generate, offer/status, offer/download endpoints
- `backend/tests/test_v2_excel_output.py` - Added 7 integration tests for API endpoint flow

## Decisions Made
- Lazy try/except import for anthropic SDK (graceful degradation when unavailable)
- ExecutiveSummaryResponse Pydantic model for Claude messages.parse() structured output
- Statistics-only fallback summary when Claude API fails or SDK unavailable
- v2_result_{analysis_id}_xlsx cache key pattern with 3600s TTL

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Pre-existing broken tests (test_offer.py, test_product_matcher.py) due to deleted/modified v1 modules - out of scope, not related to v2 changes

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- V2 API contract complete: generate -> status -> download flow works end-to-end
- Frontend can now call POST /api/offer/generate with analysis_id and poll/download
- ANTHROPIC_API_KEY required at runtime for Executive Summary AI generation (falls back gracefully)

---
*Phase: 07-excel-output-generation*
*Completed: 2026-03-10*
