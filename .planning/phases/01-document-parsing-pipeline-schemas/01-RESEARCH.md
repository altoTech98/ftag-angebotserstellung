# Phase 1: Document Parsing & Pipeline Schemas - Research

**Researched:** 2026-03-10
**Domain:** Document parsing (PDF/DOCX/XLSX), Pydantic v2 data contracts, structured AI output
**Confidence:** HIGH

## Summary

Phase 1 establishes two foundational pillars: (1) per-format document parsers that convert PDF, DOCX, and XLSX files into raw text preserving structure, and (2) Pydantic v2 data contracts (schemas) that define the typed interfaces between all pipeline stages. The parsers live in `backend/v2/parsers/` and deliver text output only -- AI structuring happens in Phase 2. The schemas live in `backend/v2/schemas/` and must be compatible with `anthropic>=0.84.0` `messages.parse()` for structured output extraction.

The existing v1 codebase provides substantial reusable logic: `excel_parser.py` (1097 lines) contains proven header auto-detection, merged cell handling, and fuzzy column matching. `document_parser.py` already uses pymupdf4llm as primary PDF parser with pdfplumber/OCR fallbacks. The v2 parsers should cleanly rewrite this logic into the new `backend/v2/` structure while preserving the battle-tested algorithms.

**Primary recommendation:** Rewrite v1 parser logic into clean v2 modules under `backend/v2/parsers/`, define all pipeline Pydantic schemas in `backend/v2/schemas/`, and ensure schemas work with `client.messages.parse(output_format=Model)`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Pydantic-Schema-Design**: Maximale Feld-Tiefe: Jede Tuer-Eigenschaft ein eigenes Feld (~50+ Felder: breite_mm, hoehe_mm, brandschutz_klasse, schallschutz_db, material_blatt, material_zarge, etc.)
- **Feldnamen auf Deutsch** (breite_mm, brandschutz_klasse, schallschutz_db) -- konsistent mit Produktkatalog und Ausschreibungen
- **Strikt + Freitext**: Bekannte Werte als Enums (Brandschutz-Klassen, Schallschutz-Klassen, Materialien), aber mit Optional[str] Freitext-Feld fuer Unbekanntes/Unerwartetes
- **Quellen-Tracking pro Feld**: Jedes Feld hat source_document + source_location (Seite/Zeile/Zelle) -- Provenienz auf Feld-Ebene, nicht nur pro Anforderung
- **Schemas muessen mit `anthropic>=0.84.0` `messages.parse()` kompatibel sein** (Pydantic v2)
- **Parser-Strategie**: v1 excel_parser.py Logik (Header-Detect, Merged Cells, fuzzy Column Matching) uebernehmen, sauber neu schreiben in v2-Struktur
- **PDF**: pymupdf4llm als Primaer-Parser, pdfplumber nur als Fallback fuer spezielle Faelle
- **OCR-Unterstuetzung** mit Tesseract fuer gescannte PDFs (v1 hat bereits pytesseract-Integration)
- **Alle Parser liefern Roh-Text** -- AI macht die Strukturierung komplett (Phase 2)
- **Neuer Ordner `backend/v2/`** -- saubere Trennung von v1
- **Struktur nach Pipeline-Stufe**: `v2/parsers/`, `v2/extraction/`, `v2/matching/`, `v2/validation/`, `v2/gaps/`, `v2/output/`
- **v1 und v2 koexistieren** waehrend Entwicklung (verschiedene Endpoints), am Ende v1 entfernen
- **Neue eigene Exception-Hierarchie** in `backend/v2/` -- keine Abhaengigkeit von v1-Exceptions
- **Fehlerbehandlung**: Bei teilweise lesbaren Dokumenten: Weitermachen + warnen
- **Parse-Warnungen nur im Logging**, nicht im Pydantic-Schema
- **Korrupte/passwortgeschuetzte Dateien**: Versuchen zu parsen, bei Scheitern als Warning melden

### Claude's Discretion
- Genaue Enum-Werte fuer Brandschutz/Schallschutz/Material (basierend auf Produktkatalog-Analyse)
- pymupdf4llm vs pdfplumber Fallback-Logik
- Interne Hilfsstrukturen und Utility-Funktionen
- Genaue Ordnerstruktur innerhalb der Pipeline-Stufen

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DOKA-01 | System parst PDF-Dateien und extrahiert vollstaendigen Text mit Tabellenstruktur | pymupdf4llm `to_markdown()` as primary parser preserves tables as Markdown; pdfplumber batch table extraction as fallback; OCR via pytesseract for scanned PDFs |
| DOKA-02 | System parst DOCX-Dateien und extrahiert Text mit Formatierung | python-docx extracts paragraphs with style info + tables with cell structure; v1 pattern is solid, rewrite cleanly |
| DOKA-03 | System parst XLSX-Dateien und erkennt Tuerlisten-Spaltenstruktur automatisch | v1 excel_parser.py has proven header auto-detect, merged cell handling, fuzzy column matching (1097 lines of battle-tested logic to port) |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pymupdf4llm | >=0.0.17 | PDF to Markdown with tables | Already in v1; best table preservation for LLM consumption |
| PyMuPDF (fitz) | >=1.24.0 | Fast PDF text extraction | Already in v1; 10-100x faster than pdfplumber for text |
| pdfplumber | ==0.11.4 | PDF table fallback extraction | Already in v1; handles edge cases pymupdf4llm misses |
| python-docx | ==1.1.2 | DOCX parsing | Already in v1; standard Python DOCX library |
| openpyxl | ==3.1.5 | XLSX parsing with merged cells | Already in v1; needed for unmerge_cells before pandas |
| pandas | ==2.2.3 | DataFrame operations for Excel | Already in v1; powers header detection and data extraction |
| pydantic | >=2.5.3 | Schema definitions (v2) | Already in v1; required for `messages.parse()` compatibility |
| anthropic | >=0.84.0 | Claude API with structured outputs | Decision from CONTEXT.md; `messages.parse(output_format=Model)` |
| pytesseract | ==0.3.10 | OCR for scanned PDFs | Already in v1; German+English language support |
| Pillow | ==10.2.0 | Image processing for OCR pipeline | Already in v1; required by pytesseract |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| python-json-logger | ==2.0.7 | Structured logging | All v2 modules must use structured logging |
| difflib (stdlib) | - | Fuzzy string matching for columns | Excel column header matching |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pymupdf4llm | unstructured[all-docs] | Unstructured is heavier (500MB+), already optional in v1; pymupdf4llm is lighter and sufficient |
| pdfplumber tables | camelot-py | camelot requires ghostscript; pdfplumber is already proven in v1 |
| openpyxl + pandas | xlrd | xlrd only supports .xls (old format); openpyxl handles .xlsx/.xlsm |

**Installation:**
All libraries already in `backend/requirements.txt`. Only update needed:
```bash
pip install anthropic>=0.84.0
```
Current requirements.txt has `anthropic>=0.49.0` -- must be bumped to `>=0.84.0` for `messages.parse()` support.

## Architecture Patterns

### Recommended Project Structure
```
backend/v2/
├── __init__.py
├── parsers/
│   ├── __init__.py
│   ├── base.py              # ParseResult dataclass, BaseParser protocol
│   ├── pdf_parser.py         # pymupdf4llm primary, pdfplumber/OCR fallback
│   ├── docx_parser.py        # python-docx with formatting context
│   ├── xlsx_parser.py        # Header auto-detect, merged cells, fuzzy matching
│   └── router.py             # Format detection + dispatch to correct parser
├── schemas/
│   ├── __init__.py
│   ├── common.py             # FieldSource, shared enums (BrandschutzKlasse, etc.)
│   ├── extraction.py         # ExtractedRequirement, ExtractedDoorPosition
│   ├── matching.py           # MatchResult, MatchDimension, ConfidenceBreakdown
│   ├── validation.py         # AdversarialResult, ValidationOutcome
│   ├── gaps.py               # GapReport, GapItem, GapSeverity
│   └── pipeline.py           # AnalysisJob, PipelineState (orchestration)
├── exceptions.py             # V2Error base, ParseError, SchemaError, etc.
├── extraction/               # (Phase 2 -- empty __init__.py placeholder)
├── matching/                 # (Phase 4 -- empty __init__.py placeholder)
├── validation/               # (Phase 5 -- empty __init__.py placeholder)
├── gaps/                     # (Phase 6 -- empty __init__.py placeholder)
└── output/                   # (Phase 7 -- empty __init__.py placeholder)
```

### Pattern 1: ParseResult as Uniform Parser Output
**What:** Every parser returns the same `ParseResult` dataclass regardless of input format
**When to use:** All parser calls
**Example:**
```python
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class ParseResult:
    """Uniform output from all document parsers."""
    text: str                               # Full extracted text (Markdown for PDF)
    format: str                             # "pdf", "docx", "xlsx"
    page_count: int = 0                     # Number of pages/sheets
    warnings: list[str] = field(default_factory=list)  # Non-fatal issues
    metadata: dict = field(default_factory=dict)       # Format-specific metadata
    source_file: str = ""                   # Original filename
```

### Pattern 2: Field-Level Source Tracking via Companion Model
**What:** Each door property field has a paired `FieldSource` tracking provenance
**When to use:** All ExtractedDoorPosition fields that come from document parsing
**Example:**
```python
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum

class FieldSource(BaseModel):
    """Provenance tracking for a single extracted field value."""
    dokument: str = Field(description="Source document filename")
    seite: Optional[int] = Field(None, description="Page number (PDF) or None")
    zeile: Optional[int] = Field(None, description="Row number (Excel) or None")
    zelle: Optional[str] = Field(None, description="Cell reference e.g. 'B15' (Excel)")
    sheet: Optional[str] = Field(None, description="Sheet name (Excel) or None")
    konfidenz: float = Field(1.0, description="Extraction confidence 0-1")

class TrackedField(BaseModel):
    """A value with its source provenance."""
    wert: Optional[str] = None
    quelle: Optional[FieldSource] = None
```
**Note:** For `messages.parse()` compatibility, keep nesting depth manageable. The SDK handles nested Pydantic models, but deeply nested Optional fields increase schema complexity. Recommend max 3 levels of nesting.

### Pattern 3: Enum + Freitext for Domain Values
**What:** Use Enums for known standard values with a parallel Optional[str] freitext field for unexpected values
**When to use:** Brandschutz, Schallschutz, Material, etc.
**Example:**
```python
from enum import Enum
from typing import Optional

class BrandschutzKlasse(str, Enum):
    """Swiss/EU fire protection classes per EN 13501-2."""
    EI30 = "EI30"
    EI60 = "EI60"
    EI90 = "EI90"
    EI120 = "EI120"
    E30 = "E30"
    E60 = "E60"
    E90 = "E90"
    T30 = "T30"       # Legacy Swiss designation
    T60 = "T60"
    T90 = "T90"
    KEINE = "keine"

class ExtractedDoorPosition(BaseModel):
    # ... other fields ...
    brandschutz_klasse: Optional[BrandschutzKlasse] = None
    brandschutz_freitext: Optional[str] = Field(
        None, description="Raw text if value doesn't match known enum"
    )
```

### Pattern 4: V2 Exception Hierarchy (Independent from V1)
**What:** New exception classes in `backend/v2/exceptions.py`, no imports from v1
**When to use:** All v2 error handling
**Example:**
```python
class V2Error(Exception):
    """Base exception for v2 pipeline."""
    def __init__(self, message: str, code: str = "V2_ERROR", details: dict = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)

class ParseError(V2Error):
    """Document parsing failed."""
    def __init__(self, message: str, filename: str = "", details: dict = None):
        super().__init__(message, code="PARSE_ERROR", details={"filename": filename, **(details or {})})

class SchemaValidationError(V2Error):
    """Pydantic schema validation failed."""
    def __init__(self, message: str, model: str = "", details: dict = None):
        super().__init__(message, code="SCHEMA_VALIDATION_ERROR", details={"model": model, **(details or {})})
```

### Anti-Patterns to Avoid
- **Importing v1 exceptions in v2:** Creates coupling. V2 has its own hierarchy.
- **Returning structured data from parsers:** Parsers return text only. Structuring is Phase 2's job.
- **Hardcoding column positions in XLSX parser:** Customer Excel files vary 39-217 columns. Always use fuzzy matching.
- **Failing on partial parse:** Decision says "Weitermachen + warnen". Never raise on partial extraction -- log warning and return what you got.
- **Using `minimum`/`maximum` constraints in Pydantic models for Claude:** These are stripped by the SDK before sending to Claude. They still validate client-side, but Claude doesn't see them during generation. Use `description` strings instead for guidance.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PDF table detection | Custom table grid parser | pymupdf4llm `to_markdown()` with `table_strategy='lines_strict'` | Table detection is deceptively hard; pymupdf4llm handles most cases |
| Excel merged cells | Manual cell range walking | openpyxl `merged_cells.ranges` + v1's `unmerge_cells()` pattern | Merged cell resolution has edge cases (nested merges, partial overlaps) |
| Fuzzy column matching | Custom string similarity | `difflib.SequenceMatcher` + v1's `KNOWN_FIELD_PATTERNS` dictionary | v1 has 23 field patterns with 200+ aliases already battle-tested |
| OCR pipeline | Custom image-to-text | pytesseract + Pillow with v1's `_configure_tesseract()` pattern | Tesseract config (binary path, tessdata, language detection) has Windows-specific quirks already solved |
| JSON schema for Claude | Manual schema construction | `client.messages.parse(output_format=PydanticModel)` | SDK handles schema transformation, constraint stripping, and response validation automatically |

**Key insight:** The v1 codebase has 1097 lines of battle-tested Excel parsing logic and 776 lines of document parsing with multiple fallback layers. Port the algorithms, clean up the structure, don't reinvent.

## Common Pitfalls

### Pitfall 1: pymupdf4llm Table Strategy Mismatch
**What goes wrong:** pymupdf4llm's default `table_strategy='lines_strict'` misses tables without full grid lines (common in Swiss tender PDFs where only horizontal rules are used)
**Why it happens:** Many Swiss Ausschreibungs-PDFs use minimal table formatting
**How to avoid:** Try `lines_strict` first, if table count is 0 on pages with suspected tables, retry with `table_strategy='text'` or fall back to pdfplumber
**Warning signs:** Extracted text has tabular data but no Markdown table formatting

### Pitfall 2: Pydantic v2 Optional Field Default Behavior
**What goes wrong:** In Pydantic v2, `Optional[str]` does NOT automatically default to `None`. You must explicitly set `= None` or the field is required.
**Why it happens:** Changed from v1 behavior; easy to miss
**How to avoid:** Always write `field: Optional[str] = None` explicitly
**Warning signs:** Pydantic `ValidationError` on missing fields during `messages.parse()`

### Pitfall 3: anthropic SDK Schema Constraint Stripping
**What goes wrong:** Field constraints like `gt=0`, `le=1000`, `min_length=1` are removed from the schema sent to Claude. Claude may generate values violating these constraints.
**Why it happens:** Claude's structured output supports a subset of JSON Schema. Unsupported constraints are stripped and moved to descriptions.
**How to avoid:** Use Enums for constrained values. For numeric ranges, add explicit description text. The SDK does validate client-side, but a `ValidationError` after Claude responds wastes an API call.
**Warning signs:** `ValidationError` after `messages.parse()` returns

### Pitfall 4: Excel Duplicate Column Names
**What goes wrong:** When merged cells create duplicate column names in pandas DataFrame, `row.get(col)` returns a Series instead of a scalar, causing "truth value of a Series is ambiguous" error
**Why it happens:** Common in multi-row header Excel files from Swiss architects
**How to avoid:** Port v1's `_to_scalar()` helper that handles this edge case
**Warning signs:** Crash on specific customer Excel files that work fine with others

### Pitfall 5: PDF Encoding and Unicode Issues
**What goes wrong:** Some PDFs use custom font encodings where extracted text is gibberish (e.g., ligatures, custom glyph mappings)
**Why it happens:** PDF is a display format, not a text format. Font subset embedding can lose character mapping.
**How to avoid:** Check if extracted text has reasonable character distribution. If mostly non-printable/unusual characters, fall back to OCR.
**Warning signs:** Extracted text has unusual Unicode characters or very low ratio of alphanumeric characters

### Pitfall 6: Password-Protected or Corrupt Files
**What goes wrong:** PyMuPDF raises on encrypted PDFs, openpyxl may hang on corrupted XLSX
**Why it happens:** Decision says "Versuchen zu parsen, bei Scheitern als Warning melden"
**How to avoid:** Wrap each parser in try/except, return partial ParseResult with warning, never let parser crash propagate to caller
**Warning signs:** Exception on file open, not during content extraction

## Code Examples

### PDF Parser with Fallback Chain
```python
# Source: v1 document_parser.py pattern, adapted for v2
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

def parse_pdf(content: bytes, filename: str = "") -> ParseResult:
    """Parse PDF with pymupdf4llm primary, pdfplumber/OCR fallbacks."""
    warnings = []

    # Try pymupdf4llm first (best table support)
    try:
        import pymupdf4llm
        md_text = pymupdf4llm.to_markdown(content)
        if md_text and len(md_text.strip()) > 100:
            import fitz
            with fitz.open(stream=content, filetype="pdf") as doc:
                page_count = len(doc)
            return ParseResult(
                text=md_text,
                format="pdf",
                page_count=page_count,
                warnings=warnings,
                source_file=filename,
                metadata={"method": "pymupdf4llm"},
            )
    except Exception as e:
        warnings.append(f"pymupdf4llm failed: {e}")
        logger.warning(f"[PDF] pymupdf4llm failed for {filename}: {e}")

    # Fallback: PyMuPDF text + pdfplumber tables
    # ... (port v1 _parse_pdf_bytes logic)

    # Last resort: OCR
    # ... (port v1 _ocr_pdf_bytes logic)
```

### XLSX Parser Header Auto-Detection
```python
# Source: v1 excel_parser.py pattern, core algorithm
def detect_header_row(ws, max_scan: int = 20) -> int:
    """Auto-detect the header row in an Excel worksheet.

    Scans first max_scan rows, scores each by:
    - Number of non-empty cells
    - Presence of known field patterns (tuer_nr, breite, brandschutz, etc.)
    - Text-heavy content (headers are text, data rows have numbers)

    Returns 0-indexed row number of best header candidate.
    """
    # Port v1 logic: iterate rows, score by KNOWN_FIELD_PATTERNS matches
    ...
```

### Pydantic Schema Compatible with messages.parse()
```python
# Source: anthropic structured outputs documentation
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum

class BrandschutzKlasse(str, Enum):
    EI30 = "EI30"
    EI60 = "EI60"
    EI90 = "EI90"
    EI120 = "EI120"
    T30 = "T30"
    T60 = "T60"
    T90 = "T90"
    KEINE = "keine"

class FieldSource(BaseModel):
    dokument: str
    seite: Optional[int] = None
    zeile: Optional[int] = None
    zelle: Optional[str] = None

class ExtractedDoorPosition(BaseModel):
    """Single door position extracted from tender documents."""
    positions_nr: str = Field(description="Position number e.g. '1.01'")

    # Dimensions
    breite_mm: Optional[int] = Field(None, description="Door width in mm")
    hoehe_mm: Optional[int] = Field(None, description="Door height in mm")

    # Protection classes
    brandschutz_klasse: Optional[BrandschutzKlasse] = None
    brandschutz_freitext: Optional[str] = None
    schallschutz_db: Optional[int] = Field(None, description="Sound protection in dB")

    # Source tracking
    quellen: dict[str, FieldSource] = Field(
        default_factory=dict,
        description="Source provenance per field name"
    )

# Usage with Claude:
# response = client.messages.parse(
#     model="claude-sonnet-4-6",
#     max_tokens=4096,
#     messages=[...],
#     output_format=ExtractedDoorPosition,
# )
# position = response.parsed_output
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| pdfplumber for all PDF parsing | pymupdf4llm for Markdown output | 2024 (pymupdf4llm v0.0.17+) | 10-100x faster, better table preservation |
| Pydantic v1 Optional defaults to None | Pydantic v2 requires explicit `= None` | 2023 (Pydantic v2.0) | Breaking change, affects all schemas |
| anthropic SDK tool_use for structured output | `messages.parse(output_format=Model)` | 2025 (anthropic v0.84.0+) | Simpler API, constrained decoding, automatic validation |
| Manual JSON schema creation | SDK auto-generates from Pydantic model | 2025 (anthropic v0.84.0+) | Less boilerplate, fewer schema bugs |

**Deprecated/outdated:**
- `pdfplumber` as primary PDF parser: Still useful for table fallback, but pymupdf4llm is primary now
- `anthropic` tool_use pattern for structured output: `messages.parse()` is cleaner and uses constrained decoding
- v1's dict-based position format: Replace with typed Pydantic models

## Open Questions

1. **Exact Enum Values for Domain Fields**
   - What we know: v1's `KNOWN_FIELD_PATTERNS` has 23 fields; catalog has 318 columns; Brandschutz uses EI30/EI60/EI90/T30/T60/T90 standards
   - What's unclear: Complete set of Schallschutz values, Material enum values, Zargentyp options from actual product catalog
   - Recommendation: Analyze `data/produktuebersicht.xlsx` column values during implementation to derive complete enum sets. Start with known standards, add freitext fallback for edge cases.

2. **Source Tracking Schema Design for messages.parse()**
   - What we know: SDK supports nested Pydantic models with Optional fields. `dict[str, FieldSource]` is valid JSON Schema.
   - What's unclear: Whether Claude reliably populates a `dict[str, FieldSource]` mapping with correct field names as keys. May need testing.
   - Recommendation: Define the schema, test with a sample extraction call. If Claude struggles with the dict key mapping, simplify to a flat list of `FieldSource` entries or move source tracking out of the Claude extraction schema (populate it post-extraction in Python).

3. **pymupdf4llm Table Strategy Selection**
   - What we know: `table_strategy='lines_strict'` is default; `'text'` mode exists for borderless tables
   - What's unclear: Which strategy works best for Swiss Ausschreibungs-PDFs specifically
   - Recommendation: Implement with `lines_strict` default, add fallback logic. Test against actual tender PDFs during implementation.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 7.4.4 + pytest-asyncio 0.23.3 |
| Config file | `backend/pytest.ini` |
| Quick run command | `cd backend && python -m pytest tests/ -x -q` |
| Full suite command | `cd backend && python -m pytest tests/ -v --tb=short` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DOKA-01 | PDF parsing preserves table structure | unit | `cd backend && python -m pytest tests/test_v2_pdf_parser.py -x` | No -- Wave 0 |
| DOKA-01 | PDF OCR fallback for scanned docs | unit | `cd backend && python -m pytest tests/test_v2_pdf_parser.py::test_ocr_fallback -x` | No -- Wave 0 |
| DOKA-02 | DOCX parsing preserves formatting context | unit | `cd backend && python -m pytest tests/test_v2_docx_parser.py -x` | No -- Wave 0 |
| DOKA-03 | XLSX auto-detects column structure | unit | `cd backend && python -m pytest tests/test_v2_xlsx_parser.py -x` | No -- Wave 0 |
| DOKA-03 | XLSX handles merged cells | unit | `cd backend && python -m pytest tests/test_v2_xlsx_parser.py::test_merged_cells -x` | No -- Wave 0 |
| ALL | Pydantic schemas importable and valid | unit | `cd backend && python -m pytest tests/test_v2_schemas.py -x` | No -- Wave 0 |
| ALL | Schemas compatible with messages.parse() | unit | `cd backend && python -m pytest tests/test_v2_schemas.py::test_anthropic_compatibility -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/test_v2_*.py -x -q`
- **Per wave merge:** `cd backend && python -m pytest tests/ -v --tb=short`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_v2_pdf_parser.py` -- covers DOKA-01 (PDF table preservation, OCR fallback, corrupt file handling)
- [ ] `backend/tests/test_v2_docx_parser.py` -- covers DOKA-02 (paragraph extraction, table extraction, formatting context)
- [ ] `backend/tests/test_v2_xlsx_parser.py` -- covers DOKA-03 (header auto-detect, merged cells, fuzzy column matching)
- [ ] `backend/tests/test_v2_schemas.py` -- covers schema validity, import, anthropic compatibility
- [ ] `backend/tests/conftest_v2.py` -- shared fixtures for v2 tests (sample PDF/DOCX/XLSX bytes, mock ParseResult)
- [ ] `backend/v2/__init__.py` -- v2 package initialization
- [ ] Framework install: Already installed (pytest in requirements.txt)

## Sources

### Primary (HIGH confidence)
- [pymupdf4llm API docs](https://pymupdf.readthedocs.io/en/latest/pymupdf4llm/api.html) - Full `to_markdown()` parameter list, v1.27.1
- [Anthropic Structured Outputs docs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) - `messages.parse()` API, schema constraints, Pydantic integration
- v1 source code: `backend/services/excel_parser.py` (1097 lines), `backend/services/document_parser.py` (776 lines), `backend/services/exceptions.py`, `backend/services/catalog_index.py`
- [Pydantic v2 Fields docs](https://docs.pydantic.dev/latest/concepts/fields/) - Field constraints, Optional behavior changes

### Secondary (MEDIUM confidence)
- [anthropic-sdk-python releases](https://github.com/anthropics/anthropic-sdk-python/releases) - SDK version history for messages.parse() availability
- [pymupdf4llm PyPI](https://pypi.org/project/pymupdf4llm/) - Package version info

### Tertiary (LOW confidence)
- Source tracking pattern with `dict[str, FieldSource]` in messages.parse() -- needs empirical validation with actual Claude calls

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all libraries already in v1, versions verified in requirements.txt
- Architecture: HIGH - v2 structure decided in CONTEXT.md, patterns derived from proven v1 code
- Pitfalls: HIGH - most pitfalls observed in v1 codebase (e.g., _to_scalar, OCR config, merged cells)
- Schema design: MEDIUM - messages.parse() with nested models is documented, but source tracking dict pattern needs empirical testing

**Research date:** 2026-03-10
**Valid until:** 2026-04-10 (stable domain, libraries well-established)
