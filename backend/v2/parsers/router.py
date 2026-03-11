"""
Parser Router - Format detection and dispatch to correct parser.

Detects document format from file extension or magic bytes,
dispatches to the appropriate parser. Returns ParseResult for all inputs.
"""

import logging
from pathlib import Path

from v2.parsers.base import ParseResult

logger = logging.getLogger(__name__)


SUPPORTED_FORMATS = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".xlsx": "xlsx",
    ".xls": "xlsx",
    ".xlsm": "xlsx",
}


def parse_document(content: bytes, filename: str) -> ParseResult:
    """Parse a document by detecting its format and dispatching to the right parser.

    Args:
        content: Raw file bytes.
        filename: Original filename (used for format detection and provenance).

    Returns:
        ParseResult from the appropriate parser. Never raises.
    """
    if not content:
        return ParseResult(
            text="",
            format="unknown",
            page_count=0,
            warnings=["Empty file provided"],
            metadata={},
            source_file=filename,
        )

    # Detect format from extension
    fmt = _detect_format_by_extension(filename)

    # Fallback: detect from magic bytes
    if not fmt:
        fmt = _detect_format_by_magic(content)

    if not fmt:
        ext = Path(filename).suffix.lower() if filename else "(no extension)"
        logger.warning(f"[ROUTER] Unsupported format: {ext} for {filename}")
        return ParseResult(
            text="",
            format="unknown",
            page_count=0,
            warnings=[f"Unsupported format: {ext}"],
            metadata={},
            source_file=filename,
        )

    logger.info(
        f"[ROUTER] Dispatching {filename} ({len(content)} bytes) to {fmt} parser"
    )

    try:
        if fmt == "pdf":
            from v2.parsers.pdf_parser import parse_pdf
            return parse_pdf(content, filename=filename)
        elif fmt == "docx":
            from v2.parsers.docx_parser import parse_docx
            return parse_docx(content, filename=filename)
        elif fmt == "xlsx":
            from v2.parsers.xlsx_parser import parse_xlsx
            return parse_xlsx(content, filename=filename)
        else:
            return ParseResult(
                text="",
                format="unknown",
                page_count=0,
                warnings=[f"No parser for format: {fmt}"],
                metadata={},
                source_file=filename,
            )
    except Exception as e:
        logger.error(f"[ROUTER] Parser failed for {filename}: {e}")
        return ParseResult(
            text="",
            format=fmt,
            page_count=0,
            warnings=[f"Parser failed: {str(e)}"],
            metadata={},
            source_file=filename,
        )


def _detect_format_by_extension(filename: str) -> str | None:
    """Detect format from file extension. Returns format string or None."""
    if not filename:
        return None
    ext = Path(filename).suffix.lower()
    return SUPPORTED_FORMATS.get(ext)


def _detect_format_by_magic(content: bytes) -> str | None:
    """Detect format from file magic bytes. Returns format string or None."""
    if not content or len(content) < 4:
        return None

    # PDF: starts with %PDF
    if content[:4] == b"%PDF":
        return "pdf"

    # ZIP-based formats (XLSX, DOCX): starts with PK
    if content[:2] == b"PK":
        # Try to distinguish DOCX from XLSX by checking ZIP contents
        try:
            import zipfile
            import io
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                names = zf.namelist()
                if any("word/" in n for n in names):
                    return "docx"
                if any("xl/" in n for n in names):
                    return "xlsx"
        except Exception:
            pass
        # Default ZIP to xlsx (more common in this domain)
        return "xlsx"

    return None
