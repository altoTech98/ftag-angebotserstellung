"""
Tests for v2 PDF parser.

Tests PDF parsing with pymupdf4llm primary, pdfplumber fallback, and OCR last resort.
All tests verify the parser returns ParseResult and never raises.
"""

import pytest

from v2.parsers.base import ParseResult


class TestPdfBasicText:
    """Test basic PDF text extraction."""

    def test_pdf_basic_text(self, sample_pdf_bytes):
        """Parse valid PDF bytes -> ParseResult with non-empty text, format='pdf', page_count > 0."""
        from v2.parsers.pdf_parser import parse_pdf

        result = parse_pdf(sample_pdf_bytes, filename="test.pdf")

        assert isinstance(result, ParseResult)
        assert result.format == "pdf"
        assert result.page_count > 0
        assert len(result.text) > 0

    def test_pdf_returns_parse_result(self, sample_pdf_bytes):
        """Return type is ParseResult."""
        from v2.parsers.pdf_parser import parse_pdf

        result = parse_pdf(sample_pdf_bytes, filename="test.pdf")
        assert isinstance(result, ParseResult)


class TestPdfTablePreservation:
    """Test table extraction from PDFs."""

    def test_pdf_table_preservation(self):
        """Parse PDF with table -> text contains Markdown table syntax (| delimiters)."""
        from v2.parsers.pdf_parser import parse_pdf

        # Create a PDF with table content using fitz
        import fitz

        doc = fitz.open()
        page = doc.new_page()
        # Insert text that includes table-like content
        text_lines = [
            "Tuerliste Projekt X",
            "",
            "| Tuer Nr. | Breite | Hoehe | Brandschutz |",
            "|-----------|--------|-------|-------------|",
            "| 1.01      | 1000   | 2100  | EI30        |",
            "| 1.02      | 900    | 2050  | EI60        |",
        ]
        y = 72
        for line in text_lines:
            page.insert_text((72, y), line, fontsize=10)
            y += 14
        pdf_bytes = doc.tobytes()
        doc.close()

        result = parse_pdf(pdf_bytes, filename="table_test.pdf")

        assert isinstance(result, ParseResult)
        # The text should contain pipe characters from the table
        assert "|" in result.text


class TestPdfMetadata:
    """Test PDF metadata extraction."""

    def test_pdf_metadata(self, sample_pdf_bytes):
        """ParseResult.metadata includes 'method' key."""
        from v2.parsers.pdf_parser import parse_pdf

        result = parse_pdf(sample_pdf_bytes, filename="test.pdf")
        assert "method" in result.metadata
        assert result.metadata["method"] in ("pymupdf4llm", "pdfplumber", "ocr", "none")


class TestPdfErrorHandling:
    """Test error handling for corrupt/empty PDFs."""

    def test_pdf_corrupt_file(self):
        """Parse garbage bytes -> returns ParseResult with warning, does not raise."""
        from v2.parsers.pdf_parser import parse_pdf

        result = parse_pdf(b"this is not a pdf at all", filename="corrupt.pdf")

        assert isinstance(result, ParseResult)
        assert len(result.warnings) > 0
        assert result.format == "pdf"

    def test_pdf_empty_file(self):
        """Parse empty bytes -> returns ParseResult with warning, text is empty or minimal."""
        from v2.parsers.pdf_parser import parse_pdf

        result = parse_pdf(b"", filename="empty.pdf")

        assert isinstance(result, ParseResult)
        assert len(result.warnings) > 0


class TestPdfOcrFallback:
    """Test OCR fallback for image-only PDFs."""

    def test_pdf_ocr_fallback(self):
        """Parse PDF with image-only page -> falls back to OCR if available."""
        pytest.importorskip("pytesseract", reason="tesseract not installed")

        from v2.parsers.pdf_parser import parse_pdf

        # Create a PDF with an image page (no selectable text)
        import fitz
        from PIL import Image
        import io

        # Create a simple image with text
        img = Image.new("RGB", (400, 100), color="white")
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="PNG")
        img_bytes.seek(0)

        doc = fitz.open()
        page = doc.new_page()
        page.insert_image(fitz.Rect(72, 72, 472, 172), stream=img_bytes.read())
        pdf_bytes = doc.tobytes()
        doc.close()

        result = parse_pdf(pdf_bytes, filename="scanned.pdf")

        assert isinstance(result, ParseResult)
        assert "method" in result.metadata
