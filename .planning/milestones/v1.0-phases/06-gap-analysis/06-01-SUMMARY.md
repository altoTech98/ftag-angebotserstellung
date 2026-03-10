---
phase: 06-gap-analysis
plan: 01
subsystem: ai
tags: [gap-analysis, opus, tfidf, pydantic, safety-escalation, german-prompts]

requires:
  - phase: 04-matching
    provides: MatchResult, MatchDimension, CatalogTfidfIndex
  - phase: 05-adversarial
    provides: AdversarialResult, ValidationStatus, DimensionCoT

provides:
  - GapDimension enum (6 values, 1:1 with MatchDimension)
  - GapItem with dual suggestions and cross-references
  - AlternativeProduct with geschlossene_gaps
  - GapReport with validation_status
  - GapAnalysisResponse structured output model for Opus
  - apply_safety_escalation function
  - analyze_gaps and analyze_single_position_gaps async functions
  - German gap analysis prompt templates
  - Gap-weighted TF-IDF alternative search

affects: [06-02, 07-output-generation, 08-integration]

tech-stack:
  added: []
  patterns: [three-track-gap-processing, safety-auto-escalation, gap-weighted-tfidf, bidirectional-cross-references]

key-files:
  created:
    - backend/v2/gaps/gap_analyzer.py
    - backend/v2/gaps/gap_prompts.py
  modified:
    - backend/v2/schemas/gaps.py
    - backend/v2/gaps/__init__.py
    - backend/tests/test_v2_gaps.py

key-decisions:
  - "GapDimension replaces NORM with BRANDSCHUTZ+SCHALLSCHUTZ for 1:1 MatchDimension parity"
  - "Dual suggestions pattern: kundenvorschlag (sales) + technischer_hinweis (engineering)"
  - "Three-track processing: bestaetigt (filtered dims), unsicher (full), abgelehnt (text only)"
  - "Safety auto-escalation as deterministic post-processing (not AI-decided)"
  - "Gap-weighted TF-IDF with 2x boost multiplier for gap dimensions"
  - "Abgelehnt alternatives filtered to >30% gap coverage minimum"

patterns-established:
  - "Three-track processing: route logic by ValidationStatus enum value"
  - "Bidirectional cross-references: gap_geschlossen_durch <-> geschlossene_gaps"
  - "GapAnalysisResponse as internal Opus output model separate from final GapReport"

requirements-completed: [GAPA-01, GAPA-02, GAPA-03, GAPA-04, GAPA-05]

duration: 8min
completed: 2026-03-10
---

# Phase 6 Plan 1: Gap Analysis Engine Summary

**Three-track gap analyzer with safety auto-escalation, German Opus prompts, gap-weighted TF-IDF alternatives, and bidirectional cross-references**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-10T18:53:39Z
- **Completed:** 2026-03-10T19:02:05Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Expanded GapDimension to 6 values matching MatchDimension exactly (replaced NORM with BRANDSCHUTZ + SCHALLSCHUTZ)
- Built three-track gap analysis engine: bestaetigt (non-perfect dims only), unsicher (full analysis), abgelehnt (text summary)
- Safety auto-escalation: MINOR never allowed for Brandschutz/Schallschutz
- Gap-weighted TF-IDF alternative search with 2x boost for gap dimensions
- 25 tests passing: schema validation, safety escalation, mocked Opus calls, alternative search

## Task Commits

Each task was committed atomically:

1. **Task 1: Expand gap schemas and create test suite** - `71d921c` (feat, TDD)
2. **Task 2: Build gap analyzer engine and German prompts** - `ab35a52` (feat)

## Files Created/Modified
- `backend/v2/schemas/gaps.py` - Expanded schemas: 6 GapDimensions, dual suggestions, cross-references, GapAnalysisResponse, apply_safety_escalation
- `backend/v2/gaps/gap_analyzer.py` - Gap analysis engine with three-track processing, alternative search, cross-references
- `backend/v2/gaps/gap_prompts.py` - German system/user prompt templates for standard and abgelehnt tracks
- `backend/v2/gaps/__init__.py` - Public exports: analyze_gaps, analyze_single_position_gaps
- `backend/tests/test_v2_gaps.py` - 25 tests: schemas, escalation, analyzer, alternatives

## Decisions Made
- GapDimension replaces NORM with BRANDSCHUTZ+SCHALLSCHUTZ for exact 1:1 MatchDimension parity
- Dual suggestions pattern: kundenvorschlag for sales team, technischer_hinweis for engineering
- Safety auto-escalation is deterministic post-processing (model_copy with update), not AI-decided
- GapAnalysisResponse is separate internal model for Opus structured output, converted to GapItem list post-parse
- Abgelehnt track uses client.messages.create (plain text) instead of messages.parse (no structured output needed)
- Gap-weighted TF-IDF boost multiplier set to 2.0 (doubles repetition for gap dimension fields)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Test file initially blocked by .gitignore -- used `git add -f` to force-add (no plan deviation, just git config)

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Gap analysis schemas and engine ready for 06-02 (output formatting / Excel gap report generation)
- All public API (analyze_gaps, analyze_single_position_gaps) exported and tested
- Cross-reference pattern established for downstream report generation

---
*Phase: 06-gap-analysis*
*Completed: 2026-03-10*
