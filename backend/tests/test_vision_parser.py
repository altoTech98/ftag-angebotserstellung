"""Tests for vision_parser service."""

import pytest
import sys
import os
from unittest.mock import patch, MagicMock
import base64

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ["TESTING"] = "true"
os.environ["ENVIRONMENT"] = "development"


class TestPageQualityCheck:
    """Tests for page quality assessment."""

    def test_good_quality_text(self):
        from services.vision_parser import assess_page_quality
        result = assess_page_quality("A" * 600, has_tables=False)
        assert result == "good"

    def test_poor_quality_short_text(self):
        from services.vision_parser import assess_page_quality
        result = assess_page_quality("short", has_tables=False)
        assert result == "poor"

    def test_poor_quality_empty(self):
        from services.vision_parser import assess_page_quality
        result = assess_page_quality("", has_tables=False)
        assert result == "poor"

    def test_table_without_text_is_poor(self):
        from services.vision_parser import assess_page_quality
        result = assess_page_quality("x" * 100, has_tables=True)
        assert result == "poor"


class TestBatchPages:
    """Tests for page batching logic."""

    def test_single_batch(self):
        from services.vision_parser import create_batches
        pages = list(range(10))
        batches = create_batches(pages, batch_size=40)
        assert len(batches) == 1
        assert batches[0] == pages

    def test_multiple_batches(self):
        from services.vision_parser import create_batches
        pages = list(range(100))
        batches = create_batches(pages, batch_size=40)
        assert len(batches) == 3
        assert len(batches[0]) == 40
        assert len(batches[1]) == 40
        assert len(batches[2]) == 20

    def test_empty_pages(self):
        from services.vision_parser import create_batches
        batches = create_batches([], batch_size=40)
        assert batches == []


class TestRenderPdfPages:
    """Tests for PDF page rendering."""

    def test_render_returns_images(self):
        from services.vision_parser import render_pdf_pages
        # Create minimal PDF using the helper from test_document_parser
        from tests.test_document_parser import _make_pdf
        pdf_bytes = _make_pdf(["Test page content here"])
        images = render_pdf_pages(pdf_bytes)
        assert len(images) >= 1
        assert all(hasattr(img, 'size') for img in images)  # PIL Image


class TestExtractPositionsFromVision:
    """Tests for parsing Claude Vision response into positions."""

    def test_parse_valid_response(self):
        from services.vision_parser import parse_vision_response
        response = '''[
            {"tuer_nr": "T01", "tuertyp": "Stahltür", "brandschutz": "EI30", "breite": 900, "hoehe": 2100, "menge": 1}
        ]'''
        positions = parse_vision_response(response)
        assert len(positions) == 1
        assert positions[0]["tuer_nr"] == "T01"
        assert positions[0]["brandschutz"] == "EI30"

    def test_parse_empty_response(self):
        from services.vision_parser import parse_vision_response
        positions = parse_vision_response("[]")
        assert positions == []

    def test_parse_invalid_json_returns_empty(self):
        from services.vision_parser import parse_vision_response
        positions = parse_vision_response("not json at all")
        assert positions == []


class TestMergeResults:
    """Tests for merging pdfplumber text + vision results."""

    def test_merge_text_and_vision(self):
        from services.vision_parser import merge_extraction_results
        text_pages = {1: "Seite 1 text content here"}
        vision_positions = [
            {"tuer_nr": "T01", "tuertyp": "Stahltür", "brandschutz": "EI30", "breite": 900, "hoehe": 2100, "menge": 1}
        ]
        result = merge_extraction_results(text_pages, vision_positions)
        assert "text" in result
        assert "positions" in result
        assert len(result["positions"]) == 1

    def test_merge_text_only(self):
        from services.vision_parser import merge_extraction_results
        text_pages = {1: "Lots of text", 2: "More text"}
        result = merge_extraction_results(text_pages, [])
        assert len(result["positions"]) == 0
        assert "Lots of text" in result["text"]
