"""
Gap analysis schemas - Phase 6 output.

Identifies specification gaps between tender requirements and matched products,
categorizes by severity, and suggests alternatives. Includes safety
auto-escalation (Brandschutz/Schallschutz MINOR -> MAJOR), dual suggestions
(Kundenvorschlag + Technischer Hinweis), and bidirectional cross-references
between gaps and alternative products.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class GapSeverity(str, Enum):
    """Severity level of a specification gap."""

    KRITISCH = "kritisch"
    MAJOR = "major"
    MINOR = "minor"


class GapDimension(str, Enum):
    """Dimension in which a gap exists.

    1:1 mapping with MatchDimension from Phase 4.
    """

    MASSE = "Masse"
    BRANDSCHUTZ = "Brandschutz"
    SCHALLSCHUTZ = "Schallschutz"
    MATERIAL = "Material"
    ZERTIFIZIERUNG = "Zertifizierung"
    LEISTUNG = "Leistung"


class GapItem(BaseModel):
    """A single specification gap with dual suggestions and cross-references."""

    dimension: GapDimension = Field(description="Gap dimension category")
    schweregrad: GapSeverity = Field(description="Severity of this gap")
    anforderung_wert: str = Field(
        description="Required value from tender document"
    )
    katalog_wert: Optional[str] = Field(
        None, description="Matched product's value, if available"
    )
    abweichung_beschreibung: str = Field(
        description="Description of the deviation"
    )
    kundenvorschlag: Optional[str] = Field(
        None, description="Sales-friendly suggestion for the customer"
    )
    technischer_hinweis: Optional[str] = Field(
        None, description="Technical suggestion for engineering"
    )
    gap_geschlossen_durch: list[str] = Field(
        default_factory=list,
        description="Product IDs of alternatives that close this gap"
    )


class AlternativeProduct(BaseModel):
    """An alternative product that partially covers the gaps."""

    produkt_id: str = Field(description="Alternative product ID")
    produkt_name: str = Field(description="Alternative product name")
    teilweise_deckung: float = Field(
        description="Partial coverage ratio between 0.0 and 1.0"
    )
    verbleibende_gaps: list[str] = Field(
        default_factory=list,
        description="Remaining gaps not covered by this alternative"
    )
    geschlossene_gaps: list[str] = Field(
        default_factory=list,
        description="Gap dimensions closed by this alternative"
    )


class GapReport(BaseModel):
    """Complete gap analysis for a single door position."""

    positions_nr: str = Field(description="Position number analyzed")
    gaps: list[GapItem] = Field(
        default_factory=list,
        description="All identified specification gaps"
    )
    alternativen: list[AlternativeProduct] = Field(
        default_factory=list,
        description="Alternative products that partially cover gaps"
    )
    zusammenfassung: str = Field(
        description="Summary of gap analysis findings"
    )
    validation_status: str = Field(
        default="",
        description="Validation status from Phase 5: bestaetigt/unsicher/abgelehnt"
    )


# ---------------------------------------------------------------------------
# Structured output model for Opus gap analysis calls
# ---------------------------------------------------------------------------


class GapAnalysisResponseItem(BaseModel):
    """A single gap item in the Opus structured output."""

    dimension: GapDimension = Field(description="Gap dimension")
    schweregrad: GapSeverity = Field(description="Severity")
    anforderung_wert: str = Field(description="Required value")
    katalog_wert: Optional[str] = Field(None, description="Product value")
    abweichung_beschreibung: str = Field(description="Deviation description")
    kundenvorschlag: Optional[str] = Field(None, description="Customer suggestion")
    technischer_hinweis: Optional[str] = Field(None, description="Technical hint")


class GapAnalysisResponse(BaseModel):
    """Structured output model for Opus gap analysis calls.

    Internal model for parsing Opus responses. NOT the final GapReport.
    Uses GapDimension and GapSeverity enums so Opus returns valid enum values.
    """

    gaps: list[GapAnalysisResponseItem] = Field(
        description="Identified specification gaps"
    )
    zusammenfassung: str = Field(
        description="Summary of gap analysis findings"
    )


# ---------------------------------------------------------------------------
# Safety auto-escalation
# ---------------------------------------------------------------------------

SAFETY_DIMENSIONS = {GapDimension.BRANDSCHUTZ, GapDimension.SCHALLSCHUTZ}


def apply_safety_escalation(gaps: list[GapItem]) -> list[GapItem]:
    """Upgrade MINOR to MAJOR for safety-critical dimensions.

    Brandschutz and Schallschutz gaps are never rated MINOR -- they are
    automatically escalated to MAJOR. Mirrors Phase 4 safety cap pattern.

    Args:
        gaps: List of gap items to process.

    Returns:
        New list with escalated severities (original items are not mutated).
    """
    result = []
    for gap in gaps:
        if gap.dimension in SAFETY_DIMENSIONS and gap.schweregrad == GapSeverity.MINOR:
            result.append(gap.model_copy(update={"schweregrad": GapSeverity.MAJOR}))
        else:
            result.append(gap)
    return result
