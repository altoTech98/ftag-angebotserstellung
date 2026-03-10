---
phase: 02-multi-pass-extraction
plan: 01
subsystem: extraction
tags: [regex, heuristics, chunking, dedup, prompts, pydantic, tdd]

# Dependency graph
requires:
  - phase: 01-document-parsing
    provides: "ParseResult, KNOWN_FIELD_PATTERNS, _MIN_DOOR_FIELDS from xlsx_parser"
provides:
  - "extract_structural: regex/heuristic Pass 1 extraction from ParseResult"
  - "chunk_by_pages: page-based text chunking with overlap for AI passes"
  - "merge_positions: field-level dedup with later-pass-wins and provenance"
  - "ai_dedup_cluster: AI-based position clustering for ambiguous cases"
  - "PASS2/PASS3/DEDUP prompt templates in German"
affects: [02-02-pipeline-orchestrator, 02-03-ai-passes, matching]

# Tech tracking
tech-stack:
  added: []
  patterns: [pipe-delimited-text-parsing, markdown-table-parsing, field-level-provenance, later-pass-wins-merge]

key-files:
  created:
    - backend/v2/extraction/pass1_structural.py
    - backend/v2/extraction/chunking.py
    - backend/v2/extraction/dedup.py
    - backend/v2/extraction/prompts.py
    - backend/tests/test_v2_pass1.py
    - backend/tests/test_v2_chunking.py
    - backend/tests/test_v2_dedup.py
  modified:
    - backend/v2/extraction/__init__.py

key-decisions:
  - "Pass 1 uses pipe-delimited text from XLSX parser (canonical field names) rather than re-parsing Excel"
  - "Dedup pre-filter uses exact positions_nr match; AI clustering reserved for ambiguous cases"
  - "All prompts in German matching domain language for Swiss tender documents"

patterns-established:
  - "FieldSource provenance: every Pass 1 field tagged with konfidenz=0.8"
  - "Later-pass-wins merge: field conflicts resolved by pass_priority, None values filled from earlier passes"
  - "Chunking contract: returns list[dict] with text/start_page/end_page keys"

requirements-completed: [DOKA-05, DOKA-06]

# Metrics
duration: 6min
completed: 2026-03-10
---

# Phase 02 Plan 01: Extraction Foundations Summary

**Pass 1 structural extraction (regex), page-based chunking, field-level dedup with provenance, and German AI prompt templates for Pass 2/3**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-10T13:22:33Z
- **Completed:** 2026-03-10T13:28:24Z
- **Tasks:** 3
- **Files modified:** 8

## Accomplishments
- Pass 1 extracts door positions from XLSX pipe-delimited text and PDF markdown tables using regex/heuristics (no AI cost)
- Page-based chunking splits documents into overlapping chunks with form-feed, page-marker, and estimated splitting
- Dedup merges positions across passes with later-pass-wins conflict resolution and FieldSource provenance tracking
- Complete German-language prompt templates for Pass 2 (semantic extraction), Pass 3 (adversarial validation), and dedup clustering

## Task Commits

Each task was committed atomically:

1. **Task 1: Pass 1 structural extraction + chunking** - `8b95934` (feat, TDD)
2. **Task 2: Dedup module + prompt templates** - `81c4ce4` (feat, TDD)
3. **Task 3: Update extraction __init__.py** - `289f1ee` (feat)

## Files Created/Modified
- `backend/v2/extraction/pass1_structural.py` - Regex/heuristic extraction from XLSX and PDF ParseResults
- `backend/v2/extraction/chunking.py` - Page-based text chunking with overlap support
- `backend/v2/extraction/dedup.py` - Position merging with field-level conflict resolution
- `backend/v2/extraction/prompts.py` - German AI prompt templates for Pass 2, Pass 3, and dedup
- `backend/v2/extraction/__init__.py` - Package exports for all extraction modules
- `backend/tests/test_v2_pass1.py` - 5 tests for structural extraction
- `backend/tests/test_v2_chunking.py` - 5 tests for chunking
- `backend/tests/test_v2_dedup.py` - 10 tests for dedup and prompts

## Decisions Made
- Pass 1 uses pipe-delimited text output from XLSX parser (canonical field names) rather than re-parsing raw Excel bytes
- Dedup pre-filter uses exact positions_nr match; AI clustering is separated into ai_dedup_cluster for ambiguous cases only
- All prompts written in German to match the Swiss tender document domain language
- FieldSource konfidenz set to 0.8 for all Pass 1 extractions (regex confidence)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Test files are matched by .gitignore `test_*` pattern; used `git add -f` to force-add them (consistent with previous phase behavior)

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All extraction building blocks ready for pipeline orchestrator (02-02)
- extract_structural provides fast, free Pass 1 results
- chunking ready to feed document chunks to AI passes
- dedup ready to merge results between passes
- Prompt templates ready for Pass 2 (semantic) and Pass 3 (adversarial) AI calls

## Self-Check: PASSED

All 8 files verified present. All 3 task commits verified in git log.

---
*Phase: 02-multi-pass-extraction*
*Completed: 2026-03-10*
