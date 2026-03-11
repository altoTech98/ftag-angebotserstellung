"""
Matching schemas - Phase 4 output.

Multi-dimensional product matching with per-dimension scoring
and confidence breakdown.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class MatchDimension(str, Enum):
    """Dimensions along which a product match is scored."""

    MASSE = "Masse"
    BRANDSCHUTZ = "Brandschutz"
    SCHALLSCHUTZ = "Schallschutz"
    MATERIAL = "Material"
    ZERTIFIZIERUNG = "Zertifizierung"
    LEISTUNG = "Leistung"


class DimensionScore(BaseModel):
    """Score for a single matching dimension."""

    dimension: MatchDimension = Field(description="Which dimension this score covers")
    score: float = Field(description="Match score between 0.0 and 1.0")
    begruendung: str = Field(description="Reasoning for this dimension score")


class MatchCandidate(BaseModel):
    """A candidate product match with its scoring breakdown."""

    produkt_id: str = Field(description="Product ID from catalog")
    produkt_name: str = Field(description="Product name from catalog")
    gesamt_konfidenz: float = Field(
        description="Overall match confidence between 0.0 and 1.0"
    )
    dimension_scores: list[DimensionScore] = Field(
        default_factory=list,
        description="Per-dimension scoring breakdown"
    )
    begruendung: str = Field(description="Overall reasoning for this match")


class MatchResult(BaseModel):
    """Complete matching result for a single door position."""

    positions_nr: str = Field(description="Position number being matched")
    bester_match: Optional[MatchCandidate] = Field(
        None, description="Best matching product, or None if no match"
    )
    alternative_matches: list[MatchCandidate] = Field(
        default_factory=list,
        description="Alternative product matches ranked by confidence"
    )
    hat_match: bool = Field(description="Whether a suitable match was found")
    match_methode: str = Field(
        description="Method used: 'tfidf_ai', 'keyword_fallback', 'manual'"
    )
