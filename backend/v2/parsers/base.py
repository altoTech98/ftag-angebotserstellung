"""
Base parser contract - ParseResult dataclass and BaseParser protocol.

Every document parser returns a ParseResult regardless of input format.
This is the uniform output contract for the parsing stage.
"""

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class ParseResult:
    """Uniform output from all document parsers.

    Parsers extract raw text and metadata only. AI structuring
    (extracting door positions, dimensions, etc.) is Phase 2's job.
    """

    text: str
    """Full extracted text. Markdown format for PDFs with tables."""

    format: str
    """Source format: 'pdf', 'docx', 'xlsx', 'txt'."""

    page_count: int = 0
    """Number of pages (PDF) or sheets (XLSX)."""

    warnings: list[str] = field(default_factory=list)
    """Non-fatal issues encountered during parsing."""

    metadata: dict = field(default_factory=dict)
    """Format-specific metadata (e.g., parsing method used, sheet names)."""

    source_file: str = ""
    """Original filename for provenance tracking."""

    tables: list[str] = field(default_factory=list)
    """Extracted table texts separately for downstream use."""


@runtime_checkable
class BaseParser(Protocol):
    """Protocol that all v2 parsers must implement."""

    def parse(self, content: bytes, filename: str = "") -> ParseResult:
        """Parse document content and return a uniform ParseResult.

        Args:
            content: Raw file bytes.
            filename: Original filename (for logging and provenance).

        Returns:
            ParseResult with extracted text and metadata.
        """
        ...
