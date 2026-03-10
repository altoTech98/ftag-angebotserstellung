"""
Tests for Phase 6 gap analysis schemas and functionality.

Covers:
- GapDimension enum values (1:1 with MatchDimension)
- Safety auto-escalation (MINOR -> MAJOR for Brandschutz/Schallschutz)
- GapItem, AlternativeProduct, GapReport expanded fields
- GapAnalysisResponse structured output model
"""

import pytest

from v2.schemas.matching import MatchDimension


class TestGapDimensions:
    """Verify GapDimension enum has 6 values matching MatchDimension."""

    def test_gap_dimension_has_six_values(self):
        from v2.schemas.gaps import GapDimension
        assert len(GapDimension) == 6

    def test_gap_dimension_matches_match_dimension(self):
        from v2.schemas.gaps import GapDimension
        gap_values = {d.value for d in GapDimension}
        match_values = {d.value for d in MatchDimension}
        assert gap_values == match_values

    def test_gap_dimension_individual_values(self):
        from v2.schemas.gaps import GapDimension
        assert GapDimension.MASSE.value == "Masse"
        assert GapDimension.BRANDSCHUTZ.value == "Brandschutz"
        assert GapDimension.SCHALLSCHUTZ.value == "Schallschutz"
        assert GapDimension.MATERIAL.value == "Material"
        assert GapDimension.ZERTIFIZIERUNG.value == "Zertifizierung"
        assert GapDimension.LEISTUNG.value == "Leistung"


class TestSeverityEscalation:
    """Verify apply_safety_escalation upgrades MINOR for safety dimensions."""

    def test_brandschutz_minor_upgraded_to_major(self):
        from v2.schemas.gaps import GapItem, GapDimension, GapSeverity, apply_safety_escalation
        gap = GapItem(
            dimension=GapDimension.BRANDSCHUTZ,
            schweregrad=GapSeverity.MINOR,
            anforderung_wert="EI60",
            katalog_wert="EI30",
            abweichung_beschreibung="Brandschutzklasse zu niedrig",
        )
        result = apply_safety_escalation([gap])
        assert result[0].schweregrad == GapSeverity.MAJOR

    def test_schallschutz_minor_upgraded_to_major(self):
        from v2.schemas.gaps import GapItem, GapDimension, GapSeverity, apply_safety_escalation
        gap = GapItem(
            dimension=GapDimension.SCHALLSCHUTZ,
            schweregrad=GapSeverity.MINOR,
            anforderung_wert="42dB",
            katalog_wert="37dB",
            abweichung_beschreibung="Schallschutz unzureichend",
        )
        result = apply_safety_escalation([gap])
        assert result[0].schweregrad == GapSeverity.MAJOR

    def test_material_minor_stays_minor(self):
        from v2.schemas.gaps import GapItem, GapDimension, GapSeverity, apply_safety_escalation
        gap = GapItem(
            dimension=GapDimension.MATERIAL,
            schweregrad=GapSeverity.MINOR,
            anforderung_wert="Stahl",
            katalog_wert="Holz",
            abweichung_beschreibung="Material abweichend",
        )
        result = apply_safety_escalation([gap])
        assert result[0].schweregrad == GapSeverity.MINOR

    def test_masse_minor_stays_minor(self):
        from v2.schemas.gaps import GapItem, GapDimension, GapSeverity, apply_safety_escalation
        gap = GapItem(
            dimension=GapDimension.MASSE,
            schweregrad=GapSeverity.MINOR,
            anforderung_wert="900x2100",
            katalog_wert="900x2000",
            abweichung_beschreibung="Hoehe weicht ab",
        )
        result = apply_safety_escalation([gap])
        assert result[0].schweregrad == GapSeverity.MINOR

    def test_major_stays_major(self):
        from v2.schemas.gaps import GapItem, GapDimension, GapSeverity, apply_safety_escalation
        gap = GapItem(
            dimension=GapDimension.BRANDSCHUTZ,
            schweregrad=GapSeverity.MAJOR,
            anforderung_wert="EI90",
            katalog_wert="EI60",
            abweichung_beschreibung="Brandschutzklasse zu niedrig",
        )
        result = apply_safety_escalation([gap])
        assert result[0].schweregrad == GapSeverity.MAJOR

    def test_kritisch_stays_kritisch(self):
        from v2.schemas.gaps import GapItem, GapDimension, GapSeverity, apply_safety_escalation
        gap = GapItem(
            dimension=GapDimension.BRANDSCHUTZ,
            schweregrad=GapSeverity.KRITISCH,
            anforderung_wert="EI120",
            katalog_wert="EI30",
            abweichung_beschreibung="Massive Abweichung",
        )
        result = apply_safety_escalation([gap])
        assert result[0].schweregrad == GapSeverity.KRITISCH


class TestGapSchemas:
    """Verify expanded GapItem, AlternativeProduct, GapReport fields."""

    def test_gap_item_dual_suggestions(self):
        from v2.schemas.gaps import GapItem, GapDimension, GapSeverity
        gap = GapItem(
            dimension=GapDimension.BRANDSCHUTZ,
            schweregrad=GapSeverity.MAJOR,
            anforderung_wert="EI60",
            katalog_wert="EI30",
            abweichung_beschreibung="Brandschutzklasse zu niedrig",
            kundenvorschlag="Wir empfehlen ein Upgrade auf EI60",
            technischer_hinweis="Tuerblatt muss ausgetauscht werden",
            gap_geschlossen_durch=["PROD-001", "PROD-002"],
        )
        assert gap.kundenvorschlag == "Wir empfehlen ein Upgrade auf EI60"
        assert gap.technischer_hinweis == "Tuerblatt muss ausgetauscht werden"
        assert gap.gap_geschlossen_durch == ["PROD-001", "PROD-002"]

    def test_gap_item_no_aenderungsvorschlag(self):
        """The old aenderungsvorschlag field should not exist."""
        from v2.schemas.gaps import GapItem, GapDimension, GapSeverity
        gap = GapItem(
            dimension=GapDimension.MATERIAL,
            schweregrad=GapSeverity.MINOR,
            anforderung_wert="Stahl",
            abweichung_beschreibung="Material",
        )
        assert not hasattr(gap, "aenderungsvorschlag")

    def test_alternative_product_geschlossene_gaps(self):
        from v2.schemas.gaps import AlternativeProduct
        alt = AlternativeProduct(
            produkt_id="PROD-001",
            produkt_name="Rahmentuere EI60",
            teilweise_deckung=0.67,
            verbleibende_gaps=["Schallschutz"],
            geschlossene_gaps=["Brandschutz", "Masse"],
        )
        assert alt.geschlossene_gaps == ["Brandschutz", "Masse"]

    def test_gap_report_validation_status(self):
        from v2.schemas.gaps import GapReport
        report = GapReport(
            positions_nr="1.01",
            zusammenfassung="Alle Anforderungen erfuellt",
            validation_status="bestaetigt",
        )
        assert report.validation_status == "bestaetigt"

    def test_gap_report_full_construction(self):
        from v2.schemas.gaps import GapReport, GapItem, GapDimension, GapSeverity, AlternativeProduct
        gap = GapItem(
            dimension=GapDimension.BRANDSCHUTZ,
            schweregrad=GapSeverity.MAJOR,
            anforderung_wert="EI60",
            katalog_wert="EI30",
            abweichung_beschreibung="Brandschutz zu niedrig",
            kundenvorschlag="Upgrade empfohlen",
            technischer_hinweis="Neues Tuerblatt erforderlich",
            gap_geschlossen_durch=["PROD-002"],
        )
        alt = AlternativeProduct(
            produkt_id="PROD-002",
            produkt_name="Brandschutztuere EI60",
            teilweise_deckung=1.0,
            verbleibende_gaps=[],
            geschlossene_gaps=["Brandschutz"],
        )
        report = GapReport(
            positions_nr="1.01",
            gaps=[gap],
            alternativen=[alt],
            zusammenfassung="Brandschutzluecke mit Alternative geschlossen",
            validation_status="unsicher",
        )
        assert len(report.gaps) == 1
        assert len(report.alternativen) == 1
        assert report.validation_status == "unsicher"


class TestGapAnalysisResponse:
    """Verify GapAnalysisResponse structured output model."""

    def test_valid_construction(self):
        from v2.schemas.gaps import GapAnalysisResponse, GapDimension, GapSeverity
        response = GapAnalysisResponse(
            gaps=[
                {
                    "dimension": GapDimension.BRANDSCHUTZ,
                    "schweregrad": GapSeverity.MAJOR,
                    "anforderung_wert": "EI60",
                    "katalog_wert": "EI30",
                    "abweichung_beschreibung": "Brandschutzklasse zu niedrig",
                    "kundenvorschlag": "Upgrade empfohlen",
                    "technischer_hinweis": "Tuerblatt tauschen",
                }
            ],
            zusammenfassung="Eine Luecke im Brandschutz",
        )
        assert len(response.gaps) == 1
        assert response.gaps[0].dimension == GapDimension.BRANDSCHUTZ

    def test_rejects_invalid_dimension(self):
        from v2.schemas.gaps import GapAnalysisResponse, GapSeverity
        with pytest.raises(Exception):
            GapAnalysisResponse(
                gaps=[
                    {
                        "dimension": "UngueltigeDimension",
                        "schweregrad": GapSeverity.MINOR,
                        "anforderung_wert": "X",
                        "katalog_wert": "Y",
                        "abweichung_beschreibung": "Test",
                    }
                ],
                zusammenfassung="Test",
            )
