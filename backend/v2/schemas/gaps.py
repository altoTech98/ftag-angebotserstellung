"""
Gap analysis schemas - Phase 6 output.

Identifies specification gaps between tender requirements and matched products,
categorizes by severity, and suggests alternatives.
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
    """Dimension in which a gap exists."""

    MASSE = "Masse"
    MATERIAL = "Material"
    NORM = "Norm"
    ZERTIFIZIERUNG = "Zertifizierung"
    LEISTUNG = "Leistung"


class GapItem(BaseModel):
    """A single specification gap."""

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
    aenderungsvorschlag: Optional[str] = Field(
        None, description="Suggested change or workaround"
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
