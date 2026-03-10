"""
PDF Parser - Extracts text from PDF files with table preservation.

Fallback chain:
1. pymupdf4llm (Markdown with tables)
2. PyMuPDF text + pdfplumber tables
3. OCR via pytesseract (if available)

Never raises exceptions to callers. Returns ParseResult with warnings on failure.
"""

import io
import logging

from v2.parsers.base import ParseResult

logger = logging.getLogger(__name__)


def parse_pdf(content: bytes, filename: str = "") -> ParseResult:
    """Parse PDF bytes into a ParseResult.

    Args:
        content: Raw PDF file bytes.
        filename: Original filename for provenance tracking.

    Returns:
        ParseResult with extracted text and metadata. Never raises.
    """
    if not content:
        return ParseResult(
            text="",
            format="pdf",
            page_count=0,
            warnings=["Empty file provided"],
            metadata={"method": "none"},
            source_file=filename,
        )

    # Track which method succeeded
    method = "none"
    text = ""
    page_count = 0
    warnings = []
    tables = []
    metadata = {}

    # --- Attempt 1: pymupdf4llm (best table support) ---
    try:
        text, page_count, method = _try_pymupdf4llm(content)
        if text and len(text.strip()) > 100:
            # Check for tables in the markdown output
            for line in text.split("\n"):
                if "|" in line and line.strip().startswith("|"):
                    # Found table lines, collect table blocks
                    break
            tables = _extract_table_blocks(text)
            metadata["method"] = method
            return ParseResult(
                text=text,
                format="pdf",
                page_count=page_count,
                warnings=warnings,
                metadata=metadata,
                source_file=filename,
                tables=tables,
            )
    except Exception as e:
        logger.debug(f"[PDF] pymupdf4llm failed for {filename}: {e}")
        warnings.append(f"pymupdf4llm failed: {str(e)}")

    # --- Attempt 2: PyMuPDF text + pdfplumber tables ---
    try:
        text, page_count, tables_found = _try_fitz_pdfplumber(content)
        if text and len(text.strip()) > 0:
            method = "pdfplumber"
            tables = tables_found
            metadata["method"] = method
            return ParseResult(
                text=text,
                format="pdf",
                page_count=page_count,
                warnings=warnings,
                metadata=metadata,
                source_file=filename,
                tables=tables,
            )
    except Exception as e:
        logger.debug(f"[PDF] fitz+pdfplumber failed for {filename}: {e}")
        warnings.append(f"pdfplumber fallback failed: {str(e)}")

    # --- Attempt 3: OCR (last resort) ---
    try:
        ocr_text, ocr_pages = _try_ocr(content)
        if ocr_text and len(ocr_text.strip()) > 0:
            method = "ocr"
            text = ocr_text
            page_count = ocr_pages or page_count
    except Exception as e:
        logger.debug(f"[PDF] OCR failed for {filename}: {e}")
        warnings.append(f"OCR fallback failed: {str(e)}")

    if not text.strip():
        warnings.append("No text could be extracted from PDF")

    metadata["method"] = method
    return ParseResult(
        text=text,
        format="pdf",
        page_count=page_count,
        warnings=warnings,
        metadata=metadata,
        source_file=filename,
        tables=tables,
    )


def _try_pymupdf4llm(content: bytes) -> tuple[str, int, str]:
    """Try extracting PDF as Markdown with pymupdf4llm.

    Returns: (text, page_count, method_name)
    Raises on failure.
    """
    import pymupdf4llm
    import fitz

    # Get page count
    with fitz.open(stream=content, filetype="pdf") as doc:
        page_count = len(doc)

    md_text = pymupdf4llm.to_markdown(content)
    return md_text, page_count, "pymupdf4llm"


def _try_fitz_pdfplumber(content: bytes) -> tuple[str, int, list[str]]:
    """Try PyMuPDF for text + pdfplumber for tables.

    Returns: (text, page_count, table_markdowns)
    Raises on failure.
    """
    import fitz
    import pdfplumber

    text_parts = []
    tables_md = []

    # Extract text with fitz
    with fitz.open(stream=content, filetype="pdf") as doc:
        page_count = len(doc)
        for page_num, page in enumerate(doc, 1):
            page_text = page.get_text()
            if page_text and page_text.strip():
                text_parts.append(f"--- Page {page_num} ---\n{page_text}")

    # Extract tables with pdfplumber
    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                try:
                    page_tables = page.extract_tables() or []
                    for table in page_tables:
                        if table:
                            md = _table_to_markdown(table)
                            if md:
                                tables_md.append(md)
                                text_parts.append(f"[Table Page {page_num}]\n{md}")
                except Exception:
                    continue
    except Exception as e:
        logger.debug(f"[PDF] pdfplumber table extraction failed: {e}")

    text = "\n\n".join(text_parts)
    return text, page_count, tables_md


def _try_ocr(content: bytes) -> tuple[str, int]:
    """Try OCR extraction using pytesseract.

    Returns: (text, page_count)
    Raises on failure or if pytesseract not available.
    """
    import fitz

    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        logger.debug("[PDF] pytesseract or Pillow not available for OCR")
        return "", 0

    # Configure tesseract path on Windows
    import os
    tesseract_cmd = os.environ.get("TESSERACT_CMD")
    if not tesseract_cmd:
        default = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        if os.path.isfile(default):
            pytesseract.pytesseract.tesseract_cmd = default
    elif tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    # Set tessdata path
    if not os.environ.get("TESSDATA_PREFIX"):
        local_tessdata = os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "data", "tessdata"
        )
        if os.path.isdir(local_tessdata):
            os.environ["TESSDATA_PREFIX"] = os.path.abspath(local_tessdata)

    # Determine OCR language
    ocr_lang = "deu+eng"
    try:
        available = pytesseract.get_languages()
        if "deu" not in available:
            ocr_lang = "eng"
    except Exception:
        ocr_lang = "eng"

    text_parts = []
    with fitz.open(stream=content, filetype="pdf") as doc:
        page_count = len(doc)
        for page_num, page in enumerate(doc, 1):
            try:
                # Render page to image
                pix = page.get_pixmap(dpi=200)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                page_text = pytesseract.image_to_string(img, lang=ocr_lang)
                if page_text and page_text.strip():
                    text_parts.append(f"--- Page {page_num} (OCR) ---\n{page_text}")
            except Exception as e:
                logger.debug(f"[PDF] OCR page {page_num} failed: {e}")
                continue

    return "\n\n".join(text_parts), page_count


def _table_to_markdown(table: list) -> str:
    """Convert a pdfplumber table (list of lists) to markdown format."""
    if not table or not table[0]:
        return ""

    rows = []
    for i, row in enumerate(table):
        cells = [str(cell).strip() if cell else "" for cell in row]
        rows.append("| " + " | ".join(cells) + " |")
        if i == 0:
            # Add separator row after header
            rows.append("| " + " | ".join(["---"] * len(cells)) + " |")

    return "\n".join(rows)


def _extract_table_blocks(markdown_text: str) -> list[str]:
    """Extract table blocks from markdown text (sequences of lines starting with |)."""
    tables = []
    current_table = []

    for line in markdown_text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("|") and "|" in stripped[1:]:
            current_table.append(stripped)
        else:
            if current_table and len(current_table) >= 2:
                tables.append("\n".join(current_table))
            current_table = []

    # Don't forget last table
    if current_table and len(current_table) >= 2:
        tables.append("\n".join(current_table))

    return tables
