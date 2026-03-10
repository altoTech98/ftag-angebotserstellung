---
phase: 02-multi-pass-extraction
plan: 03
subsystem: extraction
tags: [ai-extraction, pipeline, validation, chunking, retry, structured-output]

# Dependency graph
requires:
  - phase: 02-extraction-foundations
    provides: "extract_structural, chunk_by_pages, merge_positions, prompts"
  - phase: 02-api-endpoints
    provides: "POST /api/v2/analyze, tender storage with ParseResults"
provides:
  - "extract_semantic: AI semantic extraction with chunked overlap and retry"
  - "validate_and_enrich: Cross-reference validation and adversarial review"
  - "run_extraction_pipeline: Full 3-pass orchestrator (structural + semantic + validation)"
  - "POST /api/v2/analyze wired to full pipeline"
affects: [03-cross-document, 04-matching, 05-adversarial]

# Tech tracking
tech-stack:
  added: []
  patterns: [messages-parse-structured-output, asyncio-to-thread-wrapping, exponential-backoff-retry, position-batching]

key-files:
  created:
    - backend/v2/extraction/pass2_semantic.py
    - backend/v2/extraction/pass3_validation.py
    - backend/v2/extraction/pipeline.py
    - backend/tests/test_v2_pipeline.py
  modified:
    - backend/v2/extraction/__init__.py
    - backend/v2/routers/analyze_v2.py
    - backend/tests/test_v2_analyze.py

key-decisions:
  - "Use asyncio.to_thread wrapping sync Anthropic().messages.parse() for async compatibility"
  - "Pass 2 konfidenz=0.9, Pass 3 konfidenz=0.95 for provenance tracking"
  - "Position batching at 25 per batch for Pass 3 to avoid context overflow"
  - "Pass 3 sends compact position summaries (key fields only) not full JSON"

patterns-established:
  - "Pipeline orchestration: per-file Pass 1+2 with dedup, then cross-file Pass 3"
  - "Retry pattern: 3x with exponential backoff (2^attempt seconds)"
  - "Failed chunk skip: continue pipeline with warning on exhausted retries"

requirements-completed: [DOKA-05, DOKA-06]

# Metrics
duration: 4min
completed: 2026-03-10
---

# Phase 02 Plan 03: AI Passes + Pipeline Orchestrator Summary

**Pass 2 AI semantic extraction with chunking/retry, Pass 3 cross-reference validation with batching, and full pipeline orchestrator wired to /api/v2/analyze**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-10T13:37:00Z
- **Completed:** 2026-03-10T13:41:14Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Pass 2 extracts door positions via Claude messages.parse() with page-based chunking and 3x retry with exponential backoff
- Pass 3 validates all positions against original texts with adversarial review, batching positions >25 to avoid context overflow
- Pipeline orchestrator runs all 3 passes in XLSX > PDF > DOCX order with dedup after each pass
- POST /api/v2/analyze now triggers the full extraction pipeline and returns structured ExtractionResult
- 15 new tests covering pipeline ordering, pass execution, dedup, chunking, retry, skip, batching, and result shape

## Task Commits

Each task was committed atomically:

1. **Task 1: Pass 2 semantic + Pass 3 validation + pipeline orchestrator** - `93717c3` (feat)
2. **Task 2: Wire pipeline to /api/v2/analyze endpoint** - `ff69fb9` (feat)

## Files Created/Modified
- `backend/v2/extraction/pass2_semantic.py` - AI semantic extraction with chunking, retry, and FieldSource provenance
- `backend/v2/extraction/pass3_validation.py` - Cross-reference validation with position batching and adversarial review
- `backend/v2/extraction/pipeline.py` - Pipeline orchestrator coordinating all 3 passes with format-priority sorting
- `backend/v2/extraction/__init__.py` - Updated exports with extract_semantic, validate_and_enrich, run_extraction_pipeline
- `backend/v2/routers/analyze_v2.py` - Replaced stub with real pipeline call, error handling, status updates
- `backend/tests/test_v2_pipeline.py` - 9 tests for pipeline and pass logic (all mocked)
- `backend/tests/test_v2_analyze.py` - 6 tests for endpoint integration with mocked pipeline

## Decisions Made
- Used asyncio.to_thread() wrapping sync Anthropic client for messages.parse() since AsyncAnthropic may not support it
- Pass 2 tags fields with konfidenz=0.9 (AI confidence), Pass 3 with konfidenz=0.95 (validation confidence)
- Position batching threshold at 25 per batch for Pass 3 to stay within context limits
- Pass 3 sends compact position summaries (key fields only, not full JSON) per Pitfall 5 from research

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- .gitignore `test_*` pattern requires `git add -f` for test files (consistent with previous plans)

## User Setup Required
None - no external service configuration required. ANTHROPIC_API_KEY needed at runtime.

## Next Phase Readiness
- Full extraction pipeline operational: upload files -> analyze -> structured positions
- Phase 2 complete: all 3 plans delivered
- Ready for Phase 3 (Cross-Document Linking) or Phase 4 (Matching)

## Self-Check: PASSED
