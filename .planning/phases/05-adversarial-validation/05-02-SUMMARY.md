---
phase: 05-adversarial-validation
plan: 02
subsystem: matching
tags: [adversarial, triple-check, opus, ensemble, tfidf, claude-opus]

requires:
  - phase: 05-adversarial-validation-01
    provides: "FOR/AGAINST debate engine, adversarial schemas, resolve_debate"
  - phase: 04-matching
    provides: "TF-IDF index, MatchResult, match_positions pipeline"
provides:
  - "triple_check_position function with wider pool + inverted prompt"
  - "Full adversarial pipeline wired into analyze endpoint"
  - "Graceful degradation when adversarial modules unavailable"
affects: [06-gap-analysis, 07-offer-generation]

tech-stack:
  added: []
  patterns: ["triple-check ensemble (parallel wider pool + inverted prompt)", "confidence-based approach selection"]

key-files:
  created: []
  modified:
    - backend/v2/matching/adversarial.py
    - backend/v2/matching/adversarial_prompts.py
    - backend/v2/routers/analyze_v2.py
    - backend/tests/test_v2_adversarial.py

key-decisions:
  - "Triple-check reuses ForArgument schema for structured output from both approaches"
  - "Wider pool searches with top_k=80 (vs standard 50) for expanded candidate coverage"
  - "Weighted confidence computation shared via DIMENSION_WEIGHTS constants"
  - "Candidates from both approaches deduplicated by produkt_id, keeping higher score"

patterns-established:
  - "Triple-check pattern: parallel independent evaluations, select winner by confidence"
  - "Graceful adversarial skip: _ADVERSARIAL_AVAILABLE flag with try/except import"

requirements-completed: [MATC-06, MATC-08]

duration: 7min
completed: 2026-03-10
---

# Phase 5 Plan 02: Triple-Check Ensemble and Pipeline Wiring Summary

**Triple-check ensemble with wider TF-IDF pool (top_k=80) and inverted requirement-centric prompt, wired end-to-end into analyze endpoint**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-10T18:07:24Z
- **Completed:** 2026-03-10T18:14:20Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Triple-check triggers automatically for positions below 95% confidence after FOR/AGAINST debate
- Two parallel approaches: wider TF-IDF pool (80 candidates) and inverted requirement-centric prompt
- Higher-confidence approach selected, candidates merged/deduplicated across all passes
- Analyze endpoint runs full pipeline: extraction -> matching -> adversarial validation
- Graceful degradation when adversarial modules unavailable or fail

## Task Commits

Each task was committed atomically:

1. **Task 1: Triple-check ensemble (TDD RED)** - `2c8084a` (test)
2. **Task 1: Triple-check ensemble (TDD GREEN)** - `9c55ee1` (feat)
3. **Task 2: Wire adversarial into analyze endpoint** - `3640eed` (feat)

_Note: Task 1 used TDD with RED/GREEN commits_

## Files Created/Modified
- `backend/v2/matching/adversarial_prompts.py` - Added WIDER_POOL and INVERTED system/user prompts for triple-check
- `backend/v2/matching/adversarial.py` - Added triple_check_position, updated validate_single_position and validate_positions
- `backend/v2/routers/analyze_v2.py` - Wired adversarial validation after matching in analyze endpoint
- `backend/tests/test_v2_adversarial.py` - 40 tests covering schemas, debate, triple-check, and endpoint integration

## Decisions Made
- Reused ForArgument schema for triple-check structured output (both approaches produce same format)
- Wider pool uses top_k=80 for expanded candidate coverage beyond standard 50
- Confidence computed via shared DIMENSION_WEIGHTS for consistency with debate resolution
- Candidates deduplicated by produkt_id with higher score preserved

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Pre-existing broken tests (test_offer.py, test_product_matcher.py, test_upload.py) unrelated to this plan
- All 40 adversarial tests pass, 264 total tests pass

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Full adversarial pipeline operational: extraction -> matching -> adversarial validation
- Response includes adversarial_results with debate arguments, CoT reasoning, validation status
- Ready for Phase 6 (gap analysis) which can consume adversarial validation results

---
*Phase: 05-adversarial-validation*
*Completed: 2026-03-10*
