"""
Tests for Phase 6 gap analysis schemas and functionality.

Covers:
- GapDimension enum values (1:1 with MatchDimension)
- Safety auto-escalation (MINOR -> MAJOR for Brandschutz/Schallschutz)
- GapItem, AlternativeProduct, GapReport expanded fields
- GapAnalysisResponse structured output model
- Gap analyzer engine with mocked Opus calls
- Alternative search with mocked TF-IDF index
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from v2.schemas.matching import MatchDimension, MatchResult, MatchCandidate


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


# ---------------------------------------------------------------------------
# Integration-style tests for gap analyzer
# ---------------------------------------------------------------------------

from v2.schemas.adversarial import (
    AdversarialResult,
    AdversarialCandidate,
    DimensionCoT,
    ValidationStatus,
)
from v2.schemas.gaps import (
    AlternativeProduct,
    GapAnalysisResponse,
    GapAnalysisResponseItem,
    GapDimension,
    GapItem,
    GapReport,
    GapSeverity,
)
from v2.gaps.gap_analyzer import (
    analyze_single_position_gaps,
    search_alternatives_for_gaps,
    _cross_reference_gaps_and_alternatives,
)


def _make_match_result(pos_nr="1.01", has_match=True):
    """Create a minimal MatchResult for testing."""
    if has_match:
        candidate = MatchCandidate(
            produkt_id="PROD-100",
            produkt_name="Rahmentuere Standard",
            gesamt_konfidenz=0.85,
            begruendung="Guter Match",
        )
        return MatchResult(
            positions_nr=pos_nr,
            bester_match=candidate,
            hat_match=True,
            match_methode="tfidf_ai",
        )
    return MatchResult(
        positions_nr=pos_nr,
        bester_match=None,
        hat_match=False,
        match_methode="tfidf_ai",
    )


def _make_adversarial_result(
    pos_nr="1.01",
    status=ValidationStatus.BESTAETIGT,
    cot_scores=None,
):
    """Create a minimal AdversarialResult for testing."""
    if cot_scores is None:
        cot_scores = {
            "Masse": 1.0,
            "Brandschutz": 0.8,
            "Schallschutz": 1.0,
            "Material": 1.0,
            "Zertifizierung": 1.0,
            "Leistung": 1.0,
        }
    cot_list = [
        DimensionCoT(
            dimension=dim,
            score=score,
            reasoning=f"{dim} Bewertung",
            confidence_level="hoch" if score > 0.9 else "niedrig",
        )
        for dim, score in cot_scores.items()
    ]
    return AdversarialResult(
        positions_nr=pos_nr,
        validation_status=status,
        adjusted_confidence=0.90,
        per_dimension_cot=cot_list,
        debate=[],
        resolution_reasoning="Test resolution",
    )


def _make_mock_opus_response(gaps_data, zusammenfassung="Test Zusammenfassung"):
    """Create a mock Opus parse response."""
    parsed = GapAnalysisResponse(
        gaps=[
            GapAnalysisResponseItem(**g) for g in gaps_data
        ],
        zusammenfassung=zusammenfassung,
    )
    mock_response = MagicMock()
    mock_response.parsed = parsed
    return mock_response


def _make_mock_tfidf_index(search_results=None, candidate_fields=None):
    """Create a mock TF-IDF index for testing."""
    mock = MagicMock()
    if search_results is None:
        search_results = [
            (0, 0.9),
            (1, 0.8),
            (2, 0.7),
            (3, 0.6),
            (4, 0.5),
        ]
    mock.search.return_value = search_results

    if candidate_fields is None:
        candidate_fields = {
            0: {"Kostentraeger": "PROD-100", "Produktegruppen": "Rahmentuere", "Brandschutzklasse": "EI30", "row_index": 0},
            1: {"Kostentraeger": "PROD-201", "Produktegruppen": "Rahmentuere EI60", "Brandschutzklasse": "EI60", "row_index": 1},
            2: {"Kostentraeger": "PROD-202", "Produktegruppen": "Brandschutztuere", "Brandschutzklasse": "EI60", "Widerstandsklasse": "RC2", "row_index": 2},
            3: {"Kostentraeger": "PROD-203", "Produktegruppen": "Schallschutztuere", "Tuerrohling (dB)": "42", "row_index": 3},
            4: {"Kostentraeger": "PROD-204", "Produktegruppen": "Standardtuere", "row_index": 4},
        }

    def extract_fields(row_idx):
        return candidate_fields.get(row_idx, {"row_index": row_idx})

    mock.extract_candidate_fields.side_effect = extract_fields
    return mock


class TestGapAnalyzer:
    """Test analyze_single_position_gaps with mocked Anthropic client."""

    def test_bestaetigt_one_non_perfect_dimension(self):
        """Bestaetigt with one non-perfect dimension produces 1 gap item."""
        mock_client = MagicMock()
        mock_client.messages.parse.return_value = _make_mock_opus_response(
            gaps_data=[
                {
                    "dimension": "Brandschutz",
                    "schweregrad": "major",
                    "anforderung_wert": "EI60",
                    "katalog_wert": "EI30",
                    "abweichung_beschreibung": "Brandschutzklasse zu niedrig",
                    "kundenvorschlag": "Upgrade auf EI60",
                    "technischer_hinweis": "Tuerblatt tauschen",
                }
            ],
            zusammenfassung="Brandschutz-Luecke identifiziert",
        )

        mr = _make_match_result()
        ar = _make_adversarial_result(
            status=ValidationStatus.BESTAETIGT,
            cot_scores={
                "Masse": 1.0, "Brandschutz": 0.7, "Schallschutz": 1.0,
                "Material": 1.0, "Zertifizierung": 1.0, "Leistung": 1.0,
            },
        )

        semaphore = asyncio.Semaphore(3)
        result = asyncio.get_event_loop().run_until_complete(
            analyze_single_position_gaps(
                client=mock_client,
                match_result=mr,
                adversarial_result=ar,
                tfidf_index=None,
                semaphore=semaphore,
            )
        )

        assert isinstance(result, GapReport)
        assert len(result.gaps) == 1
        assert result.gaps[0].dimension == GapDimension.BRANDSCHUTZ
        assert result.validation_status == "bestaetigt"

    def test_bestaetigt_all_perfect_returns_empty(self):
        """Bestaetigt with all perfect scores returns empty gaps."""
        mock_client = MagicMock()
        mr = _make_match_result()
        ar = _make_adversarial_result(
            status=ValidationStatus.BESTAETIGT,
            cot_scores={
                "Masse": 1.0, "Brandschutz": 1.0, "Schallschutz": 1.0,
                "Material": 1.0, "Zertifizierung": 1.0, "Leistung": 1.0,
            },
        )

        semaphore = asyncio.Semaphore(3)
        result = asyncio.get_event_loop().run_until_complete(
            analyze_single_position_gaps(
                client=mock_client,
                match_result=mr,
                adversarial_result=ar,
                tfidf_index=None,
                semaphore=semaphore,
            )
        )

        assert len(result.gaps) == 0
        assert "perfekt" in result.zusammenfassung.lower() or "keine" in result.zusammenfassung.lower()

    def test_unsicher_produces_all_dimension_gaps(self):
        """Unsicher produces gap items for all reported dimensions."""
        mock_client = MagicMock()
        mock_client.messages.parse.return_value = _make_mock_opus_response(
            gaps_data=[
                {
                    "dimension": "Brandschutz",
                    "schweregrad": "major",
                    "anforderung_wert": "EI60",
                    "katalog_wert": "EI30",
                    "abweichung_beschreibung": "Zu niedrig",
                },
                {
                    "dimension": "Schallschutz",
                    "schweregrad": "minor",
                    "anforderung_wert": "42dB",
                    "katalog_wert": "37dB",
                    "abweichung_beschreibung": "Schallschutz unzureichend",
                },
                {
                    "dimension": "Masse",
                    "schweregrad": "minor",
                    "anforderung_wert": "900x2100",
                    "katalog_wert": "900x2000",
                    "abweichung_beschreibung": "Hoehe weicht ab",
                },
            ],
            zusammenfassung="Mehrere Luecken",
        )

        mr = _make_match_result()
        ar = _make_adversarial_result(
            status=ValidationStatus.UNSICHER,
            cot_scores={
                "Masse": 0.8, "Brandschutz": 0.5, "Schallschutz": 0.6,
                "Material": 0.9, "Zertifizierung": 0.9, "Leistung": 0.9,
            },
        )

        semaphore = asyncio.Semaphore(3)
        result = asyncio.get_event_loop().run_until_complete(
            analyze_single_position_gaps(
                client=mock_client,
                match_result=mr,
                adversarial_result=ar,
                tfidf_index=None,
                semaphore=semaphore,
            )
        )

        assert len(result.gaps) == 3
        assert result.validation_status == "unsicher"

    def test_abgelehnt_produces_empty_gaps_with_summary(self):
        """Abgelehnt produces empty gaps with text summary."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Kein passendes Produkt gefunden.")]
        mock_client.messages.create.return_value = mock_response

        mr = _make_match_result(has_match=False)
        ar = _make_adversarial_result(
            status=ValidationStatus.ABGELEHNT,
            cot_scores={},
        )

        semaphore = asyncio.Semaphore(3)
        result = asyncio.get_event_loop().run_until_complete(
            analyze_single_position_gaps(
                client=mock_client,
                match_result=mr,
                adversarial_result=ar,
                tfidf_index=None,
                semaphore=semaphore,
            )
        )

        assert len(result.gaps) == 0
        assert result.zusammenfassung
        assert result.validation_status == "abgelehnt"

    def test_safety_escalation_applied(self):
        """Mock returns Brandschutz as MINOR -> verify upgraded to MAJOR."""
        mock_client = MagicMock()
        mock_client.messages.parse.return_value = _make_mock_opus_response(
            gaps_data=[
                {
                    "dimension": "Brandschutz",
                    "schweregrad": "minor",  # Should be escalated
                    "anforderung_wert": "EI60",
                    "katalog_wert": "EI30",
                    "abweichung_beschreibung": "Brandschutz zu niedrig",
                },
            ],
        )

        mr = _make_match_result()
        ar = _make_adversarial_result(
            status=ValidationStatus.UNSICHER,
            cot_scores={
                "Masse": 1.0, "Brandschutz": 0.5, "Schallschutz": 1.0,
                "Material": 1.0, "Zertifizierung": 1.0, "Leistung": 1.0,
            },
        )

        semaphore = asyncio.Semaphore(3)
        result = asyncio.get_event_loop().run_until_complete(
            analyze_single_position_gaps(
                client=mock_client,
                match_result=mr,
                adversarial_result=ar,
                tfidf_index=None,
                semaphore=semaphore,
            )
        )

        assert result.gaps[0].schweregrad == GapSeverity.MAJOR


class TestAlternativeSearch:
    """Test search_alternatives_for_gaps with mocked tfidf_index."""

    def test_matched_product_filtered_out(self):
        """The matched product should not appear in alternatives."""
        from v2.schemas.extraction import ExtractedDoorPosition
        mock_index = _make_mock_tfidf_index()
        position = ExtractedDoorPosition(
            positions_nr="1.01",
            breite_mm=900,
            hoehe_mm=2100,
        )
        gaps = [
            GapItem(
                dimension=GapDimension.BRANDSCHUTZ,
                schweregrad=GapSeverity.MAJOR,
                anforderung_wert="EI60",
                abweichung_beschreibung="Zu niedrig",
            ),
        ]

        results = search_alternatives_for_gaps(
            position, gaps, mock_index,
            matched_product_id="PROD-100",
        )

        alt_ids = [a.produkt_id for a in results]
        assert "PROD-100" not in alt_ids

    def test_max_three_alternatives(self):
        """At most 3 alternatives should be returned."""
        from v2.schemas.extraction import ExtractedDoorPosition
        mock_index = _make_mock_tfidf_index()
        position = ExtractedDoorPosition(
            positions_nr="1.01",
            breite_mm=900,
            hoehe_mm=2100,
        )
        gaps = [
            GapItem(
                dimension=GapDimension.BRANDSCHUTZ,
                schweregrad=GapSeverity.MAJOR,
                anforderung_wert="EI60",
                abweichung_beschreibung="Zu niedrig",
            ),
        ]

        results = search_alternatives_for_gaps(
            position, gaps, mock_index,
            matched_product_id="PROD-100",
        )

        assert len(results) <= 3

    def test_abgelehnt_filter_coverage(self):
        """Abgelehnt alternatives must have >30% coverage."""
        from v2.schemas.extraction import ExtractedDoorPosition
        # Build index where most candidates won't have matching fields
        mock_index = _make_mock_tfidf_index(
            candidate_fields={
                0: {"Kostentraeger": "PROD-300", "Produktegruppen": "Leer", "row_index": 0},
                1: {"Kostentraeger": "PROD-301", "Produktegruppen": "Leer", "row_index": 1},
                2: {"Kostentraeger": "PROD-302", "Produktegruppen": "Brandschutztuere", "Brandschutzklasse": "EI60", "row_index": 2},
            },
            search_results=[(0, 0.9), (1, 0.8), (2, 0.7)],
        )
        position = ExtractedDoorPosition(
            positions_nr="1.01",
            breite_mm=900,
            hoehe_mm=2100,
        )
        gaps = [
            GapItem(
                dimension=GapDimension.BRANDSCHUTZ,
                schweregrad=GapSeverity.MAJOR,
                anforderung_wert="EI60",
                abweichung_beschreibung="Kein Brandschutz",
            ),
            GapItem(
                dimension=GapDimension.SCHALLSCHUTZ,
                schweregrad=GapSeverity.MAJOR,
                anforderung_wert="42dB",
                abweichung_beschreibung="Kein Schallschutz",
            ),
        ]

        results = search_alternatives_for_gaps(
            position, gaps, mock_index,
            matched_product_id=None,
            is_abgelehnt=True,
        )

        # Only candidates with >30% coverage should be returned
        for alt in results:
            assert alt.teilweise_deckung >= 0.3

    def test_cross_references_set_correctly(self):
        """gap_geschlossen_durch should contain valid product IDs."""
        gaps = [
            GapItem(
                dimension=GapDimension.BRANDSCHUTZ,
                schweregrad=GapSeverity.MAJOR,
                anforderung_wert="EI60",
                abweichung_beschreibung="Zu niedrig",
            ),
            GapItem(
                dimension=GapDimension.SCHALLSCHUTZ,
                schweregrad=GapSeverity.MAJOR,
                anforderung_wert="42dB",
                abweichung_beschreibung="Unzureichend",
            ),
        ]
        alternatives = [
            AlternativeProduct(
                produkt_id="PROD-201",
                produkt_name="EI60 Tuere",
                teilweise_deckung=0.5,
                verbleibende_gaps=["Schallschutz"],
                geschlossene_gaps=["Brandschutz"],
            ),
            AlternativeProduct(
                produkt_id="PROD-202",
                produkt_name="Schallschutztuere",
                teilweise_deckung=0.5,
                verbleibende_gaps=["Brandschutz"],
                geschlossene_gaps=["Schallschutz"],
            ),
        ]

        _cross_reference_gaps_and_alternatives(gaps, alternatives)

        # Brandschutz gap should reference PROD-201
        assert "PROD-201" in gaps[0].gap_geschlossen_durch
        assert "PROD-202" not in gaps[0].gap_geschlossen_durch

        # Schallschutz gap should reference PROD-202
        assert "PROD-202" in gaps[1].gap_geschlossen_durch
        assert "PROD-201" not in gaps[1].gap_geschlossen_durch
