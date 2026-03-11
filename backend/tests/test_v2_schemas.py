"""
V2 Schema validation tests.

Tests schema creation, serialization, JSON Schema generation,
and anthropic messages.parse() compatibility.
"""

import typing
from datetime import datetime, timezone

import pytest

from v2.schemas.common import (
    BrandschutzKlasse,
    DokumentTyp,
    FieldSource,
    MaterialTyp,
    OeffnungsArt,
    SchallschutzKlasse,
    TrackedField,
    ZargenTyp,
)
from v2.schemas.extraction import ExtractedDoorPosition, ExtractionResult
from v2.schemas.gaps import (
    AlternativeProduct,
    GapDimension,
    GapItem,
    GapReport,
    GapSeverity,
)
from v2.schemas.matching import (
    DimensionScore,
    MatchCandidate,
    MatchDimension,
    MatchResult,
)
from v2.schemas.pipeline import (
    AnalysisJob,
    PipelineStage,
    StageProgress,
    StageStatus,
)
from v2.schemas.validation import AdversarialResult, ValidationOutcome

# Import fixtures from conftest_v2
pytest_plugins = ["tests.conftest_v2"]


class TestExtractedDoorPosition:
    """Tests for the central ExtractedDoorPosition schema."""

    def test_extracted_door_position_creation(self):
        """Create with minimal fields (positions_nr only), verify all Optional fields default to None."""
        pos = ExtractedDoorPosition(positions_nr="1.01")
        assert pos.positions_nr == "1.01"
        assert pos.breite_mm is None
        assert pos.hoehe_mm is None
        assert pos.brandschutz_klasse is None
        assert pos.schallschutz_db is None
        assert pos.material_blatt is None
        assert pos.oeffnungsart is None
        assert pos.bemerkungen is None
        assert pos.anzahl == 1  # default
        assert pos.quellen == {}  # default_factory

    def test_extracted_door_position_full(self, sample_door_position):
        """Create with all major fields populated, verify serialization round-trip."""
        pos = sample_door_position

        # Verify key fields
        assert pos.positions_nr == "1.01"
        assert pos.breite_mm == 1000
        assert pos.brandschutz_klasse == BrandschutzKlasse.EI30
        assert pos.schallschutz_klasse == SchallschutzKlasse.RW_32

        # Round-trip: model_dump -> model_validate
        dumped = pos.model_dump()
        restored = ExtractedDoorPosition.model_validate(dumped)
        assert restored.positions_nr == pos.positions_nr
        assert restored.breite_mm == pos.breite_mm
        assert restored.brandschutz_klasse == pos.brandschutz_klasse
        assert restored.quellen["breite_mm"].zelle == "D5"

    def test_all_optional_fields_have_defaults(self):
        """Every Optional field in ExtractedDoorPosition must have a default value.

        This catches the Pydantic v2 pitfall where Optional[X] without = None
        makes the field required.
        """
        for field_name, field_info in ExtractedDoorPosition.model_fields.items():
            annotation = field_info.annotation

            # Check if annotation is Optional (Union with NoneType)
            origin = typing.get_origin(annotation)
            if origin is typing.Union:
                args = typing.get_args(annotation)
                if type(None) in args:
                    # This is an Optional field -- must have a default
                    assert not field_info.is_required(), (
                        f"Optional field '{field_name}' is missing default value (= None). "
                        f"Pydantic v2 requires explicit defaults for Optional fields."
                    )


class TestFieldSourceTracking:
    """Tests for field-level provenance tracking."""

    def test_field_source_tracking(self):
        """Create FieldSource with all fields, attach to TrackedField."""
        source = FieldSource(
            dokument="ausschreibung.pdf",
            seite=3,
            zeile=15,
            zelle="B15",
            sheet=None,
            konfidenz=0.92,
        )
        assert source.dokument == "ausschreibung.pdf"
        assert source.seite == 3
        assert source.konfidenz == 0.92

        tracked = TrackedField(wert="EI30", quelle=source)
        assert tracked.wert == "EI30"
        assert tracked.quelle.seite == 3

    def test_field_source_in_quellen_dict(self, sample_door_position):
        """Verify quellen dict maps field names to FieldSource objects."""
        pos = sample_door_position
        assert "breite_mm" in pos.quellen
        assert pos.quellen["breite_mm"].dokument == "tuerliste.xlsx"
        assert pos.quellen["breite_mm"].zelle == "D5"
        assert pos.quellen["breite_mm"].konfidenz == 0.95


class TestEnums:
    """Tests for domain enums."""

    def test_enum_values(self):
        """Verify key enums have expected values."""
        # Brandschutz
        assert BrandschutzKlasse.EI30.value == "EI30"
        assert BrandschutzKlasse.EI60.value == "EI60"
        assert BrandschutzKlasse.EI90.value == "EI90"
        assert BrandschutzKlasse.T30.value == "T30"
        assert BrandschutzKlasse.KEINE.value == "keine"

        # Schallschutz
        assert SchallschutzKlasse.RW_32.value == "Rw 32dB"
        assert SchallschutzKlasse.RW_37.value == "Rw 37dB"
        assert SchallschutzKlasse.RW_47.value == "Rw 47dB"

        # Material
        assert MaterialTyp.HOLZ.value == "Holz"
        assert MaterialTyp.STAHL.value == "Stahl"
        assert MaterialTyp.HOLZ_STAHL.value == "Holz/Stahl"

    def test_enum_plus_freitext_pattern(self):
        """Verify enum=None + freitext='custom value' coexist."""
        pos = ExtractedDoorPosition(
            positions_nr="2.01",
            brandschutz_klasse=None,
            brandschutz_freitext="Spezial-Brandschutz nach Kundenwunsch",
            material_blatt=None,
            material_blatt_freitext="Spezialmaterial XY-200",
        )
        assert pos.brandschutz_klasse is None
        assert pos.brandschutz_freitext == "Spezial-Brandschutz nach Kundenwunsch"
        assert pos.material_blatt is None
        assert pos.material_blatt_freitext == "Spezialmaterial XY-200"


class TestMatchingSchemas:
    """Tests for matching stage schemas."""

    def test_match_result_creation(self):
        """Create MatchResult with candidates and dimension scores."""
        candidate = MatchCandidate(
            produkt_id="FTAG-BAT-180",
            produkt_name="FTAG BAT 180 EI30",
            gesamt_konfidenz=0.87,
            dimension_scores=[
                DimensionScore(
                    dimension=MatchDimension.MASSE,
                    score=0.95,
                    begruendung="Breite und Hoehe passen exakt",
                ),
                DimensionScore(
                    dimension=MatchDimension.BRANDSCHUTZ,
                    score=0.99,
                    begruendung="EI30 stimmt ueberein",
                ),
            ],
            begruendung="Bestes Produkt fuer Buerotuere mit EI30",
        )

        result = MatchResult(
            positions_nr="1.01",
            bester_match=candidate,
            alternative_matches=[],
            hat_match=True,
            match_methode="tfidf_ai",
        )

        assert result.hat_match is True
        assert result.bester_match.gesamt_konfidenz == 0.87
        assert len(result.bester_match.dimension_scores) == 2
        assert result.bester_match.dimension_scores[0].dimension == MatchDimension.MASSE


class TestValidationSchemas:
    """Tests for adversarial validation schemas."""

    def test_adversarial_result_creation(self):
        """Create AdversarialResult with chain_of_thought."""
        candidate = MatchCandidate(
            produkt_id="FTAG-BAT-180",
            produkt_name="FTAG BAT 180 EI30",
            gesamt_konfidenz=0.87,
            dimension_scores=[],
            begruendung="Test match",
        )

        result = AdversarialResult(
            positions_nr="1.01",
            original_match=candidate,
            ergebnis=ValidationOutcome.BESTAETIGT,
            adversarial_begruendung="Match ist korrekt. Alle Dimensionen stimmen ueberein.",
            chain_of_thought=[
                "Schritt 1: Brandschutzklasse EI30 pruefen - stimmt ueberein",
                "Schritt 2: Masse pruefen - Breite 1000mm passt zu Lichtmass max",
                "Schritt 3: Material pruefen - Holz ist kompatibel",
            ],
            finale_konfidenz=0.92,
            triple_check_durchgefuehrt=False,
        )

        assert result.ergebnis == ValidationOutcome.BESTAETIGT
        assert len(result.chain_of_thought) == 3
        assert result.finale_konfidenz == 0.92
        assert result.triple_check_ergebnis is None


class TestGapSchemas:
    """Tests for gap analysis schemas."""

    def test_gap_report_creation(self):
        """Create GapReport with items and alternatives."""
        report = GapReport(
            positions_nr="1.01",
            gaps=[
                GapItem(
                    dimension=GapDimension.MASSE,
                    schweregrad=GapSeverity.MAJOR,
                    anforderung_wert="Breite 1200mm",
                    katalog_wert="max. 1100mm",
                    abweichung_beschreibung="Geforderte Breite ueberschreitet Katalog-Maximum",
                    aenderungsvorschlag="Sonderanfertigung oder alternatives Produkt waehlen",
                ),
                GapItem(
                    dimension=GapDimension.ZERTIFIZIERUNG,
                    schweregrad=GapSeverity.MINOR,
                    anforderung_wert="CE-Kennzeichnung",
                    katalog_wert=None,
                    abweichung_beschreibung="CE-Status nicht im Katalog erfasst",
                ),
            ],
            alternativen=[
                AlternativeProduct(
                    produkt_id="FTAG-RAH-200",
                    produkt_name="FTAG Rahmentuer 200",
                    teilweise_deckung=0.75,
                    verbleibende_gaps=["Breite nur bis 1150mm"],
                ),
            ],
            zusammenfassung="2 Gaps identifiziert: 1 Major (Masse), 1 Minor (Zertifizierung)",
        )

        assert len(report.gaps) == 2
        assert report.gaps[0].schweregrad == GapSeverity.MAJOR
        assert len(report.alternativen) == 1
        assert report.alternativen[0].teilweise_deckung == 0.75


class TestPipelineSchemas:
    """Tests for pipeline orchestration schemas."""

    def test_pipeline_job_creation(self):
        """Create AnalysisJob with stages."""
        job = AnalysisJob(
            job_id="job-2026-001",
            erstellt_am=datetime(2026, 3, 10, 12, 0, 0, tzinfo=timezone.utc),
            dateien=["ausschreibung.pdf", "tuerliste.xlsx"],
            pipeline_status=[
                StageProgress(
                    stage=PipelineStage.PARSING,
                    status=StageStatus.COMPLETED,
                    fortschritt_prozent=100.0,
                ),
                StageProgress(
                    stage=PipelineStage.EXTRACTION,
                    status=StageStatus.RUNNING,
                    fortschritt_prozent=45.0,
                    aktuelle_position="1.03",
                ),
                StageProgress(
                    stage=PipelineStage.MATCHING,
                    status=StageStatus.PENDING,
                ),
            ],
        )

        assert job.job_id == "job-2026-001"
        assert len(job.dateien) == 2
        assert len(job.pipeline_status) == 3
        assert job.pipeline_status[1].status == StageStatus.RUNNING
        assert job.ergebnis_pfad is None


class TestAnthropicCompatibility:
    """Tests for schema compatibility with anthropic messages.parse()."""

    def test_anthropic_compatibility(self):
        """Verify all main schemas produce valid JSON Schema via model_json_schema().

        This validates that the schemas can be used with
        client.messages.parse(output_format=Model).
        """
        schemas_to_check = [
            ExtractedDoorPosition,
            ExtractionResult,
            MatchResult,
            AdversarialResult,
            GapReport,
            AnalysisJob,
        ]

        for model_class in schemas_to_check:
            schema = model_class.model_json_schema()
            assert "properties" in schema, (
                f"{model_class.__name__}.model_json_schema() missing 'properties' key"
            )
            # Verify required fields are listed
            if "required" in schema:
                assert isinstance(schema["required"], list)

    def test_schema_nesting_depth(self):
        """Verify ExtractedDoorPosition JSON schema has max 3 levels of nesting.

        Per RESEARCH.md recommendation: keep nesting depth manageable
        for messages.parse() compatibility.
        """
        schema = ExtractedDoorPosition.model_json_schema()

        def max_depth(obj, current=0):
            if not isinstance(obj, dict):
                return current
            depths = [current]
            if "properties" in obj:
                for prop in obj["properties"].values():
                    depths.append(max_depth(prop, current + 1))
            if "items" in obj:
                depths.append(max_depth(obj["items"], current + 1))
            # Check $defs for referenced types
            if "$defs" in obj:
                for def_schema in obj["$defs"].values():
                    if "properties" in def_schema:
                        depths.append(max_depth(def_schema, current + 1))
            return max(depths)

        depth = max_depth(schema)
        assert depth <= 3, (
            f"ExtractedDoorPosition nesting depth is {depth}, max allowed is 3"
        )

    def test_extraction_result_serialization(self, sample_door_position):
        """Verify ExtractionResult round-trips through JSON."""
        result = ExtractionResult(
            positionen=[sample_door_position],
            dokument_zusammenfassung="Test document with 1 door position",
            warnungen=["Test warning"],
            dokument_typ=DokumentTyp.XLSX,
        )

        json_str = result.model_dump_json()
        restored = ExtractionResult.model_validate_json(json_str)
        assert len(restored.positionen) == 1
        assert restored.positionen[0].positions_nr == "1.01"
        assert restored.dokument_typ == DokumentTyp.XLSX
