"""
Common types shared across all pipeline schemas.

Includes field-level source tracking, shared enums for domain values,
and the enum+freitext pattern for extensible classification.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Field-level source tracking
# ---------------------------------------------------------------------------

class FieldSource(BaseModel):
    """Provenance tracking for a single extracted field value."""

    dokument: str = Field(description="Source document filename")
    seite: Optional[int] = Field(
        None, description="Page number (PDF) or None"
    )
    zeile: Optional[int] = Field(
        None, description="Row number (Excel) or None"
    )
    zelle: Optional[str] = Field(
        None, description="Cell reference e.g. 'B15' (Excel)"
    )
    sheet: Optional[str] = Field(
        None, description="Sheet name (Excel) or None"
    )
    konfidenz: float = Field(
        1.0, description="Extraction confidence between 0.0 and 1.0"
    )
    # Phase 3: Cross-document enrichment provenance
    enrichment_source: Optional[str] = Field(
        None, description="Document that provided this value via cross-doc enrichment"
    )
    enrichment_type: Optional[str] = Field(
        None,
        description=(
            "Type of enrichment: 'gap_fill', 'confidence_upgrade', "
            "'general_spec', 'conflict_resolution'"
        ),
    )


class TrackedField(BaseModel):
    """A value with its source provenance."""

    wert: Optional[str] = None
    quelle: Optional[FieldSource] = None


# ---------------------------------------------------------------------------
# Domain enums - derived from product catalog + Swiss/EU standards
# ---------------------------------------------------------------------------

class BrandschutzKlasse(str, Enum):
    """Fire protection classes per EN 13501-2 and Swiss VKF standards."""

    EI30 = "EI30"
    EI60 = "EI60"
    EI90 = "EI90"
    EI120 = "EI120"
    E30 = "E30"
    E60 = "E60"
    E90 = "E90"
    T30 = "T30"    # Legacy Swiss designation
    T60 = "T60"
    T90 = "T90"
    KEINE = "keine"


class SchallschutzKlasse(str, Enum):
    """Sound protection classes based on weighted sound reduction index Rw."""

    RW_27 = "Rw 27dB"
    RW_29 = "Rw 29dB"
    RW_32 = "Rw 32dB"
    RW_35 = "Rw 35dB"
    RW_37 = "Rw 37dB"
    RW_41 = "Rw 41dB"
    RW_42 = "Rw 42dB"
    RW_43 = "Rw 43dB"
    RW_44 = "Rw 44dB"
    RW_45 = "Rw 45dB"
    RW_46 = "Rw 46dB"
    RW_47 = "Rw 47dB"
    RW_53 = "Rw 53dB"
    KEINE = "keine"


class MaterialTyp(str, Enum):
    """Door leaf and frame material types."""

    HOLZ = "Holz"
    STAHL = "Stahl"
    ALUMINIUM = "Aluminium"
    GLAS = "Glas"
    KUNSTSTOFF = "Kunststoff"
    HOLZ_STAHL = "Holz/Stahl"
    HOLZ_ALU = "Holz/Aluminium"
    EICHE = "Eiche"
    BUCHE = "Buche"
    FICHTE = "Fichte"
    LAERCHE = "Laerche"
    SONSTIGE = "Sonstige"


class ZargenTyp(str, Enum):
    """Frame (Zarge) types."""

    BLOCKZARGE = "Blockzarge"
    UMFASSUNGSZARGE = "Umfassungszarge"
    ECKZARGE = "Eckzarge"
    STAHLZARGE = "Stahlzarge"
    HOLZZARGE = "Holzzarge"
    FUTTERZARGE = "Futterzarge"
    SONSTIGE = "Sonstige"


class OeffnungsArt(str, Enum):
    """Door opening types - derived from product catalog Produktgruppen."""

    DREHFLUEGEL = "Drehfluegel"
    SCHIEBETUER = "Schiebetuer"
    PENDELTUER = "Pendeltuer"
    FALTTUER = "Falttuer"
    DREHKARUSSEL = "Drehkarussel"
    GANZGLASTUER = "Ganzglastuer"
    RAHMENTUER = "Rahmentuer"
    ZARGENTUER = "Zargentuer"
    FUTTERTUER = "Futtertuer"
    FESTVERGLASUNG = "Festverglasung"
    SONSTIGE = "Sonstige"


class DokumentTyp(str, Enum):
    """Supported document types for parsing."""

    PDF = "pdf"
    DOCX = "docx"
    XLSX = "xlsx"
    TXT = "txt"
    UNKNOWN = "unknown"
