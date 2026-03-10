# Phase 7: Excel Output Generation - Context

**Gathered:** 2026-03-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Export the complete v2 analysis pipeline output (matches, gaps, reasoning) as a professional 4-sheet Excel file that the sales team can send directly to customers. Includes API endpoints for generation and download. The Excel replaces v1's 2-sheet result_generator.py with a 4-sheet version consuming v2 pipeline data (MatchResult, AdversarialResult, GapReport).

</domain>

<decisions>
## Implementation Decisions

### Sheet 1: Uebersicht
- One row per door position (compact at-a-glance view)
- Columns: Pos-Nr, Bezeichnung, Status (Match/Partial/No Match), bestes Produkt, Konfidenz%, Anzahl Gaps, Quelle (source document)
- Color-coded status cells per row

### Sheet 2: Details
- One row per position, dimensions as columns
- Columns: Pos-Nr, Produkt, Gesamt-Konfidenz, then one column per dimension (Masse, Brandschutz, Schallschutz, Material, Zertifizierung, Leistung) showing score + short reasoning
- Condensed reasoning in cell, full Chain-of-Thought in Excel cell comment/note (tooltip)

### Sheet 3: Gap-Analyse
- One row per individual gap item (multiple rows per position possible)
- Columns: Pos-Nr, Dimension, Schweregrad, Anforderung (required), Katalog (actual), Abweichung, Kundenvorschlag, Technischer Hinweis, Alternative Produkte

### Sheet 4: Executive Summary
- Statistics section: total positions, match rate, gap count by severity, dimension breakdown
- AI-generated German-language overall assessment paragraph (Claude call)
- AI-generated top 3-5 recommendations for the customer
- Presentation-ready for management

### Color Coding & Styling
- Client-facing polished quality — professional headers, clean borders, alternating row shading
- Traffic light status colors: Green (#C6EFCE) for 95%+ match, Yellow (#FFEB9C) for 60-95% partial, Red (#FFC7CE) for <60% no match
- Severity cells also color-coded: Kritisch = dark red, Major = orange/amber, Minor = light yellow
- Frozen header row on each sheet, auto-filter on all data columns, auto-fitted column widths, sheet tab colors
- Full navigation aids for easy sales team use

### Data Scope
- Sales-relevant fields only — no internal IDs, raw TF-IDF scores, or adversarial FOR/AGAINST details
- Source document info (Quelle) included on Uebersicht for traceability
- Condensed reasoning visible in cells, full CoT as Excel cell comments

### API & Download Flow
- Reuse existing job_store + memory_cache pattern (POST returns job_id, poll status, then download)
- API accepts analysis_id to look up stored pipeline results (not full data in request body)
- Filename format: Machbarkeitsanalyse_{date}_{id}.xlsx
- Cache TTL: 1 hour (3600s) for generated Excel files
- Endpoints: POST /api/offer/generate, GET /api/offer/{id}/download (match APII-04, APII-05)

### Claude's Discretion
- Exact openpyxl styling implementation (fonts, borders, header design)
- FTAG branding details if available (otherwise professional neutral)
- Executive Summary AI prompt design (German, professional tone)
- Column width calculations and row height auto-sizing
- How to structure the analysis_id lookup (in-memory dict vs DB query)
- Sheet tab color assignments

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/services/result_generator.py`: v1 Excel generator (2-sheet) with openpyxl — patterns for _auto_row_height, _clean_reason, styling helpers
- `backend/v2/output/__init__.py`: Empty v2 output module ready for new Excel generator
- `backend/v2/schemas/gaps.py`: GapReport, GapItem, AlternativeProduct, GapSeverity, GapDimension — direct input for Sheet 3
- `backend/v2/schemas/matching.py`: MatchResult, MatchCandidate, DimensionScore — input for Sheet 1 & 2
- `backend/v2/schemas/adversarial.py`: AdversarialResult with per-dimension CoT — input for reasoning columns
- `backend/services/memory_cache.py`: offer_cache with TTL — reuse for generated Excel storage
- `backend/services/job_store.py`: create_job, get_job, run_in_background — reuse for async generation
- `backend/routers/offer.py`: v1 result router with generate/status/download — extend or create v2 equivalent

### Established Patterns
- In-memory bytes return (no disk writes) — v1 result_generator pattern
- `asyncio.to_thread` for sync operations in async context
- German labels throughout (all prompts, column headers, status text)
- Lazy imports with _AVAILABLE guard for graceful degradation
- `messages.parse()` with Pydantic for structured AI outputs (for Executive Summary generation)

### Integration Points
- `backend/v2/output/` — new module: excel_generator.py (main generator)
- `backend/v2/routers/analyze_v2.py` — store pipeline results for later Excel generation
- `backend/routers/offer.py` — add v2 generation endpoint or create new v2 offer router
- Pipeline flow: analyze endpoint stores results -> offer/generate looks up by analysis_id -> generates Excel -> caches bytes -> download endpoint serves

</code_context>

<specifics>
## Specific Ideas

- v1's _auto_row_height helper is reusable for dynamic row sizing in the new generator
- Executive Summary AI call should use Claude Sonnet (not Opus) since it's text generation, not critical analysis
- The 4-sheet structure directly maps to the 4 requirements blocks (EXEL-01 through EXEL-04)
- Cell comments for full CoT keep the sheet scannable while preserving EXEL-06 (every decision cell explains WHY)
- analysis_id lookup decouples Excel generation from analyze endpoint — can regenerate without re-analyzing

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 07-excel-output-generation*
*Context gathered: 2026-03-10*
