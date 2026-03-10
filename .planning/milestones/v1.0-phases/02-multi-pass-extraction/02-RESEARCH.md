# Phase 2: Multi-Pass Extraction - Research

**Researched:** 2026-03-10
**Domain:** Multi-pass document extraction, AI-structured extraction with Claude, deduplication, multi-file upload
**Confidence:** HIGH

## Summary

Phase 2 transforms raw ParseResult text (from Phase 1 parsers) into structured `ExtractedDoorPosition` objects through a 3-pass extraction pipeline. Pass 1 uses regex/heuristics on structured data (especially XLSX), Pass 2 sends page-based chunks to Claude Opus via `messages.parse()` for AI-semantic extraction, and Pass 3 performs cross-reference validation (gap check + adversarial review). The phase also introduces multi-file upload per tender with a tender_id-based session model under `/api/v2/upload` and `/api/v2/analyze`.

The existing codebase provides strong foundations: `ExtractedDoorPosition` (55+ fields) and `ExtractionResult` schemas are already defined in `backend/v2/schemas/extraction.py`, `FieldSource` provenance tracking is in `common.py`, the `backend/v2/extraction/` package exists as an empty placeholder, and `KNOWN_FIELD_PATTERNS` with 23 fields and 200+ aliases in the XLSX parser provides the regex basis for Pass 1. The Anthropic SDK's `messages.parse(output_format=ExtractionResult)` guarantees schema-compliant output, eliminating JSON parsing errors.

**Primary recommendation:** Build the extraction pipeline in `backend/v2/extraction/` with separate modules per pass (pass1_structural.py, pass2_semantic.py, pass3_validation.py), an orchestrator (pipeline.py), and a deduplication module (dedup.py). New v2 upload/analyze endpoints go in `backend/v2/routers/`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Pass 1 (strukturell): Regex + Heuristik -- Positionen aus Tabellenstruktur extrahieren (Spalten-Matching, Positions-Nummern per Regex, Dimensionen aus bekannten Mustern). Schnell, kostenlos, nur fuer klar strukturierte Daten.
- Pass 2 (AI-semantisch): Claude Opus mit Chunked-Overlap-Strategie. Dokument in seitenbasierte Chunks teilen (z.B. 30 Seiten pro Chunk, 5 Seiten Overlap). Jeder Chunk wird einzeln an Claude gesendet. Ergebnis: vollstaendige ExtractedDoorPosition-Objekte via messages.parse().
- Pass 3 (Cross-Reference-Validierung): Beides kombiniert -- Luecken-Check UND Adversarial Review in einem Call. Pass 3 bekommt bisherige Ergebnisse + Originaltext und sucht: fehlende Positionen, unvollstaendige Felder, uebersehene Details, falsche Zuordnungen, verwechselte Positionen, falsch gelesene Werte.
- Modell: Claude Opus fuer alle AI-Passes (Pass 2 + Pass 3). Genauigkeit hat Prioritaet vor Kosten.
- Chunking: Seitenbasiert -- z.B. 30 Seiten pro Chunk, 5 Seiten Overlap. Natuerliche Grenze, ParseResult hat bereits page_count.
- Match-Key Deduplizierung: AI-basiert -- Claude entscheidet ob zwei Positionen die gleiche Tuer meinen.
- Dedup Timing: Nach jedem Pass. Pass 1 Ergebnis wird dedupliziert, dann an Pass 2 uebergeben.
- Konflikte: Spaeterer Pass gewinnt (Pass 3 > Pass 2 > Pass 1). Originalwert wird in quellen-Tracking behalten.
- Provenienz: Vollstaendig -- jedes Feld trackt welcher Pass, welches Dokument, welche Seite/Zelle via FieldSource.
- Upload-API: Session/Tender-ID basiert. POST /api/v2/upload gibt tender_id zurueck. Mehrere Uploads mit gleicher tender_id gehoeren zusammen.
- Datei-Reihenfolge: XLSX zuerst, dann PDF, dann DOCX (strukturierteste Daten zuerst).
- Pass-Scope: Pro Datei Pass 1+2 einzeln. Pass 3 laeuft ueber das fusionierte Ergebnis aller Dateien.
- AI-Fehler: 3x Retry mit Backoff. Chunk ueberspringen bei totalem Fehlschlag, Warnung loggen.
- Unsicherheit: Immer extrahieren, aber FieldSource.konfidenz auf niedrigen Wert setzen.
- Validierung: Minimal-Check -- nur positions_nr ist Pflicht.

### Claude's Discretion
- Genaue Chunk-Groesse und Overlap-Werte (30/5 als Richtwert, kann empirisch angepasst werden)
- Prompt-Design fuer Pass 2 und Pass 3
- Retry-Backoff-Strategie (exponentiell, konstant, etc.)
- Interne Dedup-Datenstrukturen
- Reihenfolge der Felder in AI-Prompts

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DOKA-04 | System akzeptiert mehrere Dateien pro Ausschreibung (PDF + Excel + DOCX gemischt) | New `/api/v2/upload` endpoint with tender_id session model; v1 already has `/api/upload/folder` for multi-file; v2 extends with tender grouping |
| DOKA-05 | System fuehrt Multi-Pass-Analyse durch (Pass 1: strukturell, Pass 2: AI-semantisch, Pass 3: Cross-Reference-Validierung) | 3-pass pipeline in `v2/extraction/`: Pass 1 regex from KNOWN_FIELD_PATTERNS, Pass 2 via `messages.parse()` with ExtractionResult, Pass 3 adversarial review with full context |
| DOKA-06 | System extrahiert ALLE technischen Anforderungen als einzelne Datenpunkte (Masse, Material, Normen, Zertifizierungen, Leistungsdaten) | ExtractedDoorPosition already has 55+ fields covering all categories; messages.parse() guarantees schema compliance; field-level FieldSource provenance |
| APII-01 | POST /api/upload akzeptiert mehrere Dateien pro Ausschreibung | New `/api/v2/upload` with tender_id, accepting multiple UploadFile; returns tender_id + per-file metadata |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| anthropic | >=0.49.0 | `messages.parse()` for structured AI extraction | Locked decision; guarantees schema-compliant output with Pydantic models |
| pydantic | >=2.5.3 | Schema definitions for ExtractedDoorPosition, ExtractionResult | Already established in Phase 1; required for `messages.parse()` |
| fastapi | >=0.115.0 | v2 API endpoints for upload/analyze | Already in project; v2 endpoints under `/api/v2/` prefix |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| python-json-logger | ==2.0.7 | Structured logging for all extraction steps | Every pass logs progress with structured fields |
| re (stdlib) | - | Regex patterns for Pass 1 structural extraction | Position number detection, dimension parsing |
| difflib (stdlib) | - | Fuzzy matching for column header recognition | Reuse KNOWN_FIELD_PATTERNS from xlsx_parser |
| uuid (stdlib) | - | tender_id generation | Multi-file session management |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| AI dedup (Claude) | Fuzzy string matching | AI understands context ("T1.01 EG links" = "Position 1.01 Erdgeschoss"); string matching cannot |
| Page-based chunking | Token-based chunking | Page-based is simpler, aligns with ParseResult.page_count, no tokenizer dependency |
| Claude Opus for all passes | Sonnet for Pass 2, Opus for Pass 3 only | User locked Claude Opus for all AI passes; accuracy over cost |

**Installation:**
No new dependencies needed. All libraries are already in `requirements.txt`.

## Architecture Patterns

### Recommended Project Structure
```
backend/v2/
  extraction/
    __init__.py           # Package exports: run_extraction_pipeline()
    pipeline.py           # Orchestrator: file ordering, pass sequencing, result merging
    pass1_structural.py   # Regex/heuristic extraction from ParseResult
    pass2_semantic.py     # Claude Opus chunked extraction via messages.parse()
    pass3_validation.py   # Cross-reference validation + adversarial review
    dedup.py              # AI-based deduplication between passes
    chunking.py           # Page-based text chunking with overlap
    prompts.py            # All AI prompt templates (Pass 2 + Pass 3 + dedup)
  routers/
    __init__.py
    upload_v2.py          # POST /api/v2/upload (multi-file with tender_id)
    analyze_v2.py         # POST /api/v2/analyze (trigger extraction pipeline)
```

### Pattern 1: Pipeline Orchestrator
**What:** Central orchestrator coordinates file ordering, per-file pass execution, cross-document merging, and result assembly.
**When to use:** Always -- this is the main entry point for Phase 2.
**Example:**
```python
# backend/v2/extraction/pipeline.py
from v2.parsers.base import ParseResult
from v2.schemas.extraction import ExtractedDoorPosition, ExtractionResult

async def run_extraction_pipeline(
    parse_results: list[ParseResult],
    tender_id: str,
) -> ExtractionResult:
    """Run 3-pass extraction across all files in a tender.

    File ordering: XLSX first, then PDF, then DOCX.
    Per file: Pass 1 (structural) -> dedup -> Pass 2 (AI semantic) -> dedup
    After all files: Pass 3 (cross-reference validation) on merged result.
    """
    # Sort files: xlsx > pdf > docx
    sorted_results = _sort_by_format(parse_results)

    all_positions: list[ExtractedDoorPosition] = []

    for pr in sorted_results:
        # Pass 1: Structural
        pass1_positions = pass1_structural.extract(pr)
        all_positions = dedup.merge(all_positions, pass1_positions)

        # Pass 2: AI Semantic (chunked)
        pass2_positions = await pass2_semantic.extract(pr, existing=all_positions)
        all_positions = dedup.merge(all_positions, pass2_positions)

    # Pass 3: Cross-reference validation (all files, all positions)
    original_texts = [pr.text for pr in sorted_results]
    all_positions = await pass3_validation.validate_and_enrich(
        all_positions, original_texts
    )

    return ExtractionResult(
        positionen=all_positions,
        dokument_zusammenfassung=_build_summary(sorted_results),
        warnungen=_collect_warnings(sorted_results),
        dokument_typ=sorted_results[0].format if sorted_results else "unknown",
    )
```

### Pattern 2: Chunked AI Extraction with Overlap
**What:** Split document text into page-based chunks with overlap, send each to Claude, merge results.
**When to use:** Pass 2 for documents exceeding single-prompt size.
**Example:**
```python
# backend/v2/extraction/chunking.py
def chunk_by_pages(
    text: str,
    page_count: int,
    chunk_size: int = 30,
    overlap: int = 5,
) -> list[dict]:
    """Split text into page-based chunks with overlap.

    Returns list of {"text": str, "start_page": int, "end_page": int}.
    For documents with page_count <= chunk_size, returns single chunk.
    """
    if page_count <= chunk_size:
        return [{"text": text, "start_page": 1, "end_page": page_count}]

    # Split text on page markers (e.g., "--- Page X ---" or form feeds)
    pages = _split_into_pages(text, page_count)

    chunks = []
    start = 0
    while start < len(pages):
        end = min(start + chunk_size, len(pages))
        chunk_text = "\n".join(pages[start:end])
        chunks.append({
            "text": chunk_text,
            "start_page": start + 1,
            "end_page": end,
        })
        if end >= len(pages):
            break
        start += chunk_size - overlap  # Step forward with overlap

    return chunks
```

### Pattern 3: AI-Based Deduplication
**What:** Send position pairs to Claude to determine if they represent the same door.
**When to use:** After each pass to merge new findings with existing positions.
**Example:**
```python
# backend/v2/extraction/dedup.py
async def merge(
    existing: list[ExtractedDoorPosition],
    new_positions: list[ExtractedDoorPosition],
    pass_priority: int = 1,  # Higher = newer pass wins conflicts
) -> list[ExtractedDoorPosition]:
    """Merge new positions into existing, deduplicating via AI.

    1. Quick pre-filter: exact positions_nr match -> likely same
    2. AI batch: send ambiguous pairs to Claude for clustering
    3. Merge matched pairs (later pass wins field conflicts)
    4. Add truly new positions
    """
    ...
```

### Pattern 4: Structured Output via messages.parse()
**What:** Use Anthropic SDK to get guaranteed schema-compliant extraction.
**When to use:** Pass 2 and Pass 3 AI calls.
**Example:**
```python
# Source: https://platform.claude.com/docs/en/build-with-claude/structured-outputs
import anthropic
from v2.schemas.extraction import ExtractionResult

client = anthropic.Anthropic()

response = client.messages.parse(
    model="claude-opus-4-6",
    max_tokens=16384,
    messages=[
        {"role": "user", "content": extraction_prompt}
    ],
    output_format=ExtractionResult,
)

result: ExtractionResult = response.parsed_output
# Guaranteed to be a valid ExtractionResult with all fields typed
```

### Anti-Patterns to Avoid
- **Monolithic extraction function:** Do NOT put all 3 passes in one function. Each pass must be independently testable and skippable.
- **Token-based chunking:** Do NOT split by tokens. Page-based chunking aligns with ParseResult.page_count and is simpler to implement.
- **String-based dedup only:** Do NOT deduplicate on exact positions_nr match alone. "T1.01", "Tuer 1.01", "Position 1.01" are the same but string-different.
- **Ignoring FieldSource provenance:** Every field value MUST track which pass, document, and location it came from. Do not skip quellen population.
- **Sequential AI calls without retry:** All Claude calls must have 3x retry with exponential backoff. Use tenacity or manual implementation.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Structured AI output parsing | Custom JSON parsing + validation | `messages.parse(output_format=Model)` | Guaranteed schema compliance, no JSON parse errors, automatic type coercion |
| Retry logic | Custom retry loops | `tenacity` library or simple backoff loop | Well-tested, configurable, handles edge cases (already available in Python stdlib patterns) |
| UUID generation | Custom ID schemes | `uuid.uuid4()` | Standard, collision-resistant, already used in v1 upload.py |
| Fuzzy column matching | Custom similarity | Existing `KNOWN_FIELD_PATTERNS` + `_best_field_match()` from xlsx_parser.py | 200+ aliases already battle-tested in v1 |

**Key insight:** The Anthropic SDK's `messages.parse()` eliminates the most error-prone part of AI extraction (JSON parsing/validation). The schema guarantee means you never need to handle malformed AI output -- if the call succeeds, the data is valid.

## Common Pitfalls

### Pitfall 1: Chunk Boundary Position Splitting
**What goes wrong:** A door position's data spans two chunks (e.g., position number on page 30, dimensions on page 31). With no overlap, one chunk gets partial data.
**Why it happens:** Fixed page boundaries don't align with logical content boundaries.
**How to avoid:** Use overlap (5 pages default). Also: in the prompt, instruct Claude to extract all positions it can see, even if data seems incomplete. Dedup will merge partial extractions.
**Warning signs:** Positions with positions_nr but no dimensions, or dimensions without positions_nr.

### Pitfall 2: AI Dedup False Merges
**What goes wrong:** Claude merges two genuinely different positions because they have similar descriptions (e.g., two "Buerotuere EG" in different rooms).
**Why it happens:** Without enough context (room number, floor), positions look identical.
**How to avoid:** Include room number, floor, and all distinguishing fields in the dedup prompt. Only merge when Claude is confident (>0.9).
**Warning signs:** Total position count drops unexpectedly after dedup.

### Pitfall 3: ExtractionResult Token Limit
**What goes wrong:** A chunk with 50+ door positions produces an ExtractionResult that exceeds max_tokens, causing truncation.
**Why it happens:** Each ExtractedDoorPosition has 55+ fields. 50 positions = huge output.
**How to avoid:** Set max_tokens generously (16384+). For very large documents, reduce chunk_size so each chunk yields fewer positions. Monitor stop_reason in responses.
**Warning signs:** `response.stop_reason == "max_tokens"` instead of `"end_turn"`.

### Pitfall 4: Pass 1 Over-Extraction from Non-Door Sheets
**What goes wrong:** Pass 1 regex matches position-like patterns in cover sheets, summary tables, or general text, producing garbage ExtractedDoorPosition objects.
**Why it happens:** Position number regex (e.g., `\d+\.\d+`) matches many things.
**How to avoid:** Only run Pass 1 structural extraction on sheets/sections that matched >= 3 door-related columns (reuse `_MIN_DOOR_FIELDS` logic from xlsx_parser). For PDFs, only extract from table sections.
**Warning signs:** Positions with only positions_nr and no other fields.

### Pitfall 5: Prompt Context Window Overflow in Pass 3
**What goes wrong:** Pass 3 receives ALL positions (as JSON) + ALL original text. For large tenders (100+ positions, 200+ pages), this exceeds context limits.
**Why it happens:** Pass 3 is designed as a holistic cross-reference check.
**How to avoid:** For Pass 3, send position summaries (positions_nr + key fields only) rather than full JSON. Include original text in paginated chunks if needed. Alternatively, batch Pass 3 into groups of 20-30 positions.
**Warning signs:** API errors with "context length exceeded" or "request too large".

### Pitfall 6: Async/Sync Mismatch
**What goes wrong:** Mixing synchronous Anthropic client calls in async FastAPI endpoints causes event loop blocking.
**Why it happens:** Default `anthropic.Anthropic()` is synchronous.
**How to avoid:** Use `anthropic.AsyncAnthropic()` for all calls within async functions. Or run sync calls in executor with `asyncio.to_thread()`.
**Warning signs:** Slow response times, event loop warnings, timeouts under concurrent load.

## Code Examples

### Pass 1: Structural Extraction from XLSX ParseResult
```python
# backend/v2/extraction/pass1_structural.py
import re
from v2.parsers.base import ParseResult
from v2.parsers.xlsx_parser import KNOWN_FIELD_PATTERNS, match_columns
from v2.schemas.extraction import ExtractedDoorPosition
from v2.schemas.common import FieldSource

# Position number patterns found in Swiss tender documents
POSITION_NR_PATTERNS = [
    re.compile(r"^(\d{1,3}\.\d{1,3})"),           # "1.01", "12.03"
    re.compile(r"^(T\d{1,3}\.\d{1,3})", re.I),    # "T1.01"
    re.compile(r"^(Pos\.?\s*\d{1,3}\.\d{1,3})"),   # "Pos. 1.01"
]

def extract_structural(parse_result: ParseResult) -> list[ExtractedDoorPosition]:
    """Pass 1: Extract positions using regex/heuristics from structured text.

    Most effective on XLSX ParseResults where columns are already matched.
    For PDF/DOCX, looks for table-like patterns only.
    """
    positions = []

    if parse_result.format == "xlsx":
        positions = _extract_from_xlsx_text(parse_result)
    elif parse_result.tables:
        # PDF/DOCX with extracted tables
        positions = _extract_from_table_text(parse_result)

    # Tag all fields with Pass 1 source
    for pos in positions:
        for field_name in pos.model_fields_set:
            if field_name != "quellen":
                pos.quellen[field_name] = FieldSource(
                    dokument=parse_result.source_file,
                    konfidenz=0.8,  # Structural extraction = high confidence
                )

    return positions
```

### Pass 2: AI Semantic Extraction
```python
# backend/v2/extraction/pass2_semantic.py
import anthropic
from v2.schemas.extraction import ExtractionResult
from v2.extraction.chunking import chunk_by_pages

PASS2_SYSTEM_PROMPT = """Du bist ein Experte fuer die Analyse von Ausschreibungen
fuer Tueren und Zargen. Extrahiere ALLE Tuerpositionen aus dem folgenden Text.

Fuer jede Position extrahiere alle verfuegbaren Felder:
- positions_nr (PFLICHT)
- Masse (breite_mm, hoehe_mm, wandstaerke_mm, etc.)
- Brandschutz, Schallschutz, Einbruchschutz
- Material, Oberflaeche, Farbe
- Beschlaege (Druecker, Schloss, Zylinder, etc.)
- Normen und Zertifizierungen

Wenn ein Wert nicht eindeutig ist, extrahiere trotzdem mit niedrigerer Konfidenz.
Lieber zu viel extrahieren als zu wenig."""

async def extract_semantic(
    parse_result: ParseResult,
    existing_positions: list = None,
) -> list:
    """Pass 2: AI semantic extraction using Claude Opus with chunking."""
    client = anthropic.AsyncAnthropic()

    chunks = chunk_by_pages(
        parse_result.text,
        parse_result.page_count,
        chunk_size=30,
        overlap=5,
    )

    all_positions = []
    for chunk in chunks:
        prompt = _build_extraction_prompt(chunk, existing_positions)

        for attempt in range(3):  # 3x retry
            try:
                response = await client.messages.parse(
                    model="claude-opus-4-6",
                    max_tokens=16384,
                    system=PASS2_SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": prompt}],
                    output_format=ExtractionResult,
                )

                result = response.parsed_output
                all_positions.extend(result.positionen)
                break

            except Exception as e:
                if attempt == 2:
                    logger.warning(f"Pass 2 chunk failed after 3 retries: {e}")
                    # Skip chunk, continue with next
                else:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff

    return all_positions
```

### Multi-File Upload Endpoint
```python
# backend/v2/routers/upload_v2.py
import uuid
from fastapi import APIRouter, UploadFile, File, Form
from typing import Optional

router = APIRouter(prefix="/api/v2", tags=["V2 Upload"])

# In-memory tender storage (upgrade to DB later)
_tenders: dict[str, dict] = {}

@router.post("/upload")
async def upload_files(
    files: list[UploadFile] = File(...),
    tender_id: Optional[str] = Form(None),
):
    """Upload one or more files to a tender.

    If tender_id is provided, files are added to existing tender.
    If not, a new tender_id is generated.
    """
    if not tender_id:
        tender_id = str(uuid.uuid4())

    if tender_id not in _tenders:
        _tenders[tender_id] = {"files": [], "status": "uploading"}

    file_results = []
    for file in files:
        content = await file.read()
        # Parse immediately (Phase 1 parsers)
        from v2.parsers.router import parse_document
        parse_result = parse_document(content, file.filename)

        _tenders[tender_id]["files"].append({
            "filename": file.filename,
            "parse_result": parse_result,
            "size": len(content),
        })
        file_results.append({
            "filename": file.filename,
            "format": parse_result.format,
            "page_count": parse_result.page_count,
            "warnings": parse_result.warnings,
        })

    return {
        "tender_id": tender_id,
        "files": file_results,
        "total_files": len(_tenders[tender_id]["files"]),
    }
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| JSON mode with manual parsing | `messages.parse(output_format=Model)` | Nov 2025 | Guaranteed schema compliance, no JSON errors |
| Single-pass AI extraction | Multi-pass (structural + AI + validation) | This phase | Catches requirements missed by any single approach |
| Manual prompt engineering for structure | Pydantic schema as output_format | Nov 2025 | Schema is the spec, not the prompt |

**Deprecated/outdated:**
- `beta.messages.parse()` -- structured outputs graduated from beta. Use `messages.parse()` directly.
- `response_format` parameter name may vary by SDK version; verify with installed version. Current pattern is `output_format=`.

## Open Questions

1. **Exact SDK parameter name: `output_format` vs `response_format`**
   - What we know: Official docs (Nov 2025) show `output_format=ContactInfo`. Phase 1 CONTEXT.md says `response_format=ExtractionResult`.
   - What's unclear: The installed anthropic SDK version (>=0.49.0 in requirements.txt) may use different parameter names. The docs fetched 2026-03-10 show `output_format`.
   - Recommendation: Use `output_format` as shown in current official docs. If it fails, check installed version and adjust.

2. **AsyncAnthropic support for messages.parse()**
   - What we know: Synchronous `Anthropic().messages.parse()` is documented. Async variant should exist as `AsyncAnthropic().messages.parse()`.
   - What's unclear: Whether async parse is fully supported in the installed SDK version.
   - Recommendation: Implement with `AsyncAnthropic`. If unavailable, use `asyncio.to_thread()` wrapper around sync calls.

3. **Optimal chunk size for Swiss tender documents**
   - What we know: User suggested 30 pages / 5 overlap as starting point. Door lists range 39-217 columns.
   - What's unclear: Actual page counts of typical tenders, optimal ratio of chunk size to extraction quality.
   - Recommendation: Start with 30/5 as default, make configurable. Add logging to track positions-per-chunk to calibrate later.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 7.4.4 + pytest-asyncio 0.23.3 |
| Config file | `backend/tests/conftest.py` (imports conftest_v2.py fixtures) |
| Quick run command | `cd backend && python -m pytest tests/test_v2_extraction.py -x -v` |
| Full suite command | `cd backend && python -m pytest tests/ -x -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DOKA-04 | Multi-file upload per tender | integration | `pytest tests/test_v2_upload.py -x` | No - Wave 0 |
| DOKA-05 | 3-pass extraction pipeline | unit + integration | `pytest tests/test_v2_extraction.py -x` | No - Wave 0 |
| DOKA-06 | All technical requirements as data points | unit | `pytest tests/test_v2_extraction.py::test_all_fields_extracted -x` | No - Wave 0 |
| APII-01 | POST /api/upload multi-file | integration | `pytest tests/test_v2_upload.py::test_multi_file_upload -x` | No - Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/test_v2_extraction.py tests/test_v2_upload.py -x -v`
- **Per wave merge:** `cd backend && python -m pytest tests/ -x -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_v2_extraction.py` -- covers DOKA-05, DOKA-06 (pass1, pass2 mock, pass3 mock, dedup, pipeline orchestration)
- [ ] `tests/test_v2_upload.py` -- covers DOKA-04, APII-01 (multi-file upload, tender_id session, file ordering)
- [ ] `tests/test_v2_dedup.py` -- covers deduplication logic (merge, conflict resolution, provenance tracking)
- [ ] `tests/conftest_v2.py` additions -- multi-file fixtures, sample tender with mixed formats

## Sources

### Primary (HIGH confidence)
- [Anthropic Structured Outputs Docs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) - messages.parse() API, output_format parameter, Pydantic integration, schema guarantees
- Existing codebase: `backend/v2/schemas/extraction.py` (ExtractedDoorPosition, ExtractionResult), `backend/v2/schemas/common.py` (FieldSource), `backend/v2/parsers/xlsx_parser.py` (KNOWN_FIELD_PATTERNS), `backend/v2/parsers/base.py` (ParseResult)

### Secondary (MEDIUM confidence)
- [Anthropic Python SDK GitHub](https://github.com/anthropics/anthropic-sdk-python) - SDK structure, async support patterns
- Phase 1 research and implementation patterns (01-RESEARCH.md, conftest_v2.py)

### Tertiary (LOW confidence)
- Exact async messages.parse() support -- not directly verified in installed SDK version

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all libraries already in requirements.txt, messages.parse() verified in official docs
- Architecture: HIGH - clear pass separation, existing schemas and patterns from Phase 1
- Pitfalls: HIGH - based on known LLM extraction patterns and codebase constraints (55+ fields, 200+ page documents)

**Research date:** 2026-03-10
**Valid until:** 2026-04-10 (stable domain, established SDK)
