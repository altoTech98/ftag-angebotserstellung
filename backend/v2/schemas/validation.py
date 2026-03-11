"""
Validation schemas - Phase 5 output.

Adversarial validation using independent AI review with
chain-of-thought reasoning to verify match quality.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from v2.schemas.matching import MatchCandidate


class ValidationOutcome(str, Enum):
    """Result of adversarial validation."""

    BESTAETIGT = "bestaetigt"
    ABGELEHNT = "abgelehnt"
    UNSICHER = "unsicher"


class AdversarialResult(BaseModel):
    """Result of adversarial validation for a single match."""

    positions_nr: str = Field(description="Position number being validated")
    original_match: MatchCandidate = Field(
        description="The match being validated"
    )
    ergebnis: ValidationOutcome = Field(
        description="Validation outcome"
    )
    adversarial_begruendung: str = Field(
        description="Detailed reasoning for the validation decision"
    )
    chain_of_thought: list[str] = Field(
        default_factory=list,
        description="Step-by-step reasoning chain"
    )
    finale_konfidenz: float = Field(
        description="Final confidence after validation, between 0.0 and 1.0"
    )
    triple_check_durchgefuehrt: bool = Field(
        False,
        description="Whether triple-check was triggered (for edge cases)"
    )
    triple_check_ergebnis: Optional[str] = Field(
        None,
        description="Triple-check result if performed"
    )
