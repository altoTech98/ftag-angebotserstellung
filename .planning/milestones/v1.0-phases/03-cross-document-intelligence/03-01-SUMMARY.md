---
phase: 03-cross-document-intelligence
plan: 01
subsystem: extraction
tags: [cross-doc, pydantic, enrichment, conflict-detection, position-matching]

requires:
  - phase: 02-multi-pass-extraction
    provides: "ExtractedDoorPosition schema, FieldSource provenance, extraction pipeline"
provides:
  - "CrossDocMatch, FieldConflict, EnrichmentReport schemas"
  - "cross_doc_matcher.py: tiered position matching across documents"
  - "enrichment.py: gap fill + confidence upgrade + general spec application"
  - "conflict_detector.py: field-level conflict detection with severity classification"
  - "German prompt templates for cross-doc AI calls"
affects: [03-02 pipeline integration, 04 matching, 06 gap-analysis]

tech-stack:
  added: []
  patterns:
    - "Tiered confidence matching (exact 1.0 > normalized 0.92 > room+floor 0.7)"
    - "Deterministic severity classification (SAFETY_FIELDS/MAJOR_FIELDS sets)"
    - "Enrichment provenance via FieldSource.enrichment_source + enrichment_type"
    - "General spec scope matching (field==value pattern)"

key-files:
  created:
    - backend/v2/extraction/cross_doc_matcher.py
    - backend/v2/extraction/enrichment.py
    - backend/v2/extraction/conflict_detector.py
    - backend/tests/test_v2_crossdoc.py
  modified:
    - backend/v2/schemas/common.py
    - backend/v2/schemas/extraction.py
    - backend/v2/extraction/prompts.py
    - backend/tests/conftest_v2.py

key-decisions:
  - "Tiered matching: exact_id (1.0) > normalized_id (0.92) > room_floor_type (0.7) with auto_merge only at 0.9+"
  - "Severity classification is deterministic via field sets, not AI -- SAFETY_FIELDS for CRITICAL, MAJOR_FIELDS for MAJOR"
  - "Enrichment never downgrades: only gap_fill (None->value) and confidence_upgrade (low->high)"
  - "General specs use scope matching (field==value) and only fill empty fields at konfidenz=0.7"
  - "Rule-based conflict resolution as fallback when AI client is None (higher confidence wins)"

patterns-established:
  - "Cross-doc matching separate from intra-doc dedup (different criteria)"
  - "FieldSource enrichment_source/enrichment_type for cross-doc provenance"
  - "_normalize_position_id() strips Swiss tender ID prefixes (Tuer, Pos., Element, T-, Nr.)"
  - "_classify_severity() deterministic field-to-severity mapping"

requirements-completed: [DOKA-07, DOKA-08]

duration: 8min
completed: 2026-03-10
---

# Phase 3 Plan 1: Cross-Document Intelligence Core Modules Summary

**Tiered position matcher, enrichment engine with provenance tracking, and conflict detector with deterministic severity classification for cross-document intelligence**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-10T14:27:09Z
- **Completed:** 2026-03-10T14:35:31Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- Extended FieldSource and ExtractionResult schemas with cross-doc enrichment fields (fully backward compatible)
- Built 3 new modules: cross_doc_matcher, enrichment, conflict_detector
- 29 comprehensive tests covering all matching tiers, enrichment modes, and conflict scenarios
- German prompt templates ready for AI-powered cross-doc matching, conflict resolution, and spec detection

## Task Commits

Each task was committed atomically:

1. **Task 1: Schema extensions + cross-doc prompts + test fixtures** - `ccd31e0` (feat)
2. **Task 2: Cross-doc matcher + enrichment + conflict detector** - `92d8587` (feat)

_Both tasks followed TDD: RED (import errors) -> GREEN (implementation) -> all tests pass_

## Files Created/Modified
- `backend/v2/schemas/common.py` - FieldSource extended with enrichment_source, enrichment_type
- `backend/v2/schemas/extraction.py` - Added 7 new schemas (ConflictSeverity, FieldConflict, CrossDocMatch, GeneralSpec, DocumentEnrichmentStats, EnrichmentReport) + extended ExtractionResult
- `backend/v2/extraction/prompts.py` - 6 German prompt templates for cross-doc AI calls
- `backend/v2/extraction/cross_doc_matcher.py` - Tiered position matching with ID normalization
- `backend/v2/extraction/enrichment.py` - Gap fill, confidence upgrade, general spec application
- `backend/v2/extraction/conflict_detector.py` - Field conflict detection with severity + resolution
- `backend/tests/conftest_v2.py` - 4 new fixtures (xlsx_positions, pdf_positions, conflicting_positions, general_spec_text)
- `backend/tests/test_v2_crossdoc.py` - 29 tests across 5 test classes

## Decisions Made
- Tiered matching confidence values: exact=1.0, normalized=0.92, room+floor=0.7 (auto_merge threshold at 0.9)
- Severity classification is deterministic (field name lookup in sets), not AI-powered -- simple and reliable
- Rule-based fallback for conflict resolution when no AI client available (higher confidence wins)
- General spec scope uses simple field==value pattern, extensible for future needs
- Test fixture positions use different naming conventions ("Pos. 1.01", "Tuer 1.02") to test normalization

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test_exact_id_match to use correct fixture data**
- **Found during:** Task 2 (test execution)
- **Issue:** Test used xlsx_positions/pdf_positions fixtures but PDF positions have "Pos. 1.01" not "1.01" -- that is a normalized match, not exact
- **Fix:** Changed test to create inline positions with identical positions_nr for true exact matching
- **Files modified:** backend/tests/test_v2_crossdoc.py
- **Verification:** All 29 tests pass
- **Committed in:** 92d8587 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug fix)
**Impact on plan:** Test correctness fix, no scope change.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All cross-doc core modules ready for pipeline integration (Plan 03-02)
- Schemas backward compatible -- existing pipeline code unaffected
- Prompt templates ready for AI-powered matching/resolution when integrated with Anthropic client

---
*Phase: 03-cross-document-intelligence*
*Completed: 2026-03-10*
