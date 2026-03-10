"""
Extraction schemas - Phase 2 output.

ExtractedDoorPosition is the central data model: ~50+ German-named fields
representing every property of a door position extracted from tender documents.
Uses the enum+freitext pattern for extensible classification.
"""

from typing import Optional

from pydantic import BaseModel, Field

from v2.schemas.common import (
    BrandschutzKlasse,
    DokumentTyp,
    FieldSource,
    MaterialTyp,
    OeffnungsArt,
    SchallschutzKlasse,
    ZargenTyp,
)


class ExtractedDoorPosition(BaseModel):
    """Single door position extracted from tender documents.

    All fields except positions_nr are Optional with explicit defaults.
    Uses German field names consistent with product catalog and tender docs.
    """

    # ---- Identifikation ----
    positions_nr: str = Field(description="Position number e.g. '1.01'")
    positions_bezeichnung: Optional[str] = Field(
        None, description="Position description/name"
    )
    raum_nr: Optional[str] = Field(None, description="Room number")
    raum_bezeichnung: Optional[str] = Field(None, description="Room name/description")
    geschoss: Optional[str] = Field(None, description="Floor/level e.g. 'EG', 'OG1'")

    # ---- Masse (Dimensions) ----
    breite_mm: Optional[int] = Field(
        None, description="Door width in millimeters"
    )
    hoehe_mm: Optional[int] = Field(
        None, description="Door height in millimeters"
    )
    wandstaerke_mm: Optional[int] = Field(
        None, description="Wall thickness in millimeters"
    )
    falzmass_breite_mm: Optional[int] = Field(
        None, description="Rabbet dimension width in millimeters"
    )
    falzmass_hoehe_mm: Optional[int] = Field(
        None, description="Rabbet dimension height in millimeters"
    )
    lichtmass_breite_mm: Optional[int] = Field(
        None, description="Clear opening width in millimeters"
    )
    lichtmass_hoehe_mm: Optional[int] = Field(
        None, description="Clear opening height in millimeters"
    )
    tuerblatt_staerke_mm: Optional[int] = Field(
        None, description="Door leaf thickness in millimeters"
    )

    # ---- Brandschutz (Fire protection) ----
    brandschutz_klasse: Optional[BrandschutzKlasse] = Field(
        None, description="Fire protection class per EN 13501-2"
    )
    brandschutz_freitext: Optional[str] = Field(
        None, description="Raw text if value doesn't match known enum"
    )
    rauchschutz: Optional[bool] = Field(
        None, description="Smoke protection required"
    )
    rauchschutz_freitext: Optional[str] = Field(
        None, description="Smoke protection details"
    )

    # ---- Schallschutz (Sound protection) ----
    schallschutz_klasse: Optional[SchallschutzKlasse] = Field(
        None, description="Sound protection class"
    )
    schallschutz_db: Optional[int] = Field(
        None, description="Sound protection in dB (Rw value)"
    )
    schallschutz_freitext: Optional[str] = Field(
        None, description="Sound protection raw text"
    )

    # ---- Material ----
    material_blatt: Optional[MaterialTyp] = Field(
        None, description="Door leaf material type"
    )
    material_blatt_freitext: Optional[str] = Field(
        None, description="Door leaf material raw text"
    )
    material_zarge: Optional[ZargenTyp] = Field(
        None, description="Frame type"
    )
    material_zarge_freitext: Optional[str] = Field(
        None, description="Frame material/type raw text"
    )

    # ---- Ausfuehrung (Configuration) ----
    oeffnungsart: Optional[OeffnungsArt] = Field(
        None, description="Door opening type"
    )
    oeffnungsart_freitext: Optional[str] = Field(
        None, description="Opening type raw text"
    )
    anzahl_fluegel: Optional[int] = Field(
        None, description="Number of door leaves (1 or 2)"
    )
    anschlag_richtung: Optional[str] = Field(
        None, description="Hinge side e.g. 'links', 'rechts', 'DIN links'"
    )
    oberflaeche: Optional[str] = Field(
        None, description="Surface finish description"
    )
    farbe_ral: Optional[str] = Field(
        None, description="RAL color code e.g. 'RAL 9010'"
    )
    glasausschnitt: Optional[bool] = Field(
        None, description="Has glass cutout"
    )
    glasart: Optional[str] = Field(
        None, description="Glass type description"
    )
    glasgroesse: Optional[str] = Field(
        None, description="Glass cutout dimensions"
    )
    tuerblatt_ausfuehrung: Optional[str] = Field(
        None, description="Door leaf configuration details"
    )

    # ---- Beschlaege (Hardware) ----
    drueckergarnitur: Optional[str] = Field(
        None, description="Door handle/lever set"
    )
    schlossart: Optional[str] = Field(
        None, description="Lock type"
    )
    schliesszylinder: Optional[str] = Field(
        None, description="Lock cylinder type"
    )
    tuerband: Optional[str] = Field(
        None, description="Door hinge type"
    )
    tuerschliesser: Optional[str] = Field(
        None, description="Door closer type"
    )
    tuerstopper: Optional[str] = Field(
        None, description="Door stop type"
    )
    bodendichtung: Optional[str] = Field(
        None, description="Bottom seal type"
    )
    obentuerband: Optional[str] = Field(
        None, description="Top pivot/hinge"
    )

    # ---- Normen/Zertifizierungen (Standards) ----
    einbruchschutz_klasse: Optional[str] = Field(
        None, description="Burglary resistance class e.g. 'RC2', 'RC3'"
    )
    klimaklasse: Optional[str] = Field(
        None, description="Climate class e.g. 'III'"
    )
    nassraumeignung: Optional[bool] = Field(
        None, description="Suitable for wet rooms"
    )
    barrierefreiheit: Optional[bool] = Field(
        None, description="Barrier-free / accessible"
    )
    ce_kennzeichnung: Optional[str] = Field(
        None, description="CE marking details"
    )
    strahlenschutz: Optional[str] = Field(
        None, description="Radiation protection details"
    )
    hygieneschutz: Optional[str] = Field(
        None, description="Hygiene protection details"
    )
    beschusshemmend: Optional[str] = Field(
        None, description="Bullet resistance details"
    )

    # ---- Sonstiges (Other) ----
    bemerkungen: Optional[str] = Field(
        None, description="General remarks and notes"
    )
    anzahl: int = Field(1, description="Quantity of this position")
    seitenteil: Optional[str] = Field(
        None, description="Side panel details"
    )
    oberlicht: Optional[str] = Field(
        None, description="Transom/fanlight details"
    )

    # ---- Quellen (Source tracking) ----
    quellen: dict[str, FieldSource] = Field(
        default_factory=dict,
        description="Source provenance per field name, maps field name to its FieldSource"
    )


class ExtractionResult(BaseModel):
    """Complete extraction result from a document analysis."""

    positionen: list[ExtractedDoorPosition] = Field(
        description="All extracted door positions"
    )
    dokument_zusammenfassung: str = Field(
        description="Summary of the analyzed document"
    )
    warnungen: list[str] = Field(
        default_factory=list,
        description="Warnings encountered during extraction"
    )
    dokument_typ: DokumentTyp = Field(
        description="Type of the source document"
    )
