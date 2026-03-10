---
phase: 01-document-parsing-pipeline-schemas
plan: 01
subsystem: schemas
tags: [pydantic-v2, schemas, pipeline, german-fields, enums, dataclass]

# Dependency graph
requires: []
provides:
  - "V2 package structure with all subpackage placeholders"
  - "55-field ExtractedDoorPosition Pydantic schema with German field names"
  - "Complete pipeline schemas: extraction, matching, validation, gaps, pipeline"
  - "ParseResult dataclass as uniform parser output contract"
  - "V2 exception hierarchy independent from v1"
  - "14 passing schema tests with anthropic compatibility verification"
  - "Test fixtures (conftest_v2.py) for Plan 02 parser tests"
affects: [02-document-parsing-pipeline-schemas, 02-multi-pass-extraction, 04-product-matching, 05-adversarial-validation, 06-gap-analysis]

# Tech tracking
tech-stack:
  added: []
  patterns: ["enum+freitext for extensible classification", "FieldSource provenance tracking per field", "ParseResult as uniform parser output"]

key-files:
  created:
    - backend/v2/__init__.py
    - backend/v2/exceptions.py
    - backend/v2/parsers/base.py
    - backend/v2/schemas/common.py
    - backend/v2/schemas/extraction.py
    - backend/v2/schemas/matching.py
    - backend/v2/schemas/validation.py
    - backend/v2/schemas/gaps.py
    - backend/v2/schemas/pipeline.py
    - backend/tests/conftest_v2.py
    - backend/tests/test_v2_schemas.py
  modified: []

key-decisions:
  - "Extended SchallschutzKlasse enum with Rw 29/35/41/43/44/45/46/53dB values from actual product catalog"
  - "Added OeffnungsArt enum values Ganzglastuer/Rahmentuer/Zargentuer/Futtertuer/Festverglasung from catalog Produktgruppen"
  - "Added MaterialTyp enum values Eiche/Buche/Fichte/Laerche from catalog Umfassung Materialisierung column"
  - "Added Futterzarge to ZargenTyp enum based on catalog Futtertuer product group"

patterns-established:
  - "Enum + freitext pattern: Optional[Enum] = None paired with Optional[str] freitext field for unknown values"
  - "Field descriptions instead of numeric constraints: Pydantic description strings guide Claude, not min/max validators"
  - "Quellen dict pattern: dict[str, FieldSource] maps field names to provenance sources"
  - "ParseResult dataclass (not Pydantic): lightweight parser output without validation overhead"

requirements-completed: [DOKA-01, DOKA-02, DOKA-03]

# Metrics
duration: 5min
completed: 2026-03-10
---

# Phase 1 Plan 01: Pipeline Schemas & V2 Scaffolding Summary

**55-field ExtractedDoorPosition with 6 domain enums derived from product catalog, complete pipeline schemas for all 6 stages, ParseResult contract, and 14 passing tests**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-10T12:27:24Z
- **Completed:** 2026-03-10T12:32:47Z
- **Tasks:** 3
- **Files modified:** 17

## Accomplishments
- Complete `backend/v2/` package with placeholder subpackages for all 6 pipeline stages
- ExtractedDoorPosition with 55 German-named fields covering identification, dimensions, fire/sound protection, material, hardware, standards, and source tracking
- 6 domain enums (BrandschutzKlasse, SchallschutzKlasse, MaterialTyp, ZargenTyp, OeffnungsArt, DokumentTyp) with values derived from actual product catalog analysis
- All schemas validated for anthropic messages.parse() compatibility via JSON Schema generation
- 14 tests passing: creation, serialization round-trip, Optional defaults check, nesting depth verification

## Task Commits

Each task was committed atomically:

1. **Task 1: Create v2 package structure, exceptions, and ParseResult contract** - `8874791` (feat)
2. **Task 2: Define all pipeline Pydantic schemas with German field names** - `c4292ee` (feat)
3. **Task 3: Create test scaffolds and conftest fixtures for v2** - `d0608b6` (test)

## Files Created/Modified
- `backend/v2/__init__.py` - V2 package init with version string
- `backend/v2/exceptions.py` - Independent exception hierarchy (V2Error, ParseError, SchemaValidationError, etc.)
- `backend/v2/parsers/__init__.py` - Parser package re-exports
- `backend/v2/parsers/base.py` - ParseResult dataclass and BaseParser protocol
- `backend/v2/schemas/__init__.py` - Schema package with key type re-exports
- `backend/v2/schemas/common.py` - FieldSource, TrackedField, 6 domain enums
- `backend/v2/schemas/extraction.py` - ExtractedDoorPosition (55 fields), ExtractionResult
- `backend/v2/schemas/matching.py` - MatchResult, MatchCandidate, DimensionScore
- `backend/v2/schemas/validation.py` - AdversarialResult, ValidationOutcome
- `backend/v2/schemas/gaps.py` - GapReport, GapItem, AlternativeProduct
- `backend/v2/schemas/pipeline.py` - AnalysisJob, StageProgress, PipelineStage
- `backend/v2/extraction/__init__.py` - Phase 2 placeholder
- `backend/v2/matching/__init__.py` - Phase 4 placeholder
- `backend/v2/validation/__init__.py` - Phase 5 placeholder
- `backend/v2/gaps/__init__.py` - Phase 6 placeholder
- `backend/v2/output/__init__.py` - Phase 7 placeholder
- `backend/tests/conftest_v2.py` - Test fixtures: sample bytes, mock ParseResult, sample door position
- `backend/tests/test_v2_schemas.py` - 14 schema validation tests

## Decisions Made
- Extended enum values beyond plan specification based on actual product catalog analysis (SchallschutzKlasse gained 7 additional dB values, OeffnungsArt gained 5 product-group-derived values, MaterialTyp gained 4 wood species)
- Added Futterzarge to ZargenTyp to match catalog's Futtertuer product group
- Used `@runtime_checkable` on BaseParser Protocol for isinstance checks in tests

## Deviations from Plan

None - plan executed exactly as written. Enum values were extended based on product catalog analysis as instructed by the plan.

## Issues Encountered

- `.gitignore` pattern `test_*` excluded `test_v2_schemas.py`; used `git add -f` to force-add test files. This is a pre-existing .gitignore configuration that broadly excludes test scripts from the root directory.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- All schemas importable and tested, ready for Plan 02 (document parsers)
- conftest_v2.py fixtures (sample PDF/DOCX/XLSX bytes, mock ParseResult) ready for parser tests
- ParseResult contract established for parser implementations

## Self-Check: PASSED

All 11 files verified present. All 3 task commits verified in git log.

---
*Phase: 01-document-parsing-pipeline-schemas*
*Completed: 2026-03-10*
