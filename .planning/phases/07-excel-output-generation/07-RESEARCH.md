# Phase 7: Excel Output Generation - Research

**Researched:** 2026-03-10
**Domain:** openpyxl Excel generation, FastAPI async endpoints, Claude AI structured output
**Confidence:** HIGH

## Summary

Phase 7 transforms the v2 pipeline output (MatchResult, AdversarialResult, GapReport) into a professional 4-sheet Excel file for sales team use. The project already has a mature v1 Excel generator (`result_generator.py`, 934 lines) using openpyxl 3.1.5, plus established patterns for job_store background processing, memory_cache byte storage, and FastAPI download endpoints. The new v2 generator consumes Pydantic schema objects directly rather than raw dicts.

The core challenge is mapping three separate schema hierarchies (matching, adversarial, gap) into four coherent Excel sheets with proper color coding, cell comments for Chain-of-Thought reasoning, and an AI-generated Executive Summary. openpyxl 3.1.5 (already installed) supports all needed features: Comment objects for cell notes, sheet tab colors, frozen panes, auto-filters, and rich styling.

**Primary recommendation:** Build `backend/v2/output/excel_generator.py` as a single module with four private sheet-writer functions, reusing v1's `_auto_row_height` helper. Wire it through the existing offer router pattern (POST generate -> job_store -> cache bytes -> GET download). Use `anthropic` `messages.parse()` with a Pydantic response model for the Executive Summary AI call.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Sheet 1 "Uebersicht": One row per door position with Pos-Nr, Bezeichnung, Status, bestes Produkt, Konfidenz%, Anzahl Gaps, Quelle columns; color-coded status cells
- Sheet 2 "Details": One row per position with Pos-Nr, Produkt, Gesamt-Konfidenz, then one column per dimension (Masse, Brandschutz, Schallschutz, Material, Zertifizierung, Leistung) with score + short reasoning; full CoT in cell comments
- Sheet 3 "Gap-Analyse": One row per individual gap item (multiple rows per position); columns: Pos-Nr, Dimension, Schweregrad, Anforderung, Katalog, Abweichung, Kundenvorschlag, Technischer Hinweis, Alternative Produkte
- Sheet 4 "Executive Summary": Statistics section + AI-generated German overall assessment paragraph (Claude call) + AI-generated top 3-5 recommendations
- Color coding: Green (#C6EFCE) for 95%+ match, Yellow (#FFEB9C) for 60-95% partial, Red (#FFC7CE) for <60% no match; Severity: Kritisch=dark red, Major=orange/amber, Minor=light yellow
- Professional styling: frozen header rows, auto-filter, auto-fitted column widths, sheet tab colors, alternating row shading
- Sales-relevant fields only (no internal IDs, raw TF-IDF scores, or adversarial FOR/AGAINST details)
- Condensed reasoning in cells, full CoT as Excel cell comments
- API: Reuse job_store + memory_cache pattern; API accepts analysis_id to look up stored pipeline results
- Filename format: Machbarkeitsanalyse_{date}_{id}.xlsx
- Cache TTL: 1 hour (3600s)
- Endpoints: POST /api/offer/generate, GET /api/offer/{id}/download

### Claude's Discretion
- Exact openpyxl styling implementation (fonts, borders, header design)
- FTAG branding details if available (otherwise professional neutral)
- Executive Summary AI prompt design (German, professional tone)
- Column width calculations and row height auto-sizing
- How to structure the analysis_id lookup (in-memory dict vs DB query)
- Sheet tab color assignments

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| EXEL-01 | Sheet 1 "Uebersicht" with all requirements and match status (green/yellow/red) | MatchResult.hat_match + AdversarialResult.adjusted_confidence drive status; openpyxl PatternFill for colors |
| EXEL-02 | Sheet 2 "Details" with requirement-to-product mapping, confidence, dimensional breakdown, reasoning | MatchResult.bester_match.dimension_scores for per-dimension; AdversarialResult.per_dimension_cot for CoT comments |
| EXEL-03 | Sheet 3 "Gap-Analyse" with non-matches, gap reasons, deviations, severity, alternatives | GapReport.gaps (list[GapItem]) directly maps to rows; GapReport.alternativen for alternative products |
| EXEL-04 | Sheet 4 "Executive Summary" with statistics, overall assessment, recommendations | Aggregation from all results + Claude Sonnet API call for German text generation |
| EXEL-05 | Color-coding: green (95%+), yellow (60-95%), red (<60%) | openpyxl PatternFill with exact hex colors from CONTEXT.md |
| EXEL-06 | Every decision cell explains WHY | Cell comments via openpyxl.comments.Comment for full CoT; short reasoning in cell value |
| APII-04 | POST /api/offer/generate creates 4-sheet Excel | Extend offer.py router; use job_store + run_in_background pattern |
| APII-05 | GET /api/offer/{id}/download delivers generated Excel | Reuse existing download_result pattern from offer.py with offer_cache |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| openpyxl | 3.1.5 | Excel .xlsx generation with rich formatting | Already installed; supports Comments, PatternFill, freeze_panes, auto_filter, tab colors |
| anthropic | >=0.49.0 | Claude API for Executive Summary generation | Already installed; messages.parse() for structured Pydantic output |
| FastAPI | >=0.115.0 | API endpoints for generate/download | Already installed; existing router patterns |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| io.BytesIO | stdlib | In-memory Excel bytes (no disk writes) | Always -- established v1 pattern |
| openpyxl.comments.Comment | 3.1.5 | Cell notes/tooltips for CoT reasoning | Sheet 2 dimension cells, any reasoning cell |
| datetime | stdlib | Filename timestamps, sheet dates | Filename format and header dates |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| openpyxl | xlsxwriter | xlsxwriter is write-only (no read), already have openpyxl patterns; no benefit to switch |
| In-memory dict for analysis_id | SQLite/Redis | Overkill for single-process dev; dict matches _tenders pattern from upload_v2.py |

**Installation:**
```bash
# No new dependencies needed -- all already in requirements.txt
```

## Architecture Patterns

### Recommended Project Structure
```
backend/v2/output/
    __init__.py          # Already exists (empty)
    excel_generator.py   # NEW: Main 4-sheet generator (public API)

backend/routers/
    offer.py             # EXTEND: Add v2 generate/download endpoints
```

### Pattern 1: Schema-to-Sheet Mapping
**What:** Each sheet writer receives typed Pydantic objects, not raw dicts
**When to use:** All four sheet writers
**Example:**
```python
from openpyxl.comments import Comment
from v2.schemas.matching import MatchResult, DimensionScore
from v2.schemas.adversarial import AdversarialResult, DimensionCoT
from v2.schemas.gaps import GapReport, GapItem, GapSeverity

def _write_uebersicht_sheet(
    wb: Workbook,
    match_results: list[MatchResult],
    adversarial_results: list[AdversarialResult],
    gap_reports: list[GapReport],
) -> None:
    """Sheet 1: One row per position with status overview."""
    ...
```

### Pattern 2: Analysis Results Store
**What:** In-memory dict keyed by analysis_id stores pipeline results for later Excel generation
**When to use:** Decouples analyze endpoint from Excel generation
**Example:**
```python
# In analyze_v2.py -- store after pipeline completes
_analysis_results: dict[str, dict] = {}

# After pipeline:
analysis_id = str(uuid.uuid4())[:8]
_analysis_results[analysis_id] = {
    "match_results": match_results,
    "adversarial_results": adversarial_results,
    "gap_reports": gap_reports,
    "positions": result.positionen,
    "created_at": datetime.now(),
}
response["analysis_id"] = analysis_id
```

### Pattern 3: Background Job + Cache Bytes
**What:** Excel generation runs in background thread, caches bytes in offer_cache
**When to use:** POST /api/offer/generate endpoint
**Example:**
```python
# Reuse existing pattern from offer.py
from services.job_store import create_job, run_in_background
from services.memory_cache import offer_cache

def _run_excel_generation(analysis_id: str) -> dict:
    results = _analysis_results[analysis_id]
    xlsx_bytes = generate_v2_excel(
        match_results=results["match_results"],
        adversarial_results=results["adversarial_results"],
        gap_reports=results["gap_reports"],
        positions=results["positions"],
    )
    cache_key = f"v2_result_{analysis_id}_xlsx"
    offer_cache.set(cache_key, xlsx_bytes, ttl_seconds=3600)
    return {"result_id": analysis_id, "has_result": True}
```

### Pattern 4: Cell Comment for CoT
**What:** Full Chain-of-Thought reasoning stored as Excel cell comment (tooltip on hover)
**When to use:** Sheet 2 dimension score cells
**Example:**
```python
from openpyxl.comments import Comment

# Short text in cell, full CoT in comment
cell.value = f"{score:.0%} - {short_reason}"
if full_cot_reasoning:
    cell.comment = Comment(
        text=full_cot_reasoning,
        author="FTAG KI-Analyse",
        height=150,
        width=300,
    )
```

### Pattern 5: Executive Summary via messages.parse()
**What:** Claude Sonnet generates German executive summary as structured Pydantic output
**When to use:** Sheet 4 content generation
**Example:**
```python
import anthropic
from pydantic import BaseModel, Field

class ExecutiveSummaryResponse(BaseModel):
    gesamtbewertung: str = Field(description="Overall assessment paragraph in German")
    empfehlungen: list[str] = Field(description="3-5 recommendations for the customer")

client = anthropic.Anthropic()
response = client.messages.parse(
    model="claude-sonnet-4-20250514",
    max_tokens=2000,
    system="Du bist ein Experte fuer Tueren und Brandschutz...",
    messages=[{"role": "user", "content": summary_prompt}],
    output_format=ExecutiveSummaryResponse,
)
summary = response.parsed
```

### Anti-Patterns to Avoid
- **Writing to disk:** Always return `io.BytesIO().getvalue()` bytes, never write temp files
- **Raw dict access on schemas:** Use `.model_dump()` only at API boundary, not inside generator; work with typed objects
- **Blocking the event loop:** Excel generation is sync (openpyxl); wrap with `asyncio.to_thread` or use `run_in_background` thread
- **Exposing internal data:** Do NOT include raw adversarial FOR/AGAINST debate text, TF-IDF scores, or internal IDs in the Excel output

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Row height calculation | Custom height logic | Reuse `_auto_row_height` from result_generator.py | Already handles multi-line text wrapping, tested in production |
| Background job management | Custom threading | `job_store.create_job` + `run_in_background` | Handles timeout, concurrent limits, SSE notifications |
| Byte caching with TTL | Custom dict with cleanup | `offer_cache` from memory_cache.py | Thread-safe, LRU eviction, TTL, stats tracking |
| Excel cell comments | Manual XML manipulation | `openpyxl.comments.Comment(text, author)` | Built into openpyxl, handles sizing and formatting |
| Structured AI output | JSON parsing + validation | `messages.parse()` with Pydantic model | Type-safe, automatic retry on parse failure |

**Key insight:** This phase is primarily a data transformation layer (Pydantic schemas -> Excel cells). Nearly all infrastructure (caching, jobs, API patterns) already exists from v1. The new code is the four sheet-writer functions and the Executive Summary prompt.

## Common Pitfalls

### Pitfall 1: Position-to-Result Joining
**What goes wrong:** MatchResult, AdversarialResult, and GapReport are separate lists keyed by positions_nr. If joining is done naively, mismatches occur when some positions lack adversarial or gap results.
**Why it happens:** Adversarial can be skipped, gap analysis may fail for individual positions. Lists may have different lengths.
**How to avoid:** Build a `dict[str, ...]` lookup by positions_nr for each result type. Default to None/empty when a position lacks a result.
**Warning signs:** IndexError, positions showing wrong data, missing rows.

### Pitfall 2: Comment Text Length
**What goes wrong:** openpyxl Comments with very long text (>32000 chars) can cause Excel corruption or extremely slow file opening.
**Why it happens:** Full Chain-of-Thought for complex positions with triple-check can be very verbose.
**How to avoid:** Truncate comment text to a maximum (e.g., 2000 characters) with a "..." truncation indicator.
**Warning signs:** Generated Excel files taking >10 seconds to open.

### Pitfall 3: Color Threshold Mismatch
**What goes wrong:** The color thresholds (95%+ green, 60-95% yellow, <60% red) don't align with AdversarialResult.adjusted_confidence which may differ from MatchResult.gesamt_konfidenz.
**Why it happens:** Adversarial review adjusts confidence. The "official" confidence for color coding should be the post-adversarial score.
**How to avoid:** Always use `adversarial_result.adjusted_confidence` when available, falling back to `match_result.bester_match.gesamt_konfidenz` only when adversarial was skipped.
**Warning signs:** Green-coded rows that actually have significant gaps.

### Pitfall 4: Sync Claude Call in Background Thread
**What goes wrong:** The Executive Summary requires a Claude API call. If called from the background thread (which is sync), the `anthropic.Anthropic()` sync client must be used, not the async one.
**Why it happens:** `run_in_background` runs in a regular `threading.Thread`, not an async context.
**How to avoid:** Use the sync `anthropic.Anthropic().messages.parse()` directly in the background thread function. Do NOT try to use `await` or async client.
**Warning signs:** RuntimeError about no running event loop.

### Pitfall 5: Missing Gap Reports for Matched Positions
**What goes wrong:** Gap analysis only runs for positions with adversarial status `unsicher` or `abgelehnt`. Positions with `bestaetigt` (confirmed at 95%+) have no GapReport. Sheet 1 must still show these as green with 0 gaps.
**Why it happens:** Gap analysis is filtered by validation_status in Phase 6.
**How to avoid:** When building Sheet 1 rows, check if a GapReport exists. If not, default to 0 gaps.
**Warning signs:** Confirmed positions appearing with "N/A" in gap count column.

### Pitfall 6: German Encoding in Excel
**What goes wrong:** Umlauts (ae, oe, ue) and special characters display incorrectly.
**Why it happens:** openpyxl handles UTF-8 natively for .xlsx, but string formatting bugs can mangle characters.
**How to avoid:** All column headers and status text should use proper German characters directly (Uebersicht, not Übersicht, per context decision on sheet name). Verify with a test that opens the file.
**Warning signs:** Mojibake characters in Excel output.

## Code Examples

### Verified: openpyxl Comment Assignment
```python
# Source: openpyxl official docs (https://openpyxl.readthedocs.io/en/stable/comments.html)
from openpyxl.comments import Comment

comment = Comment("Full Chain-of-Thought reasoning text here...", "FTAG KI-Analyse")
comment.width = 300  # pixels
comment.height = 150  # pixels
cell.comment = comment
```

### Verified: Sheet Tab Color
```python
# Source: openpyxl docs (https://openpyxl.readthedocs.io/en/stable/worksheet_properties.html)
ws.sheet_properties.tabColor = "C6EFCE"  # green tab for Uebersicht
```

### Verified: Traffic Light Color Fills
```python
# From CONTEXT.md locked decisions
from openpyxl.styles import PatternFill

GREEN_FILL = PatternFill("solid", fgColor="C6EFCE")   # 95%+ match
YELLOW_FILL = PatternFill("solid", fgColor="FFEB9C")  # 60-95% partial
RED_FILL = PatternFill("solid", fgColor="FFC7CE")     # <60% no match

# Severity fills
KRITISCH_FILL = PatternFill("solid", fgColor="C00000")  # dark red
MAJOR_FILL = PatternFill("solid", fgColor="FFC000")     # orange/amber
MINOR_FILL = PatternFill("solid", fgColor="FFF2CC")     # light yellow
```

### Verified: Confidence-to-Status Mapping
```python
def _confidence_to_status(confidence: float) -> tuple[str, PatternFill, Font]:
    """Map confidence score to display status, fill color, and font."""
    if confidence >= 0.95:
        return "MATCH", GREEN_FILL, Font(color="006100", bold=True)
    elif confidence >= 0.60:
        return "TEILWEISE", YELLOW_FILL, Font(color="9C6500", bold=True)
    else:
        return "KEIN MATCH", RED_FILL, Font(color="9C0006", bold=True)
```

### Verified: In-Memory Bytes Pattern (from v1 result_generator.py)
```python
import io
import openpyxl

wb = openpyxl.Workbook()
# ... build sheets ...
buf = io.BytesIO()
wb.save(buf)
return buf.getvalue()  # Returns bytes, no disk writes
```

### Data Flow: Schema Fields to Sheet Columns

**Sheet 1 (Uebersicht) column mapping:**
| Column | Source |
|--------|--------|
| Pos-Nr | MatchResult.positions_nr |
| Bezeichnung | ExtractedDoorPosition.positions_bezeichnung |
| Status | Derived from AdversarialResult.adjusted_confidence thresholds |
| Bestes Produkt | MatchResult.bester_match.produkt_name |
| Konfidenz% | AdversarialResult.adjusted_confidence * 100 |
| Anzahl Gaps | len(GapReport.gaps) or 0 if no report |
| Quelle | ExtractedDoorPosition.quellen (first document name) |

**Sheet 2 (Details) column mapping:**
| Column | Source |
|--------|--------|
| Pos-Nr | MatchResult.positions_nr |
| Produkt | MatchResult.bester_match.produkt_name |
| Gesamt-Konfidenz | AdversarialResult.adjusted_confidence |
| Masse | DimensionScore where dimension=MASSE (.score in cell, .begruendung + DimensionCoT.reasoning in comment) |
| Brandschutz | DimensionScore where dimension=BRANDSCHUTZ |
| Schallschutz | DimensionScore where dimension=SCHALLSCHUTZ |
| Material | DimensionScore where dimension=MATERIAL |
| Zertifizierung | DimensionScore where dimension=ZERTIFIZIERUNG |
| Leistung | DimensionScore where dimension=LEISTUNG |

**Sheet 3 (Gap-Analyse) column mapping:**
| Column | Source |
|--------|--------|
| Pos-Nr | GapReport.positions_nr |
| Dimension | GapItem.dimension.value |
| Schweregrad | GapItem.schweregrad.value |
| Anforderung | GapItem.anforderung_wert |
| Katalog | GapItem.katalog_wert |
| Abweichung | GapItem.abweichung_beschreibung |
| Kundenvorschlag | GapItem.kundenvorschlag |
| Technischer Hinweis | GapItem.technischer_hinweis |
| Alternative Produkte | GapReport.alternativen (formatted as "name (coverage%)" list) |

## State of the Art

| Old Approach (v1) | Current Approach (v2) | Impact |
|--------------------|----------------------|--------|
| Raw dict data from matching | Typed Pydantic schemas (MatchResult, AdversarialResult, GapReport) | Type-safe column mapping, no KeyError risk |
| 2-sheet Excel (Tuermatrix + GAP) | 4-sheet Excel (Uebersicht + Details + Gap-Analyse + Executive Summary) | Richer output for sales team |
| No reasoning in output | Cell comments with full CoT | EXEL-06 compliance: every decision explains WHY |
| Keyword matching only | Multi-dimensional confidence with adversarial validation | Color coding reflects validated confidence |
| No AI-generated summary | Claude Sonnet generates German executive summary | Professional output for management |

## Open Questions

1. **Analysis results storage location**
   - What we know: analyze_v2.py currently returns results directly in the response dict. There is no persistent storage of analysis results.
   - What's unclear: Where to store results so offer/generate can look them up by analysis_id. Options: (a) add `_analysis_results` dict in analyze_v2.py, (b) use memory_cache, (c) store in _tenders dict.
   - Recommendation: Use a module-level dict in analyze_v2.py (`_analysis_results`), similar to `_tenders` pattern. Add analysis_id to the analyze response. TTL cleanup optional since offer_cache handles byte caching.

2. **Executive Summary prompt calibration**
   - What we know: Must be German, professional tone, include statistics and 3-5 recommendations.
   - What's unclear: Exact prompt wording and how much context to include (full gap list vs. summary statistics only).
   - Recommendation: Pass aggregated statistics + top 5 most critical gaps as context. Keep prompt under 2000 tokens for cost efficiency. Use Claude Sonnet (not Opus) per context decision.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 7.4.4 + pytest-asyncio 0.23.3 |
| Config file | backend/tests/ directory with conftest.py + conftest_v2.py |
| Quick run command | `cd backend && python -m pytest tests/test_v2_excel_output.py -x -v` |
| Full suite command | `cd backend && python -m pytest tests/ -x -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EXEL-01 | Sheet 1 has correct columns, one row per position, color-coded status | unit | `python -m pytest tests/test_v2_excel_output.py::test_uebersicht_sheet -x` | Wave 0 |
| EXEL-02 | Sheet 2 has dimension columns with scores and comments | unit | `python -m pytest tests/test_v2_excel_output.py::test_details_sheet -x` | Wave 0 |
| EXEL-03 | Sheet 3 has gap rows with severity and alternatives | unit | `python -m pytest tests/test_v2_excel_output.py::test_gap_analyse_sheet -x` | Wave 0 |
| EXEL-04 | Sheet 4 has statistics and AI-generated text | unit | `python -m pytest tests/test_v2_excel_output.py::test_executive_summary_sheet -x` | Wave 0 |
| EXEL-05 | Cells use correct color fills for thresholds | unit | `python -m pytest tests/test_v2_excel_output.py::test_color_coding -x` | Wave 0 |
| EXEL-06 | Decision cells have comments with reasoning | unit | `python -m pytest tests/test_v2_excel_output.py::test_cell_comments -x` | Wave 0 |
| APII-04 | POST /api/offer/generate returns job_id | integration | `python -m pytest tests/test_v2_excel_output.py::test_generate_endpoint -x` | Wave 0 |
| APII-05 | GET /api/offer/{id}/download returns xlsx bytes | integration | `python -m pytest tests/test_v2_excel_output.py::test_download_endpoint -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/test_v2_excel_output.py -x -v`
- **Per wave merge:** `cd backend && python -m pytest tests/ -x -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_v2_excel_output.py` -- covers EXEL-01 through EXEL-06, APII-04, APII-05
- [ ] Test fixtures: sample MatchResult, AdversarialResult, GapReport objects in conftest_v2.py
- [ ] Mock for Claude API call in Executive Summary tests (avoid real API calls in tests)

## Sources

### Primary (HIGH confidence)
- openpyxl 3.1.5 already installed in project (`requirements.txt` pinned)
- [openpyxl Comments docs](https://openpyxl.readthedocs.io/en/stable/comments.html) -- Comment(text, author, height, width)
- [openpyxl Worksheet Properties](https://openpyxl.readthedocs.io/en/stable/worksheet_properties.html) -- tabColor, freeze_panes
- v1 `result_generator.py` (934 lines) -- verified patterns for styling, _auto_row_height, in-memory bytes
- v2 schemas: `matching.py`, `adversarial.py`, `gaps.py` -- exact field names and types
- `offer.py` router -- existing job_store + cache + download pattern
- `memory_cache.py` -- offer_cache with TTL, thread-safe

### Secondary (MEDIUM confidence)
- [openpyxl Filters docs](https://openpyxl.readthedocs.io/en/3.1.1/filters.html) -- auto_filter.ref usage

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already installed and used in v1
- Architecture: HIGH -- patterns directly visible in existing codebase (offer.py, result_generator.py)
- Pitfalls: HIGH -- derived from actual code inspection (schema structure, async patterns, data flow)
- Data mapping: HIGH -- exact field names verified from Pydantic schema source code

**Research date:** 2026-03-10
**Valid until:** 2026-04-10 (stable -- no external dependencies changing)
