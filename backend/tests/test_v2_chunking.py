"""
Tests for page-based text chunking utility.

Tests cover single-page documents, multi-page splitting with overlap,
and documents without page markers.
"""

import pytest


class TestChunking:

    def test_chunking_single_page(self):
        """Document with page_count <= chunk_size returns single chunk."""
        from v2.extraction.chunking import chunk_by_pages

        text = "This is a short document.\nWith some text."
        chunks = chunk_by_pages(text, page_count=5, chunk_size=30, overlap=5)
        assert len(chunks) == 1
        assert chunks[0]["start_page"] == 1
        assert chunks[0]["end_page"] == 5
        assert chunks[0]["text"] == text

    def test_chunking_splits_with_overlap(self):
        """60-page doc with chunk_size=30, overlap=5 produces correct page ranges."""
        from v2.extraction.chunking import chunk_by_pages

        # Build text with 60 pages separated by form feeds
        pages = [f"Content of page {i+1}" for i in range(60)]
        text = "\f".join(pages)

        chunks = chunk_by_pages(text, page_count=60, chunk_size=30, overlap=5)

        # Should produce at least 2 chunks
        assert len(chunks) >= 2

        # First chunk: pages 1-30
        assert chunks[0]["start_page"] == 1
        assert chunks[0]["end_page"] == 30

        # Second chunk: pages 26-55 (overlap=5)
        assert chunks[1]["start_page"] == 26
        assert chunks[1]["end_page"] == 55

        # Third chunk: pages 51-60
        assert chunks[2]["start_page"] == 51
        assert chunks[2]["end_page"] == 60

    def test_chunking_handles_no_page_markers(self):
        """Text without page markers still produces reasonable chunks."""
        from v2.extraction.chunking import chunk_by_pages

        # Long text, no form feeds or page markers
        text = "Some content. " * 500  # ~7000 chars
        chunks = chunk_by_pages(text, page_count=60, chunk_size=30, overlap=5)

        # Should still produce multiple chunks
        assert len(chunks) >= 2
        # Each chunk should have text content
        for chunk in chunks:
            assert len(chunk["text"]) > 0
            assert "start_page" in chunk
            assert "end_page" in chunk

    def test_chunking_empty_text(self):
        """Empty text returns a single empty chunk."""
        from v2.extraction.chunking import chunk_by_pages

        chunks = chunk_by_pages("", page_count=0, chunk_size=30, overlap=5)
        assert len(chunks) == 1
        assert chunks[0]["text"] == ""

    def test_chunking_page_marker_pattern(self):
        """Documents with '--- Page X ---' markers are split correctly."""
        from v2.extraction.chunking import chunk_by_pages

        pages = []
        for i in range(10):
            pages.append(f"--- Page {i+1} ---\nContent of page {i+1}")
        text = "\n".join(pages)

        chunks = chunk_by_pages(text, page_count=10, chunk_size=5, overlap=2)
        assert len(chunks) >= 2
        assert chunks[0]["start_page"] == 1
        assert chunks[0]["end_page"] == 5
