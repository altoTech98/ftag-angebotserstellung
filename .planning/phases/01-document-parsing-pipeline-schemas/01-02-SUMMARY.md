---
phase: 01-document-parsing-pipeline-schemas
plan: 02
subsystem: parsers
tags: [pdf, docx, xlsx, parsers, fallback-chain, fuzzy-matching, tdd]

# Dependency graph
requires:
  - "ParseResult dataclass from 01-01"
  - "V2 exception hierarchy from 01-01"
  - "Test fixtures from 01-01 conftest_v2.py"
provides:
  - "PDF parser with pymupdf4llm -> pdfplumber -> OCR fallback chain"
  - "DOCX parser with heading markers and table markdown"
  - "XLSX parser with header auto-detect, fuzzy column matching (23 fields, 200+ aliases)"
  - "Parser router with extension + magic byte format detection"
  - "34 passing v2 tests (14 schemas + 20 parsers)"
affects: [02-multi-pass-extraction, 03-cross-document-linking]

# Tech tracking
tech-stack:
  added: [pymupdf4llm, pdfplumber, pytesseract, python-docx, openpyxl]
  patterns: ["fallback chain (primary -> secondary -> last resort)", "never-raise parser contract", "fuzzy column matching with SequenceMatcher"]

key-files:
  created:
    - backend/v2/parsers/pdf_parser.py
    - backend/v2/parsers/docx_parser.py
    - backend/v2/parsers/xlsx_parser.py
    - backend/v2/parsers/router.py
    - backend/tests/test_v2_pdf_parser.py
    - backend/tests/test_v2_docx_parser.py
    - backend/tests/test_v2_xlsx_parser.py
  modified:
    - backend/v2/parsers/__init__.py
    - backend/tests/conftest.py

key-decisions:
  - "Imported conftest_v2 fixtures via wildcard import in conftest.py rather than renaming file"
  - "XLSX parser saves workbook after unmerge then re-reads with pandas for correct header detection"
  - "Router uses lazy imports to avoid circular dependencies and reduce startup cost"

patterns-established:
  - "Never-raise parser contract: all parsers catch exceptions internally, return ParseResult with warnings"
  - "Fallback chain pattern: try best method first, fall through to alternatives on failure"
  - "TDD RED-GREEN: tests committed before implementation for each parser group"

requirements-completed: [DOKA-01, DOKA-02, DOKA-03]

# Metrics
duration: 6min
completed: 2026-03-10
---

# Phase 1 Plan 02: Document Parsers Summary

**Three document parsers (PDF/DOCX/XLSX) with fallback chains, fuzzy column matching for 23+ door-list fields, and format-detection router -- all returning ParseResult, never raising**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-10T12:35:42Z
- **Completed:** 2026-03-10T12:41:31Z
- **Tasks:** 3
- **Files created:** 7
- **Files modified:** 2

## Accomplishments

- PDF parser with 3-stage fallback: pymupdf4llm (Markdown tables) -> PyMuPDF+pdfplumber -> OCR (pytesseract)
- DOCX parser preserving heading hierarchy (# ## ###) and extracting tables as markdown
- XLSX parser porting v1's battle-tested algorithms: header auto-detect, KNOWN_FIELD_PATTERNS (23 fields, 200+ aliases), fuzzy matching via SequenceMatcher (threshold 0.65), merged cell unmerging, _to_scalar for duplicate columns
- Parser router dispatching by file extension with magic byte fallback (PDF %PDF, ZIP PK with internal structure inspection)
- 34 v2 tests passing (14 schemas + 7 PDF + 5 DOCX + 9 XLSX), 1 skipped (OCR requires tesseract)

## Task Commits

Each task was committed atomically (TDD RED then GREEN):

1. **Task 1 RED: Failing PDF/DOCX tests** - `c47b642` (test)
2. **Task 1 GREEN: PDF and DOCX parsers** - `a36a97a` (feat)
3. **Task 2 RED: Failing XLSX tests** - `8e81a2b` (test)
4. **Task 2 GREEN: XLSX parser** - `d34ac9d` (feat)
5. **Task 3: Parser router + package exports** - `853e8a6` (feat)

## Files Created/Modified

- `backend/v2/parsers/pdf_parser.py` - PDF parsing with pymupdf4llm/pdfplumber/OCR fallback chain
- `backend/v2/parsers/docx_parser.py` - DOCX parsing with heading markers and table extraction
- `backend/v2/parsers/xlsx_parser.py` - XLSX parsing with header auto-detect and 23-field fuzzy matching
- `backend/v2/parsers/router.py` - Format detection router with extension + magic byte detection
- `backend/v2/parsers/__init__.py` - Updated with all parser exports
- `backend/tests/test_v2_pdf_parser.py` - 7 PDF parser tests
- `backend/tests/test_v2_docx_parser.py` - 5 DOCX parser tests
- `backend/tests/test_v2_xlsx_parser.py` - 9 XLSX parser tests
- `backend/tests/conftest.py` - Added v2 fixture import

## Decisions Made

- Imported conftest_v2.py fixtures into main conftest.py via wildcard import (pytest only auto-discovers conftest.py files)
- XLSX parser saves workbook to buffer after unmerge, then re-reads with pandas -- ensures header detection works on clean data
- Router uses lazy imports for parsers to avoid circular dependencies

## Deviations from Plan

None - plan executed exactly as written. All three parsers implemented with specified fallback chains and error handling.

## Issues Encountered

- conftest_v2.py fixtures were not auto-discovered by pytest (only conftest.py is auto-loaded). Fixed by adding wildcard import in conftest.py. [Rule 3 - Blocking: fixture discovery]

## User Setup Required

None - all dependencies already in requirements.txt.

## Next Phase Readiness

- All parsers return ParseResult, ready for Phase 2 (multi-pass extraction)
- XLSX column detection metadata available for downstream field mapping
- Router provides single entry point for document ingestion

## Self-Check: PASSED

All 7 created files verified present. All 5 task commits verified in git log.
