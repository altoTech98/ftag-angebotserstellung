"""
Tests for document_parser service.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.document_parser import (
    DocumentParser,
    parse_document_bytes,
    parse_pdf_specs_bytes,
    _ocr_pdf_bytes,
    _table_to_text,
)
from services.error_handler import FileError


def _make_pdf(text_lines):
    """Create a minimal valid PDF with given text lines."""
    stream_parts = ["BT", "/F1 12 Tf"]
    y = 700
    for line in text_lines:
        safe = line.replace("(", "\\(").replace(")", "\\)")
        stream_parts.append(f"{100} {y} Td")
        stream_parts.append(f"({safe}) Tj")
        y -= 20
    stream_parts.append("ET")
    stream = "\n".join(stream_parts)
    length = len(stream)

    pdf = f"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>
endobj
4 0 obj
<< /Length {length} >>
stream
{stream}
endstream
endobj
5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
xref
0 6
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000266 00000 n
0000000900 00000 n
trailer
<< /Size 6 /Root 1 0 R >>
startxref
978
%%EOF"""
    return pdf.encode("latin-1")


class TestDocumentParser:
    """Tests for the DocumentParser class."""

    def test_get_format_pdf(self):
        assert DocumentParser.get_format("document.pdf") == "PDF"

    def test_get_format_excel(self):
        assert DocumentParser.get_format("data.xlsx") == "Excel"
        assert DocumentParser.get_format("data.xls") == "Excel"
        assert DocumentParser.get_format("data.xlsm") == "Excel"

    def test_get_format_word(self):
        assert DocumentParser.get_format("doc.docx") == "Word"
        assert DocumentParser.get_format("doc.doc") == "Word"

    def test_get_format_txt(self):
        assert DocumentParser.get_format("readme.txt") == "Text"

    def test_get_format_unsupported(self):
        assert DocumentParser.get_format("image.jpg") is None
        assert DocumentParser.get_format("script.py") is None

    def test_get_format_case_insensitive(self):
        assert DocumentParser.get_format("DOC.PDF") == "PDF"
        assert DocumentParser.get_format("file.XLSX") == "Excel"

    def test_is_supported(self):
        assert DocumentParser.is_supported("file.pdf") is True
        assert DocumentParser.is_supported("file.exe") is False


class TestParseDocumentBytes:
    """Tests for parse_document_bytes function."""

    def test_parse_txt(self, sample_txt_bytes):
        result = parse_document_bytes(sample_txt_bytes, ".txt")
        assert "Ausschreibung" in result
        assert "Stahltür" in result
        assert len(result) > 0

    def test_parse_empty_raises(self):
        with pytest.raises(FileError):
            parse_document_bytes(b"", ".txt")

    def test_parse_empty_txt_raises(self):
        with pytest.raises(FileError):
            parse_document_bytes(b"   ", ".txt")

    def test_parse_unsupported_format_raises(self):
        with pytest.raises(FileError):
            parse_document_bytes(b"data", ".xyz")

    def test_parse_excel(self, sample_excel_bytes):
        result = parse_document_bytes(sample_excel_bytes, ".xlsx")
        assert "Stahltür" in result or "Position" in result
        assert len(result) > 0

    def test_parse_word(self, sample_word_bytes):
        result = parse_document_bytes(sample_word_bytes, ".docx")
        assert "Ausschreibung" in result
        assert len(result) > 0

    def test_parse_pdf(self):
        """PDF text extraction works correctly."""
        pdf = _make_pdf(["Ausschreibung Tueren", "Position 1.01 Brandschutztuere T30"])
        result = parse_document_bytes(pdf, ".pdf")
        assert "Ausschreibung" in result
        assert len(result) > 0

    def test_parse_pdf_extracts_content(self):
        """PDF parser extracts meaningful text content."""
        pdf = _make_pdf(["Tuere 900x2100mm", "Preis CHF 1500.00"])
        result = parse_document_bytes(pdf, ".pdf")
        assert "900" in result or "Tuere" in result

    def test_parse_pdf_invalid_raises(self):
        """Invalid PDF content raises FileError."""
        with pytest.raises(FileError):
            parse_document_bytes(b"This is not a PDF file", ".pdf")

    def test_parse_pdf_empty_bytes_raises(self):
        """Empty bytes with .pdf extension raises FileError."""
        with pytest.raises(FileError):
            parse_document_bytes(b"", ".pdf")

    def test_parse_none_content_raises(self):
        with pytest.raises(FileError):
            parse_document_bytes(None, ".pdf")

    def test_long_txt_accepted(self, sample_txt_bytes):
        """TXT parser returns full text (truncation only applies to PDF/Excel/Word)."""
        long_text = ("A" * 200000).encode("utf-8")
        result = parse_document_bytes(long_text, ".txt")
        assert len(result) == 200000


class TestPdfSpecsParsing:
    """Tests for PDF specs parsing (limited extraction)."""

    def test_specs_basic(self):
        pdf = _make_pdf(["Spezifikation Brandschutztuere EI30"])
        result = parse_pdf_specs_bytes(pdf, max_chars=8000)
        assert "Brandschutz" in result or "EI30" in result

    def test_specs_empty_returns_fallback(self):
        result = parse_pdf_specs_bytes(b"", max_chars=8000)
        assert result == ""

    def test_specs_invalid_pdf_returns_error_message(self):
        result = parse_pdf_specs_bytes(b"not a pdf", max_chars=8000)
        assert "konnte nicht gelesen werden" in result.lower() or "error" in result.lower()


class TestOcrFallback:
    """Tests for OCR fallback functionality."""

    def test_ocr_graceful_when_unavailable(self):
        """OCR returns empty string when Tesseract is not installed."""
        pdf = _make_pdf(["Test"])
        result = _ocr_pdf_bytes(pdf)
        assert isinstance(result, str)

    def test_ocr_invalid_input(self):
        """OCR handles invalid input gracefully."""
        result = _ocr_pdf_bytes(b"not a pdf")
        assert isinstance(result, str)


class TestTableToText:
    """Tests for _table_to_text helper."""

    def test_basic_table(self):
        table = [["A", "B"], ["1", "2"]]
        result = _table_to_text(table)
        assert "A | B" in result
        assert "1 | 2" in result

    def test_empty_table(self):
        assert _table_to_text([]) == ""
        assert _table_to_text(None) == ""

    def test_table_with_none_cells(self):
        table = [["A", None, "C"]]
        result = _table_to_text(table)
        assert "A" in result
        assert "C" in result


class TestHybridPdfParsing:
    """Tests for hybrid PDF analysis (pdfplumber + Vision)."""

    def test_analyze_pdf_hybrid_returns_structure(self):
        from services.vision_parser import analyze_pdf_hybrid
        pdf = _make_pdf(["Ausschreibung Tueren Position 1 Stahltuere T30 Brandschutz 900x2100"])
        result = analyze_pdf_hybrid(pdf)
        assert "text" in result
        assert "positions" in result
        assert "method" in result
        assert "stats" in result
        assert result["stats"]["total_pages"] >= 1

    def test_analyze_pdf_hybrid_text_only_for_good_pages(self):
        from services.vision_parser import analyze_pdf_hybrid
        # This PDF has enough text (>500 chars won't trigger, but structure test)
        pdf = _make_pdf(["A" * 600])
        result = analyze_pdf_hybrid(pdf)
        # Good text page should not trigger vision
        assert result["stats"]["vision_pages"] == 0 or result["method"] == "text_only"
