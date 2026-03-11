"""
V2 Parsers - Document format parsers returning uniform ParseResult.

Parsers extract raw text only. AI structuring happens in Phase 2 (extraction).
"""

from v2.parsers.base import BaseParser, ParseResult
from v2.parsers.router import parse_document, SUPPORTED_FORMATS
from v2.parsers.pdf_parser import parse_pdf
from v2.parsers.docx_parser import parse_docx
from v2.parsers.xlsx_parser import parse_xlsx

__all__ = [
    "BaseParser",
    "ParseResult",
    "parse_document",
    "SUPPORTED_FORMATS",
    "parse_pdf",
    "parse_docx",
    "parse_xlsx",
]
