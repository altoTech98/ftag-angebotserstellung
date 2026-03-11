"""
Page-based text chunking for multi-pass AI extraction.

Splits parsed document text into overlapping chunks respecting page boundaries.
Used to feed manageable portions of text to AI passes (Pass 2 and Pass 3).
"""

import re
from typing import Optional


# Page marker patterns
_FORMFEED_RE = re.compile(r"\f")
_PAGE_MARKER_RE = re.compile(r"---\s*Page\s+(\d+)\s*---", re.IGNORECASE)


def _split_by_formfeeds(text: str) -> list[str]:
    """Split text on form feed characters."""
    return text.split("\f")


def _split_by_page_markers(text: str) -> list[str]:
    """Split text on '--- Page X ---' patterns."""
    parts = _PAGE_MARKER_RE.split(text)
    # split produces: [before_first_marker, page_num_1, content_1, page_num_2, content_2, ...]
    if len(parts) <= 1:
        return []

    pages = []
    # First part (before any marker) might be empty or a preamble
    if parts[0].strip():
        pages.append(parts[0])

    # Recombine page number with its content
    for i in range(1, len(parts), 2):
        page_num = parts[i]
        content = parts[i + 1] if i + 1 < len(parts) else ""
        pages.append(f"--- Page {page_num} ---\n{content}")

    return pages


def _split_by_estimated_pages(text: str, page_count: int) -> list[str]:
    """Split text into roughly equal chunks based on estimated page count.

    Falls back to splitting by double-newlines or by character count.
    """
    if page_count <= 0:
        return [text]

    # Try splitting on double newlines first
    paragraphs = text.split("\n\n")
    if len(paragraphs) >= page_count:
        # Distribute paragraphs across pages
        pages = []
        per_page = max(1, len(paragraphs) // page_count)
        for i in range(0, len(paragraphs), per_page):
            chunk = "\n\n".join(paragraphs[i : i + per_page])
            if chunk.strip():
                pages.append(chunk)
        return pages if pages else [text]

    # Fall back to character-based splitting
    chars_per_page = max(1, len(text) // page_count)
    pages = []
    for i in range(0, len(text), chars_per_page):
        chunk = text[i : i + chars_per_page]
        if chunk.strip():
            pages.append(chunk)
    return pages if pages else [text]


def _split_into_pages(text: str, page_count: int) -> list[str]:
    """Split text into individual page texts using best available method."""
    if not text:
        return [""]

    # Method 1: Form feeds
    if "\f" in text:
        pages = _split_by_formfeeds(text)
        if len(pages) > 1:
            return pages

    # Method 2: Page markers
    pages = _split_by_page_markers(text)
    if pages:
        return pages

    # Method 3: Estimated splitting
    return _split_by_estimated_pages(text, page_count)


def chunk_by_pages(
    text: str,
    page_count: int,
    chunk_size: int = 30,
    overlap: int = 5,
) -> list[dict]:
    """Split text into overlapping page-based chunks.

    Args:
        text: Full document text.
        page_count: Total number of pages in the document.
        chunk_size: Maximum pages per chunk.
        overlap: Number of pages to overlap between chunks.

    Returns:
        List of dicts with keys: text, start_page, end_page.
    """
    if not text or page_count <= 0:
        return [{"text": text or "", "start_page": 1, "end_page": max(page_count, 1)}]

    # Single chunk case
    if page_count <= chunk_size:
        return [{"text": text, "start_page": 1, "end_page": page_count}]

    # Split into pages
    pages = _split_into_pages(text, page_count)
    total_pages = len(pages)

    # If splitting produced fewer pages than expected, adjust
    if total_pages <= chunk_size:
        return [{"text": text, "start_page": 1, "end_page": page_count}]

    # Build overlapping chunks
    chunks = []
    step = chunk_size - overlap
    if step <= 0:
        step = 1

    i = 0
    while i < total_pages:
        end = min(i + chunk_size, total_pages)
        chunk_pages = pages[i:end]
        chunk_text = "\n".join(chunk_pages)

        # Map page indices back to 1-based page numbers
        # Scale to match the declared page_count
        start_page = int(i * page_count / total_pages) + 1
        end_page = int((end - 1) * page_count / total_pages) + 1
        end_page = min(end_page, page_count)

        chunks.append({
            "text": chunk_text,
            "start_page": start_page,
            "end_page": end_page,
        })

        if end >= total_pages:
            break
        i += step

    return chunks
