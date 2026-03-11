---
phase: 13-analysis-wizard-results-view
plan: 03
subsystem: ui
tags: [react, shadcn, analysis, detail-expansion, dimension-bars, comparison-card, wizard-routing]

requires:
  - phase: 13-analysis-wizard-results-view
    provides: wizard shell, types, steps 1-5, results table, server actions
  - phase: 12-file-handling
    provides: project detail page with analyses section
provides:
  - Expandable result detail with AI reasoning, 6-dimension bars, and comparison card
  - Project detail page "Neue Analyse" button and clickable completed analyses
  - analysisId query param -> wizard step 5 direct loading for past results
affects: [13-04-PLAN, 14-catalog-management]

tech-stack:
  added: []
  patterns: [expandable-table-row-detail, dimension-score-derivation, past-result-loading]

key-files:
  created:
    - frontend/src/components/analysis/dimension-bars.tsx
    - frontend/src/components/analysis/comparison-card.tsx
    - frontend/src/components/analysis/result-detail.tsx
  modified:
    - frontend/src/components/analysis/step-results.tsx
    - frontend/src/app/(app)/projekte/[id]/client.tsx
    - frontend/src/app/(app)/projekte/[id]/analyse/page.tsx
    - frontend/src/app/(app)/projekte/[id]/analyse/client.tsx
    - frontend/src/__tests__/analysis/result-detail.test.tsx
    - frontend/src/__tests__/analysis/comparison-card.test.tsx
    - frontend/src/__tests__/analysis/wizard-init.test.tsx

key-decisions:
  - "Dimension scores derived from gap_items/missing_info regex patterns against 6 door categories"
  - "Comparison card uses dynamic field extraction with name-similarity matching between requirement and product"
  - "Past analysis results loaded via analysisId searchParam, wizard initializes at step 5 with all navigation hidden"

patterns-established:
  - "Expandable table row: React.Fragment wraps data row + conditional detail row with colSpan"
  - "Dimension derivation: regex DIMENSION_PATTERNS matched against gap_items/missing_info to adjust base confidence"
  - "Past result viewing: server component fetches saved result from Prisma, passes as initialResult prop"

requirements-completed: [ANLZ-05, RSLT-02, RSLT-03]

duration: 5min
completed: 2026-03-11
---

# Phase 13 Plan 03: Detail Expansion & Project Integration Summary

**Expandable result rows with AI reasoning, 6-dimension confidence bars, two-column comparison cards, and project-level wizard navigation with past-result direct loading**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-11T10:50:56Z
- **Completed:** 2026-03-11T10:56:10Z
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments
- Built dimension-bars.tsx deriving 6 per-dimension scores from gap_items and missing_info regex patterns
- Built comparison-card.tsx with two-column Anforderung vs Produkt layout, field matching, and gap rejection display
- Built result-detail.tsx combining AI reasoning badge, dimension bars, and comparison card into expandable section
- Updated step-results.tsx with inline accordion rows (one expanded at a time, FTAG Red left border accent)
- Wired project detail page with "Neue Analyse starten" button and clickable completed analysis links
- Implemented analysisId query param -> step 5 direct loading for viewing past analysis results
- 10 passing tests across result-detail (4), comparison-card (3), and wizard-init (3)

## Task Commits

Each task was committed atomically:

1. **Task 1: Detail expansion components (reasoning, dimension bars, comparison card)** - `d1021ee` (feat)
2. **Task 2: Wire wizard into project detail page with analysisId loading** - `d22b451` (feat)

## Files Created/Modified
- `frontend/src/components/analysis/dimension-bars.tsx` - 6-dimension horizontal bars with color-coded scores derived from gap patterns
- `frontend/src/components/analysis/comparison-card.tsx` - Two-column requirement vs product comparison with match/mismatch indicators
- `frontend/src/components/analysis/result-detail.tsx` - Expandable detail section combining AI reasoning, dimensions, and comparison
- `frontend/src/components/analysis/step-results.tsx` - Added inline expandable detail rows with React.Fragment pattern
- `frontend/src/app/(app)/projekte/[id]/client.tsx` - Added "Neue Analyse" button and clickable completed analysis links
- `frontend/src/app/(app)/projekte/[id]/analyse/page.tsx` - Added searchParams handling, Prisma analysis fetch, initialResult passing
- `frontend/src/app/(app)/projekte/[id]/analyse/client.tsx` - Added initialResult prop, step 5 direct initialization, hidden navigation
- `frontend/src/__tests__/analysis/result-detail.test.tsx` - 4 tests for AI reasoning, dimensions, comparison, gap entries
- `frontend/src/__tests__/analysis/comparison-card.test.tsx` - 3 tests for layout, match indicators, rejection reasons
- `frontend/src/__tests__/analysis/wizard-init.test.tsx` - 3 tests for initialResult -> step 5, no result -> step 1, hidden back button

## Decisions Made
- Dimension scores derived using regex DIMENSION_PATTERNS (tuertyp, material, brandschutz, masse, ausfuehrung, zubehoer) matched against gap_items and missing_info fields to scale confidence up or down
- Comparison card dynamically extracts fields from original_position and matched_products[0], matching by key name similarity
- Past analysis viewing initializes wizard at step 5 with all 5 steps marked completed, navigation buttons hidden

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Pre-existing Prisma type errors (prisma.project, prisma.analysis, prisma.file) due to Prisma types not generated on local machine -- not caused by our changes, ignored (consistent with Plans 01 and 02)

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Full analysis experience complete: project page -> wizard -> progress -> results with expandable details
- Ready for Plan 04 (polish and accessibility improvements)
- All 3 result detail components export cleanly for reuse

---
*Phase: 13-analysis-wizard-results-view*
*Completed: 2026-03-11*

## Self-Check: PASSED

All 10 key files verified to exist. Both task commits (d1021ee, d22b451) confirmed in git log.
