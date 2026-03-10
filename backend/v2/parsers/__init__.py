"""
V2 Parsers - Document format parsers returning uniform ParseResult.

Parsers extract raw text only. AI structuring happens in Phase 2 (extraction).
"""

from v2.parsers.base import BaseParser, ParseResult

__all__ = ["BaseParser", "ParseResult"]
