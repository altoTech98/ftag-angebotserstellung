"""
Tests for Phase 3: Cross-Document Intelligence.

Tests cover schemas, cross-doc matcher, enrichment engine, and conflict detector.
"""

import pytest

from v2.schemas.common import FieldSource
from v2.schemas.extraction import (
    ConflictSeverity,
    CrossDocMatch,
    DocumentEnrichmentStats,
    EnrichmentReport,
    ExtractedDoorPosition,
    ExtractionResult,
    FieldConflict,
    GeneralSpec,
)


# ---------------------------------------------------------------------------
# Schema Tests
# ---------------------------------------------------------------------------


class TestSchemas:
    """Test Phase 3 schema extensions and new models."""

    def test_field_source_enrichment_fields(self):
        """FieldSource has enrichment_source and enrichment_type fields."""
        fs = FieldSource(dokument="test.xlsx", konfidenz=0.9)
        assert fs.enrichment_source is None
        assert fs.enrichment_type is None

        fs2 = FieldSource(
            dokument="spec.pdf",
            konfidenz=0.8,
            enrichment_source="tuerliste.xlsx",
            enrichment_type="gap_fill",
        )
        assert fs2.enrichment_source == "tuerliste.xlsx"
        assert fs2.enrichment_type == "gap_fill"

    def test_field_source_backward_compat(self):
        """Existing FieldSource usage still works without new fields."""
        fs = FieldSource(
            dokument="old.xlsx",
            seite=1,
            zeile=5,
            zelle="B5",
            sheet="Sheet1",
            konfidenz=0.95,
        )
        assert fs.dokument == "old.xlsx"
        assert fs.konfidenz == 0.95
        # New fields default to None
        assert fs.enrichment_source is None
        assert fs.enrichment_type is None

    def test_conflict_severity_enum(self):
        """ConflictSeverity has CRITICAL, MAJOR, MINOR values."""
        assert ConflictSeverity.CRITICAL == "critical"
        assert ConflictSeverity.MAJOR == "major"
        assert ConflictSeverity.MINOR == "minor"
        assert len(ConflictSeverity) == 3

    def test_field_conflict_model(self):
        """FieldConflict stores both values with severity and resolution."""
        conflict = FieldConflict(
            positions_nr="1.01",
            field_name="brandschutz_klasse",
            wert_a="T30",
            quelle_a=FieldSource(dokument="tuerliste.xlsx", konfidenz=0.9),
            wert_b="T90",
            quelle_b=FieldSource(dokument="spec.pdf", konfidenz=0.95),
            severity=ConflictSeverity.CRITICAL,
            resolution="T90",
            resolution_reason="PDF-Spezifikation hat hoehere Prioritaet",
            resolved_by="ai",
        )
        assert conflict.positions_nr == "1.01"
        assert conflict.severity == ConflictSeverity.CRITICAL
        assert conflict.resolution == "T90"
        assert conflict.resolved_by == "ai"

    def test_crossdoc_match_model(self):
        """CrossDocMatch stores match details with confidence and method."""
        match = CrossDocMatch(
            position_a_index=0,
            position_b_index=1,
            confidence=0.92,
            match_method="normalized_id",
            auto_merge=True,
        )
        assert match.confidence == 0.92
        assert match.match_method == "normalized_id"
        assert match.auto_merge is True

    def test_general_spec_model(self):
        """GeneralSpec has beschreibung, scope, affected_fields, source, konfidenz."""
        spec = GeneralSpec(
            beschreibung="Alle Innenturen im OG muessen T30 Brandschutz aufweisen",
            scope="geschoss==OG",
            affected_fields={"brandschutz_klasse": "T30"},
            source=FieldSource(dokument="pflichtenheft.docx", seite=5, konfidenz=0.8),
            konfidenz=0.7,
        )
        assert spec.beschreibung.startswith("Alle")
        assert spec.konfidenz == 0.7
        assert "brandschutz_klasse" in spec.affected_fields

    def test_general_spec_default_konfidenz(self):
        """GeneralSpec defaults konfidenz to 0.7."""
        spec = GeneralSpec(
            beschreibung="Test",
            scope="all",
            affected_fields={},
            source=FieldSource(dokument="test.pdf", konfidenz=0.8),
        )
        assert spec.konfidenz == 0.7

    def test_enrichment_report_model(self):
        """EnrichmentReport has all required statistics fields."""
        report = EnrichmentReport(
            total_positionen=10,
            positionen_matched_cross_doc=6,
            felder_enriched=45,
            konflikte_total=3,
            konflikte_critical=1,
            konflikte_major=1,
            konflikte_minor=1,
            general_specs_applied=2,
            dokument_stats=[
                DocumentEnrichmentStats(
                    dokument="tuerliste.xlsx",
                    positionen_matched=4,
                    felder_enriched=20,
                    konflikte_gefunden=2,
                ),
            ],
            zusammenfassung="PDF-Spezifikation hat 45 Felder ergaenzt.",
        )
        assert report.total_positionen == 10
        assert report.konflikte_critical == 1
        assert len(report.dokument_stats) == 1
        assert report.dokument_stats[0].dokument == "tuerliste.xlsx"

    def test_extraction_result_backward_compat(self):
        """ExtractionResult works without new fields (backward compat)."""
        from v2.schemas.common import DokumentTyp

        result = ExtractionResult(
            positionen=[],
            dokument_zusammenfassung="Test",
            warnungen=[],
            dokument_typ=DokumentTyp.PDF,
        )
        assert result.enrichment_report is None
        assert result.conflicts == []

    def test_extraction_result_with_crossdoc_fields(self):
        """ExtractionResult accepts enrichment_report and conflicts."""
        from v2.schemas.common import DokumentTyp

        report = EnrichmentReport(
            total_positionen=5,
            positionen_matched_cross_doc=3,
            felder_enriched=10,
            konflikte_total=1,
            konflikte_critical=0,
            konflikte_major=1,
            konflikte_minor=0,
            general_specs_applied=0,
            dokument_stats=[],
            zusammenfassung="Test",
        )
        conflict = FieldConflict(
            positions_nr="1.01",
            field_name="breite_mm",
            wert_a="1000",
            quelle_a=FieldSource(dokument="a.xlsx", konfidenz=0.9),
            wert_b="900",
            quelle_b=FieldSource(dokument="b.pdf", konfidenz=0.95),
            severity=ConflictSeverity.MAJOR,
            resolution="900",
            resolution_reason="PDF spec wins",
            resolved_by="ai",
        )
        result = ExtractionResult(
            positionen=[],
            dokument_zusammenfassung="Test",
            warnungen=[],
            dokument_typ=DokumentTyp.PDF,
            enrichment_report=report,
            conflicts=[conflict],
        )
        assert result.enrichment_report is not None
        assert len(result.conflicts) == 1


# ---------------------------------------------------------------------------
# Prompt Template Tests
# ---------------------------------------------------------------------------


class TestPromptTemplates:
    """Test that cross-doc prompt templates exist and are non-empty."""

    def test_crossdoc_matching_prompts_exist(self):
        from v2.extraction.prompts import (
            CROSSDOC_MATCHING_SYSTEM_PROMPT,
            CROSSDOC_MATCHING_USER_TEMPLATE,
        )
        assert len(CROSSDOC_MATCHING_SYSTEM_PROMPT) > 100
        assert "{" in CROSSDOC_MATCHING_USER_TEMPLATE  # has format placeholders

    def test_crossdoc_conflict_prompts_exist(self):
        from v2.extraction.prompts import (
            CROSSDOC_CONFLICT_SYSTEM_PROMPT,
            CROSSDOC_CONFLICT_USER_TEMPLATE,
        )
        assert len(CROSSDOC_CONFLICT_SYSTEM_PROMPT) > 100
        assert "{" in CROSSDOC_CONFLICT_USER_TEMPLATE

    def test_crossdoc_enrichment_prompts_exist(self):
        from v2.extraction.prompts import (
            CROSSDOC_ENRICHMENT_SYSTEM_PROMPT,
            CROSSDOC_ENRICHMENT_USER_TEMPLATE,
        )
        assert len(CROSSDOC_ENRICHMENT_SYSTEM_PROMPT) > 100
        assert "{" in CROSSDOC_ENRICHMENT_USER_TEMPLATE


# ---------------------------------------------------------------------------
# Cross-Doc Matcher Tests (stubs for Task 2)
# ---------------------------------------------------------------------------


class TestCrossDocMatcher:
    """Tests for cross-document position matcher."""

    def test_exact_id_match(self):
        """Positions with same positions_nr match with confidence 1.0."""
        from v2.extraction.cross_doc_matcher import match_positions_across_docs

        pos_a = [ExtractedDoorPosition(positions_nr="1.01", breite_mm=1000)]
        pos_b = [ExtractedDoorPosition(positions_nr="1.01", hoehe_mm=2100)]
        matches = match_positions_across_docs({
            "tuerliste.xlsx": pos_a,
            "spec.pdf": pos_b,
        })
        exact_matches = [m for m in matches if m.match_method == "exact_id"]
        assert len(exact_matches) == 1
        assert exact_matches[0].confidence == 1.0
        assert exact_matches[0].auto_merge is True

    def test_normalized_id_match(self, xlsx_positions, pdf_positions):
        """'Tuer 1.02' from PDF matches '1.02' from XLSX via normalization."""
        from v2.extraction.cross_doc_matcher import match_positions_across_docs

        matches = match_positions_across_docs({
            "tuerliste.xlsx": xlsx_positions,
            "spec.pdf": pdf_positions,
        })
        normalized_matches = [m for m in matches if m.match_method == "normalized_id"]
        assert len(normalized_matches) >= 1
        assert all(m.confidence >= 0.9 for m in normalized_matches)
        assert all(m.auto_merge is True for m in normalized_matches)

    def test_room_floor_type_match(self):
        """Same room+floor+type matches with lower confidence."""
        from v2.extraction.cross_doc_matcher import match_positions_across_docs
        from v2.schemas.common import BrandschutzKlasse

        pos_a = [ExtractedDoorPosition(
            positions_nr="A.01",
            raum_nr="B101",
            geschoss="EG",
            oeffnungsart=None,
        )]
        pos_b = [ExtractedDoorPosition(
            positions_nr="X.99",
            raum_nr="B101",
            geschoss="EG",
            oeffnungsart=None,
        )]
        matches = match_positions_across_docs({
            "doc_a.xlsx": pos_a,
            "doc_b.pdf": pos_b,
        })
        room_matches = [m for m in matches if m.match_method == "room_floor_type"]
        assert len(room_matches) >= 1
        assert all(0.6 <= m.confidence <= 0.9 for m in room_matches)
        assert all(m.auto_merge is False for m in room_matches)

    def test_no_match(self):
        """Different positions with nothing in common -> no match."""
        from v2.extraction.cross_doc_matcher import match_positions_across_docs

        pos_a = [ExtractedDoorPosition(
            positions_nr="1.01", raum_nr="A100", geschoss="EG",
        )]
        pos_b = [ExtractedDoorPosition(
            positions_nr="9.99", raum_nr="Z999", geschoss="OG3",
        )]
        matches = match_positions_across_docs({
            "a.xlsx": pos_a,
            "b.pdf": pos_b,
        })
        assert len(matches) == 0

    def test_normalize_position_id(self):
        """Various Swiss ID formats normalize to the same value."""
        from v2.extraction.cross_doc_matcher import _normalize_position_id

        assert _normalize_position_id("1.01") == _normalize_position_id("Tuer 1.01")
        assert _normalize_position_id("1.01") == _normalize_position_id("Pos. 1.01")
        assert _normalize_position_id("1.01") == _normalize_position_id("Element 1.01")
        assert _normalize_position_id("1.01") == _normalize_position_id("T-1.01")
        assert _normalize_position_id("1.01") == _normalize_position_id("Nr. 1.01")
        assert _normalize_position_id("1.01") != _normalize_position_id("2.01")


# ---------------------------------------------------------------------------
# Enrichment Tests (stubs for Task 2)
# ---------------------------------------------------------------------------


class TestEnrichment:
    """Tests for cross-document enrichment engine."""

    def test_gap_fill(self, xlsx_positions, pdf_positions):
        """Empty field filled from other doc with enrichment_source."""
        from v2.extraction.cross_doc_matcher import match_positions_across_docs
        from v2.extraction.enrichment import enrich_positions

        matches = match_positions_across_docs({
            "tuerliste.xlsx": xlsx_positions,
            "spec.pdf": pdf_positions,
        })
        all_positions = xlsx_positions + pdf_positions
        enriched, report = enrich_positions(matches, all_positions)

        # Find position 1.01 - xlsx has no brandschutz, pdf does
        pos_101 = [p for p in enriched if _normalize_nr(p.positions_nr) == "1.01"][0]
        # The gap should be filled
        assert pos_101.brandschutz_klasse is not None

    def test_confidence_upgrade(self):
        """Low-konfidenz field upgraded from higher-konfidenz source."""
        from v2.extraction.cross_doc_matcher import match_positions_across_docs
        from v2.extraction.enrichment import enrich_positions

        pos_a = [ExtractedDoorPosition(
            positions_nr="1.01",
            breite_mm=1000,
            quellen={"breite_mm": FieldSource(dokument="a.xlsx", konfidenz=0.5)},
        )]
        pos_b = [ExtractedDoorPosition(
            positions_nr="1.01",
            breite_mm=1000,
            quellen={"breite_mm": FieldSource(dokument="b.pdf", konfidenz=0.95)},
        )]
        matches = match_positions_across_docs({"a.xlsx": pos_a, "b.pdf": pos_b})
        enriched, report = enrich_positions(matches, pos_a + pos_b)

        pos = enriched[0]
        # Confidence should have been upgraded
        assert pos.quellen["breite_mm"].konfidenz >= 0.7

    def test_no_downgrade(self):
        """High-konfidenz field NOT overwritten by lower konfidenz."""
        from v2.extraction.cross_doc_matcher import match_positions_across_docs
        from v2.extraction.enrichment import enrich_positions

        pos_a = [ExtractedDoorPosition(
            positions_nr="1.01",
            breite_mm=1000,
            quellen={"breite_mm": FieldSource(dokument="a.xlsx", konfidenz=0.95)},
        )]
        pos_b = [ExtractedDoorPosition(
            positions_nr="1.01",
            breite_mm=900,
            quellen={"breite_mm": FieldSource(dokument="b.pdf", konfidenz=0.5)},
        )]
        matches = match_positions_across_docs({"a.xlsx": pos_a, "b.pdf": pos_b})
        enriched, report = enrich_positions(matches, pos_a + pos_b)

        pos = enriched[0]
        assert pos.breite_mm == 1000  # Original high-confidence value preserved
        assert pos.quellen["breite_mm"].konfidenz == 0.95

    def test_general_spec_application(self, xlsx_positions):
        """General spec fills empty fields with konfidenz=0.7."""
        from v2.extraction.enrichment import enrich_positions
        from v2.schemas.common import BrandschutzKlasse

        spec = GeneralSpec(
            beschreibung="Alle Innenturen im OG muessen T30 aufweisen",
            scope="geschoss==OG",
            affected_fields={"brandschutz_klasse": "T30"},
            source=FieldSource(dokument="pflichtenheft.docx", konfidenz=0.8),
        )
        # Give one position geschoss=OG and no brandschutz
        positions = [
            ExtractedDoorPosition(positions_nr="2.01", geschoss="OG"),
        ]
        enriched, report = enrich_positions([], positions, general_specs=[spec])

        pos = enriched[0]
        assert pos.brandschutz_klasse == BrandschutzKlasse.T30
        assert report.general_specs_applied >= 1

    def test_general_spec_no_override(self, xlsx_positions):
        """General spec does NOT override existing specific value."""
        from v2.extraction.enrichment import enrich_positions
        from v2.schemas.common import BrandschutzKlasse

        spec = GeneralSpec(
            beschreibung="Alle Tueren T30",
            scope="all",
            affected_fields={"brandschutz_klasse": "T30"},
            source=FieldSource(dokument="pflichtenheft.docx", konfidenz=0.8),
        )
        positions = [
            ExtractedDoorPosition(
                positions_nr="1.01",
                brandschutz_klasse=BrandschutzKlasse.EI90,
            ),
        ]
        enriched, report = enrich_positions([], positions, general_specs=[spec])

        pos = enriched[0]
        assert pos.brandschutz_klasse == BrandschutzKlasse.EI90  # NOT overridden

    def test_enrichment_provenance(self, xlsx_positions, pdf_positions):
        """Enriched fields have enrichment_source and enrichment_type set."""
        from v2.extraction.cross_doc_matcher import match_positions_across_docs
        from v2.extraction.enrichment import enrich_positions

        matches = match_positions_across_docs({
            "tuerliste.xlsx": xlsx_positions,
            "spec.pdf": pdf_positions,
        })
        all_positions = xlsx_positions + pdf_positions
        enriched, report = enrich_positions(matches, all_positions)

        # Check that at least one enriched field has provenance
        found_enrichment = False
        for pos in enriched:
            for field_name, source in pos.quellen.items():
                if source.enrichment_source is not None:
                    found_enrichment = True
                    assert source.enrichment_type in (
                        "gap_fill", "confidence_upgrade", "general_spec", "conflict_resolution"
                    )
        assert found_enrichment, "Expected at least one enriched field with provenance"

    def test_enrichment_report_stats(self, xlsx_positions, pdf_positions):
        """EnrichmentReport counts are accurate."""
        from v2.extraction.cross_doc_matcher import match_positions_across_docs
        from v2.extraction.enrichment import enrich_positions

        matches = match_positions_across_docs({
            "tuerliste.xlsx": xlsx_positions,
            "spec.pdf": pdf_positions,
        })
        all_positions = xlsx_positions + pdf_positions
        enriched, report = enrich_positions(matches, all_positions)

        assert report.total_positionen == len(all_positions)
        assert report.positionen_matched_cross_doc >= 1
        assert report.felder_enriched >= 0
        assert isinstance(report.zusammenfassung, str)
        assert len(report.zusammenfassung) > 0


# ---------------------------------------------------------------------------
# Conflict Detector Tests (stubs for Task 2)
# ---------------------------------------------------------------------------


class TestConflictDetector:
    """Tests for cross-document conflict detection."""

    def test_exact_conflict(self, conflicting_positions):
        """Different values for same field -> FieldConflict created."""
        from v2.extraction.cross_doc_matcher import match_positions_across_docs
        from v2.extraction.conflict_detector import detect_and_resolve_conflicts
        from unittest.mock import AsyncMock, patch

        matches = match_positions_across_docs({
            "a.xlsx": [conflicting_positions[0]],
            "b.pdf": [conflicting_positions[1]],
        })

        # Mock AI resolution
        mock_resolution = [FieldConflict(
            positions_nr="1.01",
            field_name="brandschutz_klasse",
            wert_a="T30",
            quelle_a=FieldSource(dokument="a.xlsx", konfidenz=0.9),
            wert_b="T90",
            quelle_b=FieldSource(dokument="b.pdf", konfidenz=0.95),
            severity=ConflictSeverity.CRITICAL,
            resolution="T90",
            resolution_reason="PDF spec has higher priority",
            resolved_by="ai",
        )]

        with patch("v2.extraction.conflict_detector._resolve_conflicts_with_ai",
                    return_value=mock_resolution):
            conflicts = detect_and_resolve_conflicts(
                matches, conflicting_positions, client=None
            )

        assert len(conflicts) >= 1
        fire_conflicts = [c for c in conflicts if c.field_name == "brandschutz_klasse"]
        assert len(fire_conflicts) == 1

    def test_severity_classification(self):
        """Fire rating = CRITICAL, dimensions = MAJOR, color = MINOR."""
        from v2.extraction.cross_doc_matcher import _classify_severity

        assert _classify_severity("brandschutz_klasse") == ConflictSeverity.CRITICAL
        assert _classify_severity("rauchschutz") == ConflictSeverity.CRITICAL
        assert _classify_severity("einbruchschutz_klasse") == ConflictSeverity.CRITICAL
        assert _classify_severity("breite_mm") == ConflictSeverity.MAJOR
        assert _classify_severity("hoehe_mm") == ConflictSeverity.MAJOR
        assert _classify_severity("material_blatt") == ConflictSeverity.MAJOR
        assert _classify_severity("farbe_ral") == ConflictSeverity.MINOR
        assert _classify_severity("oberflaeche") == ConflictSeverity.MINOR

    def test_no_conflict_when_same_value(self):
        """Identical values -> no conflict."""
        from v2.extraction.cross_doc_matcher import match_positions_across_docs
        from v2.extraction.conflict_detector import detect_and_resolve_conflicts
        from v2.schemas.common import BrandschutzKlasse
        from unittest.mock import patch

        pos_a = [ExtractedDoorPosition(
            positions_nr="1.01",
            brandschutz_klasse=BrandschutzKlasse.T30,
            quellen={"brandschutz_klasse": FieldSource(dokument="a.xlsx", konfidenz=0.9)},
        )]
        pos_b = [ExtractedDoorPosition(
            positions_nr="1.01",
            brandschutz_klasse=BrandschutzKlasse.T30,
            quellen={"brandschutz_klasse": FieldSource(dokument="b.pdf", konfidenz=0.95)},
        )]
        matches = match_positions_across_docs({"a.xlsx": pos_a, "b.pdf": pos_b})

        with patch("v2.extraction.conflict_detector._resolve_conflicts_with_ai",
                    return_value=[]):
            conflicts = detect_and_resolve_conflicts(
                matches, pos_a + pos_b, client=None
            )

        # Same value in both docs -> no conflict
        fire_conflicts = [c for c in conflicts if c.field_name == "brandschutz_klasse"]
        assert len(fire_conflicts) == 0

    def test_no_conflict_when_one_none(self):
        """None vs value -> enrichment opportunity, not conflict."""
        from v2.extraction.cross_doc_matcher import match_positions_across_docs
        from v2.extraction.conflict_detector import detect_and_resolve_conflicts
        from v2.schemas.common import BrandschutzKlasse
        from unittest.mock import patch

        pos_a = [ExtractedDoorPosition(
            positions_nr="1.01",
            brandschutz_klasse=None,
        )]
        pos_b = [ExtractedDoorPosition(
            positions_nr="1.01",
            brandschutz_klasse=BrandschutzKlasse.T30,
            quellen={"brandschutz_klasse": FieldSource(dokument="b.pdf", konfidenz=0.95)},
        )]
        matches = match_positions_across_docs({"a.xlsx": pos_a, "b.pdf": pos_b})

        with patch("v2.extraction.conflict_detector._resolve_conflicts_with_ai",
                    return_value=[]):
            conflicts = detect_and_resolve_conflicts(
                matches, pos_a + pos_b, client=None
            )

        # None vs value is not a conflict, it's an enrichment opportunity
        assert len(conflicts) == 0


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _normalize_nr(nr: str) -> str:
    """Minimal normalizer for test assertions."""
    import re
    nr = re.sub(r"^(Tuer|Pos\.|Element|T-|Nr\.)\s*", "", nr.strip())
    return nr.strip()


# ---------------------------------------------------------------------------
# AI Conflict Resolution Tests (Plan 03-03)
# ---------------------------------------------------------------------------


class TestAIConflictResolution:
    """Tests for AI-powered conflict resolution in conflict_detector."""

    @pytest.mark.asyncio
    async def test_ai_resolution_called_when_client_provided(self):
        """When client is provided and AI call succeeds, resolved_by is 'ai'."""
        from unittest.mock import MagicMock, patch
        from v2.extraction.conflict_detector import (
            ConflictResolutionItem,
            ConflictResolutionResult,
            _resolve_conflicts_with_ai,
        )

        # Build a mock client whose messages.parse returns structured result
        mock_client = MagicMock()
        ai_response = ConflictResolutionResult(
            resolutions=[
                ConflictResolutionItem(
                    field_name="brandschutz_klasse",
                    resolution="T90",
                    resolution_reason="PDF-Spezifikation hat hoehere Prioritaet fuer Brandschutz",
                ),
            ]
        )
        # messages.parse is called via asyncio.to_thread, so it's sync on the mock
        mock_client.messages.parse.return_value = ai_response

        raw_conflicts = [
            {
                "positions_nr": "1.01",
                "field_name": "brandschutz_klasse",
                "wert_a": "T30",
                "quelle_a": FieldSource(dokument="a.xlsx", konfidenz=0.9),
                "wert_b": "T90",
                "quelle_b": FieldSource(dokument="b.pdf", konfidenz=0.95),
                "severity": ConflictSeverity.CRITICAL,
            },
        ]

        resolved = await _resolve_conflicts_with_ai(raw_conflicts, mock_client)
        assert len(resolved) == 1
        assert resolved[0].resolved_by == "ai"
        assert resolved[0].resolution == "T90"
        assert "Prioritaet" in resolved[0].resolution_reason
        mock_client.messages.parse.assert_called_once()

    @pytest.mark.asyncio
    async def test_rule_fallback_when_no_client(self):
        """When client is None, falls back to rule-based resolution with resolved_by='rule'."""
        from v2.extraction.conflict_detector import _resolve_conflicts_with_ai

        raw_conflicts = [
            {
                "positions_nr": "1.01",
                "field_name": "brandschutz_klasse",
                "wert_a": "T30",
                "quelle_a": FieldSource(dokument="a.xlsx", konfidenz=0.9),
                "wert_b": "T90",
                "quelle_b": FieldSource(dokument="b.pdf", konfidenz=0.95),
                "severity": ConflictSeverity.CRITICAL,
            },
        ]

        resolved = await _resolve_conflicts_with_ai(raw_conflicts, None)
        assert len(resolved) == 1
        assert resolved[0].resolved_by == "rule"

    @pytest.mark.asyncio
    async def test_rule_fallback_on_ai_failure(self):
        """When AI call raises exception 3 times, falls back to rule-based with warning."""
        import logging
        from unittest.mock import MagicMock, patch
        from v2.extraction.conflict_detector import _resolve_conflicts_with_ai

        mock_client = MagicMock()
        mock_client.messages.parse.side_effect = Exception("API error")

        raw_conflicts = [
            {
                "positions_nr": "1.01",
                "field_name": "brandschutz_klasse",
                "wert_a": "T30",
                "quelle_a": FieldSource(dokument="a.xlsx", konfidenz=0.9),
                "wert_b": "T90",
                "quelle_b": FieldSource(dokument="b.pdf", konfidenz=0.95),
                "severity": ConflictSeverity.CRITICAL,
            },
        ]

        # Patch asyncio.sleep to avoid actual delays in tests
        with patch("v2.extraction.conflict_detector.asyncio.sleep"):
            resolved = await _resolve_conflicts_with_ai(raw_conflicts, mock_client)

        assert len(resolved) == 1
        assert resolved[0].resolved_by == "rule"
        assert mock_client.messages.parse.call_count == 3

    @pytest.mark.asyncio
    async def test_ai_receives_formatted_prompt(self):
        """AI receives conflict data formatted via CROSSDOC_CONFLICT_USER_TEMPLATE."""
        from unittest.mock import MagicMock, patch, call
        from v2.extraction.conflict_detector import (
            ConflictResolutionItem,
            ConflictResolutionResult,
            _resolve_conflicts_with_ai,
        )
        from v2.extraction.prompts import (
            CROSSDOC_CONFLICT_SYSTEM_PROMPT,
        )

        mock_client = MagicMock()
        ai_response = ConflictResolutionResult(
            resolutions=[
                ConflictResolutionItem(
                    field_name="breite_mm",
                    resolution="1000",
                    resolution_reason="XLSX hat praezisere Massdaten",
                ),
            ]
        )
        mock_client.messages.parse.return_value = ai_response

        raw_conflicts = [
            {
                "positions_nr": "1.01",
                "field_name": "breite_mm",
                "wert_a": "1000",
                "quelle_a": FieldSource(dokument="a.xlsx", konfidenz=0.95),
                "wert_b": "900",
                "quelle_b": FieldSource(dokument="b.pdf", konfidenz=0.9),
                "severity": ConflictSeverity.MAJOR,
            },
        ]

        resolved = await _resolve_conflicts_with_ai(raw_conflicts, mock_client)

        # Verify the call used proper system prompt and formatted user message
        call_kwargs = mock_client.messages.parse.call_args
        assert call_kwargs.kwargs["system"] == CROSSDOC_CONFLICT_SYSTEM_PROMPT
        # User message should contain conflicts JSON
        user_msg = call_kwargs.kwargs["messages"][0]["content"]
        assert "breite_mm" in user_msg
        assert "1000" in user_msg

    @pytest.mark.asyncio
    async def test_detect_and_resolve_conflicts_is_async(self, conflicting_positions):
        """detect_and_resolve_conflicts is async and can be awaited."""
        from v2.extraction.cross_doc_matcher import match_positions_across_docs
        from v2.extraction.conflict_detector import detect_and_resolve_conflicts

        matches = match_positions_across_docs({
            "a.xlsx": [conflicting_positions[0]],
            "b.pdf": [conflicting_positions[1]],
        })

        # Should be awaitable (async function)
        conflicts = await detect_and_resolve_conflicts(
            matches, conflicting_positions, client=None
        )
        assert len(conflicts) >= 1
        # Without client, should be rule-based
        assert all(c.resolved_by == "rule" for c in conflicts)


# ---------------------------------------------------------------------------
# Pipeline Integration Tests (Plan 03-02)
# ---------------------------------------------------------------------------


class TestPipelineIntegration:
    """Integration tests for cross-doc intelligence in the pipeline."""

    def test_api_response_extended(self):
        """Verify response JSON includes enrichment_report and conflicts keys."""
        import uuid
        from datetime import datetime, timezone
        from unittest.mock import patch
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from v2.parsers.base import ParseResult
        from v2.routers.upload_v2 import router as upload_router, _tenders
        from v2.routers.analyze_v2 import router as analyze_router
        from v2.schemas.common import DokumentTyp

        app = FastAPI()
        app.include_router(upload_router)
        app.include_router(analyze_router)
        test_client = TestClient(app)

        tender_id = str(uuid.uuid4())
        pr = ParseResult(
            text="tuer_nr: 1.01",
            format="xlsx",
            page_count=1,
            warnings=[],
            metadata={},
            source_file="test.xlsx",
            tables=[],
        )
        _tenders[tender_id] = {
            "files": [pr],
            "status": "uploading",
            "created_at": datetime.now(timezone.utc),
        }

        report = EnrichmentReport(
            total_positionen=2,
            positionen_matched_cross_doc=1,
            felder_enriched=3,
            konflikte_total=0,
            konflikte_critical=0,
            konflikte_major=0,
            konflikte_minor=0,
            general_specs_applied=0,
            dokument_stats=[],
            zusammenfassung="Test",
        )
        mock_result = ExtractionResult(
            positionen=[ExtractedDoorPosition(positions_nr="1.01", quellen={})],
            dokument_zusammenfassung="Test",
            warnungen=[],
            dokument_typ=DokumentTyp.XLSX,
            enrichment_report=report,
            conflicts=[],
        )

        async def mock_pipeline(*args, **kwargs):
            return mock_result

        with patch("v2.routers.analyze_v2.run_extraction_pipeline", side_effect=mock_pipeline):
            resp = test_client.post(
                "/api/v2/analyze",
                json={"tender_id": tender_id},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "enrichment_report" in data
        assert "conflicts" in data
        assert "total_conflicts" in data
        assert data["enrichment_report"] is not None
        assert data["enrichment_report"]["felder_enriched"] == 3

        _tenders.clear()

    def test_backward_compat_single_file(self):
        """Single-file response has enrichment_report=null, conflicts=[]."""
        import uuid
        from datetime import datetime, timezone
        from unittest.mock import patch
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from v2.parsers.base import ParseResult
        from v2.routers.upload_v2 import router as upload_router, _tenders
        from v2.routers.analyze_v2 import router as analyze_router
        from v2.schemas.common import DokumentTyp

        app = FastAPI()
        app.include_router(upload_router)
        app.include_router(analyze_router)
        test_client = TestClient(app)

        tender_id = str(uuid.uuid4())
        pr = ParseResult(
            text="tuer_nr: 1.01",
            format="xlsx",
            page_count=1,
            warnings=[],
            metadata={},
            source_file="test.xlsx",
            tables=[],
        )
        _tenders[tender_id] = {
            "files": [pr],
            "status": "uploading",
            "created_at": datetime.now(timezone.utc),
        }

        mock_result = ExtractionResult(
            positionen=[ExtractedDoorPosition(positions_nr="1.01", quellen={})],
            dokument_zusammenfassung="Test",
            warnungen=[],
            dokument_typ=DokumentTyp.XLSX,
        )

        async def mock_pipeline(*args, **kwargs):
            return mock_result

        with patch("v2.routers.analyze_v2.run_extraction_pipeline", side_effect=mock_pipeline):
            resp = test_client.post(
                "/api/v2/analyze",
                json={"tender_id": tender_id},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["enrichment_report"] is None
        assert data["conflicts"] == []
        assert data["total_conflicts"] == 0

        _tenders.clear()
