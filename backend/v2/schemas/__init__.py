"""
V2 Pipeline Schemas - Pydantic v2 data contracts for all pipeline stages.

All schemas are compatible with anthropic messages.parse() for structured output.
"""

from v2.schemas.extraction import ExtractedDoorPosition, ExtractionResult
from v2.schemas.gaps import GapReport
from v2.schemas.matching import MatchResult
from v2.schemas.pipeline import AnalysisJob
from v2.schemas.validation import AdversarialResult

__all__ = [
    "ExtractedDoorPosition",
    "ExtractionResult",
    "MatchResult",
    "AdversarialResult",
    "GapReport",
    "AnalysisJob",
]
