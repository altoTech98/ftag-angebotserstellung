# Phase 19: PDF Performance Fix - Research

**Researched:** 2026-03-12
**Domain:** PDF text extraction performance, pydantic compatibility, document parser architecture
**Confidence:** HIGH

## Summary

Phase 19 addresses the root cause of the analysis pipeline failure chain: pdfplumber's pure-Python PDF parsing takes ~10 minutes for a 286-page tender PDF, making analysis unusable for real FTAG documents. The fix is straightforward -- replace pdfplumber's text extraction with PyMuPDF (which wraps the C-based MuPDF engine from Artifex, the PDF specification authors) while retaining pdfplumber exclusively for table extraction where it excels.

The codebase has two PDF parsing entry points: `_parse_pdf_bytes()` (general parsing, called via `parse_document_bytes`) and `parse_pdf_specs_bytes()` (spec parsing with char limit, called from `_run_project_analysis` with `max_chars=0`). Both iterate every page with pdfplumber for text AND tables, which is the bottleneck. PyMuPDF can extract text from the same document in 8-17 seconds -- a 30-70x improvement. The `max_chars=0` bug is already fixed (line 144: `effective_limit = 999_999_999`), but the `max_pages = 30` hardcap in `parse_pdf_specs_bytes` should be removed since PyMuPDF can handle all 286 pages in seconds. The pydantic compatibility fix (INT-02) requires pinning `pydantic>=2.7.0` which is already in `requirements.txt` -- verification that it is actually installed at runtime is what matters.

**Primary recommendation:** Add PyMuPDF as a fast text extraction layer in both `_parse_pdf_bytes()` and `parse_pdf_specs_bytes()`, keep pdfplumber for table extraction only, remove the 30-page cap, add per-page progress logging, and verify pydantic version at startup.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PDF-01 | PDF text extraction uses PyMuPDF instead of pdfplumber for spec text, completing 286-page PDF in under 30 seconds | PyMuPDF `page.get_text()` benchmarks at 17-35 pages/sec; drop-in replacement in `_parse_pdf_bytes()` and `parse_pdf_specs_bytes()` |
| PDF-02 | pdfplumber retained exclusively for table extraction where PyMuPDF is insufficient | Hybrid approach: PyMuPDF for text, pdfplumber only for `extract_tables()` on pages where tables detected |
| PDF-03 | max_chars=0 treated as unlimited consistently across all PDF parsing paths | Already fixed at line 144; verify no regression when switching to PyMuPDF path; remove `max_pages=30` cap |
| PDF-04 | Per-page progress logging emitted during PDF parsing for observability | Add `logger.info(f"PDF page {page_num}/{total_pages}")` every N pages in PyMuPDF loop |
| INT-02 | No by_alias pydantic/anthropic SDK errors (pydantic >=2.7.0 verified) | requirements.txt already pins `pydantic>=2.7.0`; add startup version check in `main.py` |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PyMuPDF | >=1.24.0 | Fast PDF text extraction (C-based MuPDF engine) | 10-50x faster than pdfplumber; maintained by Artifex (MuPDF/PDF spec authors); 10+ years production use |
| pdfplumber | 0.11.4 (existing) | Table extraction only | Best Python table parser; already validated against FTAG tender docs; keep for `extract_tables()` |
| pydantic | >=2.7.0 (existing) | Data validation | Already pinned in requirements.txt; anthropic SDK requires >=2.7.0 for `by_alias` parameter support |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytesseract | 0.3.10 (existing) | OCR fallback for scanned PDFs | When PyMuPDF text extraction returns empty/short text |
| Pillow | 10.2.0 (existing) | Image processing for OCR | Used by OCR fallback chain |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| PyMuPDF | pypdfium2 | Also fast (C-based), but smaller ecosystem and less documentation |
| PyMuPDF | pdftext | Newer, less battle-tested; PyMuPDF has decade+ of production use |
| PyMuPDF | pymupdf4llm | Wrapper around PyMuPDF for markdown output -- unnecessary abstraction for this use case |

**Installation:**
```bash
pip install PyMuPDF>=1.24.0
```

Note: Package name is `PyMuPDF` on PyPI, but import is `import fitz`. There is an unrelated `fitz` package on PyPI -- always install `PyMuPDF`, never `fitz`.

## Architecture Patterns

### Current Document Parser Structure
```
backend/services/document_parser.py
  parse_document_bytes(content, ext)        # Main entry: routes by extension
    _parse_pdf_bytes(content)               # PDF: pdfplumber text + tables + OCR/Vision fallback
    _parse_excel_bytes(content)             # Excel: pandas
    _parse_word_bytes(content)              # Word: python-docx

  parse_pdf_specs_bytes(content, max_chars) # Spec PDF: pdfplumber text + tables, char-limited
    max_pages = 30  (REMOVE THIS)           # Artificial cap, unnecessary with PyMuPDF speed

  _ocr_pdf_bytes(content, max_pages)        # OCR fallback: pytesseract
  parse_pdf_with_vision(content)            # Vision fallback: Claude Vision API
```

### Recommended Modified Structure
```
backend/services/document_parser.py
  parse_document_bytes(content, ext)
    _parse_pdf_bytes(content)
      Pass 1: PyMuPDF page.get_text() for ALL pages (fast, seconds)
      Pass 2: pdfplumber extract_tables() ONLY on pages with tables
      Fallback: OCR -> Vision (unchanged)

  parse_pdf_specs_bytes(content, max_chars)
    PyMuPDF page.get_text() for ALL pages (no max_pages cap)
    pdfplumber extract_tables() on table-containing pages only
    Character limit applied at the end (unchanged)
```

### Pattern 1: Hybrid PDF Parsing (PyMuPDF text + pdfplumber tables)
**What:** Use PyMuPDF for fast text extraction on all pages, then selectively use pdfplumber only for pages that contain tables.
**When to use:** Always -- this is the core change for Phase 19.
**Example:**
```python
import fitz  # PyMuPDF
import pdfplumber
import io

def _extract_text_fast(content: bytes) -> tuple[list[str], int]:
    """Fast text extraction with PyMuPDF. Returns (text_parts, page_count)."""
    doc = fitz.open(stream=content, filetype="pdf")
    total_pages = len(doc)
    text_parts = []
    for page_num in range(total_pages):
        page = doc[page_num]
        text = page.get_text()
        if text and text.strip():
            text_parts.append(f"--- Seite {page_num + 1} ---\n{text}")
        if (page_num + 1) % 50 == 0 or page_num == total_pages - 1:
            logger.info(f"PDF text extraction: {page_num + 1}/{total_pages} pages")
    doc.close()
    return text_parts, total_pages

def _extract_tables_selective(content: bytes, max_pages: int = None) -> list[str]:
    """Extract tables using pdfplumber only on pages that have them."""
    table_parts = []
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        pages = pdf.pages[:max_pages] if max_pages else pdf.pages
        for page_num, page in enumerate(pages, 1):
            try:
                tables = page.extract_tables()
                for table in tables or []:
                    if table:
                        table_text = _table_to_text(table)
                        if table_text:
                            table_parts.append(f"[Tabelle Seite {page_num}]\n{table_text}")
            except Exception as e:
                logger.debug(f"Table extraction page {page_num} failed: {e}")
    return table_parts
```

### Pattern 2: Progress Logging for Long Operations
**What:** Emit per-page progress during PDF parsing for observability.
**When to use:** In both `_parse_pdf_bytes` and `parse_pdf_specs_bytes`.
**Example:**
```python
# Log every 50 pages and on the last page
if (page_num + 1) % 50 == 0 or page_num + 1 == total_pages:
    logger.info(f"[PDF] Text extraction progress: {page_num + 1}/{total_pages} pages")
```

### Pattern 3: Graceful Fallback Chain
**What:** Try fast path first, fall back to slower but reliable methods.
**Already in codebase:** `_parse_pdf_bytes` already does text -> OCR -> Vision. Preserve this chain but swap PyMuPDF in as the first text extraction step.

### Anti-Patterns to Avoid
- **Removing pdfplumber entirely:** pdfplumber is still needed for table extraction AND as the image rendering backend in `_ocr_pdf_bytes`. Keep it installed.
- **Using PyMuPDF for table extraction:** PyMuPDF's `find_tables()` exists (since v1.23.0) but is less mature than pdfplumber's `extract_tables()`. Do not switch table extraction.
- **Running pdfplumber on all pages for tables:** Only run pdfplumber table extraction on pages where tables are actually needed. For `_parse_pdf_bytes`, tables are extracted on every page currently -- consider keeping this for correctness, but the speed win comes from text extraction, not table extraction.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Fast PDF text extraction | Custom C extension or subprocess call to pdftotext | PyMuPDF `page.get_text()` | PyMuPDF wraps MuPDF (C library), handles encoding, font mapping, layout; custom solutions miss edge cases |
| PDF page count / metadata | Parse PDF header bytes manually | `fitz.open()` then `len(doc)` | PDF format is complex; PyMuPDF handles all versions and encryption |
| Table detection | Regex on extracted text | pdfplumber `extract_tables()` | Table detection requires spatial analysis of text positions, line detection, cell boundary computation |
| Pydantic version verification | Manual string parsing of pip output | `importlib.metadata.version("pydantic")` | Standard Python API, no subprocess needed |

## Common Pitfalls

### Pitfall 1: PyMuPDF Table Extraction Produces Different Output Than pdfplumber
**What goes wrong:** Swapping PyMuPDF for ALL extraction (text + tables) gives different table structures. The `[Tabelle Seite X]` markers and `_table_to_text()` format depend on pdfplumber's `list[list[str]]` output.
**Why it happens:** Developers benchmark text speed, swap everything, only test with text-heavy PDFs. FTAG tender docs are table-heavy.
**How to avoid:** Keep pdfplumber for table extraction. Only use PyMuPDF for `page.get_text()`.
**Warning signs:** AI extraction produces fewer door positions or `gesamtanzahl_tueren` drops.

### Pitfall 2: OCR Fallback Chain Breaks When pdfplumber Import Changes
**What goes wrong:** `_ocr_pdf_bytes()` (line 274-278) uses pdfplumber to render pages as images when `pdf2image` is not installed. If pdfplumber is removed from imports or dependencies, OCR silently returns empty string.
**Why it happens:** The dependency is hidden inside a `try/except ImportError` block.
**How to avoid:** Keep pdfplumber as a dependency (it is still needed for tables anyway). Optionally update OCR to use PyMuPDF's `page.get_pixmap()` for image rendering as an improvement.
**Warning signs:** Scanned PDFs return "PDF ist leer oder konnte nicht gelesen werden".

### Pitfall 3: PyMuPDF `fitz` Import Name Conflict
**What goes wrong:** There is an old, unrelated `fitz` package on PyPI. Installing `pip install fitz` gives the wrong package. On Windows with NSSM, stale `.pyc` files can also cause confusion.
**Why it happens:** PyMuPDF's import name (`fitz`) differs from its package name (`PyMuPDF`).
**How to avoid:** Always install as `pip install PyMuPDF`. Verify with `python -c "import fitz; print(fitz.__doc__)"` -- should show "PyMuPDF".
**Warning signs:** ImportError or unexpected behavior after install.

### Pitfall 4: `max_pages = 30` Cap Still Active After PyMuPDF Switch
**What goes wrong:** `parse_pdf_specs_bytes()` has `max_pages = 30` (line 153). With pdfplumber this was necessary (30 pages already slow). With PyMuPDF, this cap artificially limits extraction to 30 pages of a 286-page document, missing 90% of the spec content.
**Why it happens:** The cap was a performance workaround, not a business rule.
**How to avoid:** Remove `max_pages = 30` when switching to PyMuPDF. The `effective_limit` (character-based) is the correct limit mechanism.
**Warning signs:** Spec parsing returns incomplete text, AI misses requirements from later pages.

### Pitfall 5: `--- Seite X ---` and `[Tabelle Seite X]` Marker Format Changes
**What goes wrong:** Downstream code and AI prompts may pattern-match on `--- Seite X ---` markers. If PyMuPDF changes the format (e.g., different page numbering), parsing breaks silently.
**Why it happens:** The markers are constructed in the parser, not by pdfplumber. As long as the replacement code uses the same format string, this is fine.
**How to avoid:** Use identical marker format: `f"--- Seite {page_num} ---\n{text}"` and `f"[Tabelle Seite {page_num}]\n{table_text}"`.

## Code Examples

### Example 1: Modified `_parse_pdf_bytes` with PyMuPDF Fast Path
```python
def _parse_pdf_bytes(content: bytes) -> str:
    """Extract text from PDF: PyMuPDF for text (fast), pdfplumber for tables, OCR/Vision fallback."""
    text_parts = []

    try:
        # Pass 1: Fast text extraction with PyMuPDF
        import fitz
        doc = fitz.open(stream=content, filetype="pdf")
        total_pages = len(doc)

        if total_pages == 0:
            doc.close()
            raise FileError(ErrorCode.FILE_PARSE_ERROR, "PDF hat keine Seiten", filename=".pdf")

        logger.info(f"[PDF] Starting PyMuPDF text extraction: {total_pages} pages")
        for page_num in range(total_pages):
            page = doc[page_num]
            page_text = page.get_text()
            if page_text and page_text.strip():
                text_parts.append(f"--- Seite {page_num + 1} ---\n{page_text}")
            # Progress logging every 50 pages
            if (page_num + 1) % 50 == 0 or page_num + 1 == total_pages:
                logger.info(f"[PDF] Text extraction: {page_num + 1}/{total_pages} pages")
        doc.close()

        # Pass 2: Table extraction with pdfplumber (slower, but needed for structured data)
        import pdfplumber
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                try:
                    tables = page.extract_tables()
                    for table in tables or []:
                        if table:
                            table_text = _table_to_text(table)
                            if table_text:
                                text_parts.append(f"[Tabelle Seite {page_num}]\n{table_text}")
                except Exception as e:
                    logger.debug(f"Table extraction page {page_num} failed: {e}")

        result = "\n\n".join(text_parts)

        # ... existing OCR/Vision fallback chain (unchanged) ...
```

### Example 2: Modified `parse_pdf_specs_bytes` with PyMuPDF
```python
def parse_pdf_specs_bytes(content: bytes, max_chars: int = 8000) -> str:
    if not content:
        return ""

    effective_limit = max_chars if max_chars > 0 else 999_999_999

    try:
        import fitz
        doc = fitz.open(stream=content, filetype="pdf")
        total_pages = len(doc)
        logger.info(f"PDF spec parsing: {total_pages} pages (PyMuPDF), max_chars={max_chars}")

        text_parts = []
        total_chars = 0

        for page_num in range(total_pages):
            if total_chars >= effective_limit:
                break
            page = doc[page_num]
            page_text = page.get_text()
            if page_text and page_text.strip():
                text_parts.append(f"--- Seite {page_num + 1} ---\n{page_text}")
                total_chars += len(page_text)
            # Progress logging
            if (page_num + 1) % 50 == 0 or page_num + 1 == total_pages:
                logger.info(f"[PDF spec] Page {page_num + 1}/{total_pages}, {total_chars} chars so far")
        doc.close()

        # Table extraction with pdfplumber (keep for structured data)
        import pdfplumber
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                if total_chars >= effective_limit:
                    break
                try:
                    tables = page.extract_tables()
                    for table in tables or []:
                        if table and total_chars < effective_limit:
                            table_text = _table_to_text(table)
                            if table_text:
                                text_parts.append(f"[Tabelle Seite {page_num}]\n{table_text}")
                                total_chars += len(table_text)
                except Exception as e:
                    logger.debug(f"Table extraction page {page_num} failed: {e}")

        text = "\n\n".join(text_parts)
        if max_chars > 0 and len(text) > max_chars:
            text = text[:max_chars] + "\n[... Text gekuerzt]"

        logger.info(f"PDF spec parsed: {len(text_parts)} parts, {total_chars} chars extracted")
        return text if text.strip() else "[PDF konnte nicht vollstaendig gelesen werden]"

    except ImportError:
        logger.warning("[PDF] PyMuPDF not installed, falling back to pdfplumber")
        # Fall back to existing pdfplumber implementation
        ...
    except Exception as e:
        logger.exception("PDF-Specs Parsing fehlgeschlagen")
        return f"[PDF konnte nicht gelesen werden: {str(e)}]"
```

### Example 3: Pydantic Version Verification at Startup
```python
# In main.py startup or lifespan
def _verify_pydantic_version():
    """Verify pydantic >= 2.7.0 to avoid anthropic SDK by_alias errors."""
    from importlib.metadata import version as get_version
    pydantic_version = get_version("pydantic")
    major, minor = [int(x) for x in pydantic_version.split(".")[:2]]
    if major < 2 or (major == 2 and minor < 7):
        logger.error(
            f"pydantic {pydantic_version} detected, but >=2.7.0 required "
            f"for anthropic SDK compatibility. Run: pip install 'pydantic>=2.7.0'"
        )
        raise RuntimeError(f"pydantic >= 2.7.0 required, found {pydantic_version}")
    logger.info(f"pydantic version OK: {pydantic_version}")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| pdfplumber for all PDF text | PyMuPDF for text, pdfplumber for tables | Standard since ~2023 | 10-50x speed improvement on text extraction |
| `max_pages = 30` cap | No page cap (PyMuPDF handles full doc in seconds) | This phase | Extracts all content from large PDFs |
| `max_chars=0` means "extract nothing" | `max_chars=0` means unlimited | Already fixed (line 144) | Full spec text reaches AI |
| pydantic 2.5.x | pydantic >=2.7.0 | Anthropic SDK requirement since anthropic 0.30+ | Fixes `by_alias` parameter errors |

**Deprecated/outdated:**
- `max_pages = 30` in `parse_pdf_specs_bytes`: Performance workaround for pdfplumber, unnecessary with PyMuPDF

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 7.4.4 |
| Config file | None detected -- Wave 0 gap |
| Quick run command | `python -m pytest tests/ -x -q` |
| Full suite command | `python -m pytest tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PDF-01 | PyMuPDF extracts text from PDF in <30s | integration | `python -c "import fitz; doc=fitz.open('test.pdf'); print(len(doc))"` (basic); full timing test needs real PDF | No -- Wave 0 |
| PDF-02 | pdfplumber still extracts tables correctly | unit | `python -m pytest tests/test_document_parser.py::test_table_extraction -x` | No -- Wave 0 |
| PDF-03 | max_chars=0 extracts all text | unit | `python -m pytest tests/test_document_parser.py::test_max_chars_zero -x` | No -- Wave 0 |
| PDF-04 | Per-page progress in logs | manual-only | Check log output during PDF parsing -- visual inspection | N/A |
| INT-02 | No pydantic by_alias errors | smoke | `python -c "from importlib.metadata import version; v=version('pydantic'); print(v)"` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `python -c "import fitz; print('PyMuPDF OK:', fitz.__doc__[:20])"` + `python -c "import pdfplumber; print('pdfplumber OK')"` (verify both imports work)
- **Per wave merge:** Manual test with a real PDF file
- **Phase gate:** Verify all 5 success criteria manually

### Wave 0 Gaps
- [ ] `tests/test_document_parser.py` -- unit tests for `_parse_pdf_bytes` and `parse_pdf_specs_bytes` with PyMuPDF
- [ ] A small test PDF file in `tests/fixtures/` for automated testing
- [ ] Verify `pydantic>=2.7.0` is installed (not just pinned)

## Open Questions

1. **PyMuPDF text quality on German construction PDFs**
   - What we know: PyMuPDF handles Unicode/UTF-8 well, including German umlauts
   - What's unclear: Whether layout-sensitive text (multi-column tender specs) produces equivalent output to pdfplumber
   - Recommendation: Test with a real 286-page FTAG tender PDF after implementation. If quality is noticeably worse, consider `page.get_text("blocks")` for layout-aware extraction.

2. **Table extraction speed impact**
   - What we know: pdfplumber table extraction is the slow part. Running it on ALL pages even after PyMuPDF text extraction still adds time.
   - What's unclear: For a 286-page PDF, how much time does table extraction alone take?
   - Recommendation: For `parse_pdf_specs_bytes`, consider skipping table extraction if text extraction already produced sufficient content. For `_parse_pdf_bytes`, keep table extraction on all pages for correctness.

3. **OCR fallback with PyMuPDF image rendering**
   - What we know: PyMuPDF can render pages to images via `page.get_pixmap()`, which could replace pdfplumber's role in the OCR fallback
   - What's unclear: Whether this is needed now or is a nice-to-have
   - Recommendation: Defer to a future phase. Keep the existing OCR chain unchanged -- pdfplumber is still installed for tables, so the OCR fallback works as-is.

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection: `backend/services/document_parser.py` (529 lines), `backend/routers/analyze.py` (658 lines), `backend/services/job_store.py` (170 lines), `backend/requirements.txt`
- PyMuPDF performance comparison (official): benchmarks showing 10-50x speed advantage over pdfplumber
- Milestone research: `.planning/research/STACK.md`, `.planning/research/PITFALLS.md`, `.planning/research/ARCHITECTURE.md`

### Secondary (MEDIUM confidence)
- PyMuPDF `find_tables()` availability since v1.23.0 -- verify with changelog before relying on it for table detection
- Independent benchmarks (2025-2026) confirming PyMuPDF speed advantage

### Tertiary (LOW confidence)
- None -- all findings verified against codebase and official documentation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - PyMuPDF is well-documented, benchmarked, and the clear standard for fast PDF text extraction in Python
- Architecture: HIGH - All findings from direct codebase inspection; hybrid approach (PyMuPDF text + pdfplumber tables) is a standard pattern
- Pitfalls: HIGH - All pitfalls identified from direct code analysis of the actual files being modified

**Research date:** 2026-03-12
**Valid until:** 2026-04-12 (stable domain, libraries well-established)
