"""
Adversarial validation schemas - Phase 5 output.

Debate-format (FOR/AGAINST) validation of Phase 4 matches with
chain-of-thought reasoning and adaptive verbosity.
"""

from enum import Enum
from typing import Optional, Literal

from pydantic import BaseModel, Field


class ValidationStatus(str, Enum):
    """Adversarial validation outcome."""

    BESTAETIGT = "bestaetigt"   # Confirmed at 95%+
    UNSICHER = "unsicher"       # Best effort but <95% after all passes
    ABGELEHNT = "abgelehnt"    # No viable match found


class DimensionCoT(BaseModel):
    """Chain-of-thought reasoning for a single matching dimension."""

    dimension: str = Field(description="Dimension name (Masse, Brandschutz, etc.)")
    score: float = Field(description="Adjusted score after adversarial review (0.0-1.0)")
    reasoning: str = Field(description="Chain-of-thought reasoning for this dimension")
    confidence_level: Literal["hoch", "niedrig"] = Field(
        description="Adaptive verbosity: 'hoch' for score > 0.9, 'niedrig' for <= 0.9"
    )


class CandidateDebate(BaseModel):
    """FOR and AGAINST debate arguments for a single candidate."""

    produkt_id: str = Field(description="Product ID from catalog")
    produkt_name: str = Field(description="Product name from catalog")
    for_argument: str = Field(description="Arguments supporting this match")
    against_argument: str = Field(description="Arguments challenging this match")
    for_confidence: float = Field(description="FOR-side confidence (0.0-1.0)")
    against_confidence: float = Field(description="AGAINST-side confidence (0.0-1.0)")


class AdversarialCandidate(BaseModel):
    """A candidate with adjusted confidence after adversarial review."""

    produkt_id: str = Field(description="Product ID from catalog")
    produkt_name: str = Field(description="Product name from catalog")
    adjusted_confidence: float = Field(
        description="Post-adversarial confidence (0.0-1.0)"
    )
    dimension_scores: list[DimensionCoT] = Field(
        default_factory=list,
        description="Per-dimension chain-of-thought scoring",
    )
    reasoning_summary: str = Field(
        description="Summary of adversarial reasoning for this candidate"
    )


class AdversarialResult(BaseModel):
    """Complete adversarial validation result for a single door position.

    Links to MatchResult by positions_nr. MatchResult remains untouched;
    this is a separate parallel structure with debate arguments,
    per-dimension CoT, and adjusted confidence.
    """

    positions_nr: str = Field(description="Position number (links to MatchResult)")
    validation_status: ValidationStatus = Field(
        description="Final verdict: bestaetigt (95%+), unsicher (<95%), abgelehnt (no match)"
    )
    adjusted_confidence: float = Field(
        description="Post-adversarial adjusted confidence (0.0-1.0)"
    )
    bester_match: Optional[AdversarialCandidate] = Field(
        None, description="Best candidate after adversarial review"
    )
    alternative_candidates: list[AdversarialCandidate] = Field(
        default_factory=list,
        description="Alternative candidates with individual scores and reasoning",
    )
    debate: list[CandidateDebate] = Field(
        default_factory=list,
        description="FOR/AGAINST debate entries for each debated candidate",
    )
    resolution_reasoning: str = Field(
        description="Final synthesis explaining the verdict"
    )
    per_dimension_cot: list[DimensionCoT] = Field(
        default_factory=list,
        description="Per-dimension chain-of-thought for the best match",
    )
    triple_check_used: bool = Field(
        default=False,
        description="Whether triple-check ensemble was triggered",
    )
    triple_check_method: Optional[str] = Field(
        None, description="Triple-check method used (wider_pool, inverted_prompt)"
    )
    triple_check_reasoning: Optional[str] = Field(
        None, description="Reasoning from triple-check pass"
    )
    api_calls_count: int = Field(
        default=2,
        description="Number of Opus API calls used (2 for standard debate)",
    )


# ---------------------------------------------------------------------------
# Structured output models for messages.parse (Opus API)
# ---------------------------------------------------------------------------


class ForDimensionBewertung(BaseModel):
    """Single dimension evaluation from FOR perspective."""

    dimension: str = Field(description="Dimension name")
    score: float = Field(description="Score from FOR perspective (0.0-1.0)")
    begruendung: str = Field(description="Reasoning from FOR perspective")


class ForArgument(BaseModel):
    """Structured output for the FOR (supporting) Opus call.

    Used as output_format in client.messages.parse().
    """

    produkt_id: str = Field(description="Product ID being defended")
    produkt_name: str = Field(description="Product name being defended")
    for_konfidenz: float = Field(
        description="Overall confidence that this is the correct match (0.0-1.0)"
    )
    dimension_bewertungen: list[ForDimensionBewertung] = Field(
        description="Per-dimension FOR evaluation"
    )
    zusammenfassung: str = Field(
        description="Summary of FOR argument"
    )


class AgainstDimensionBewertung(BaseModel):
    """Single dimension evaluation from AGAINST perspective."""

    dimension: str = Field(description="Dimension name")
    score: float = Field(description="Score from AGAINST perspective (0.0-1.0)")
    begruendung: str = Field(description="Reasoning from AGAINST perspective")


class AgainstArgument(BaseModel):
    """Structured output for the AGAINST (challenging) Opus call.

    Used as output_format in client.messages.parse().
    """

    produkt_id: str = Field(description="Product ID being challenged")
    produkt_name: str = Field(description="Product name being challenged")
    against_konfidenz: float = Field(
        description="Confidence that this match is WRONG (0.0-1.0)"
    )
    dimension_bewertungen: list[AgainstDimensionBewertung] = Field(
        description="Per-dimension AGAINST evaluation"
    )
    zusammenfassung: str = Field(
        description="Summary of AGAINST argument"
    )
