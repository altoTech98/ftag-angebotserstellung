"""
Tests for Pass 1 structural extraction from ParseResult.

Tests cover XLSX extraction, PDF table extraction, field source provenance,
and edge cases like non-door sheets.
"""

import pytest

from v2.parsers.base import ParseResult
from v2.schemas.extraction import ExtractedDoorPosition
from v2.schemas.common import FieldSource


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def xlsx_parse_result():
    """ParseResult simulating XLSX output with door-list columns."""
    text = (
        "=== Sheet: Tuerliste ===\n"
        "tuer_nr: 1.01 | breite: 1000 | hoehe: 2100 | brandschutz: EI30 | schallschutz: Rw 37dB | tuertyp: Holz\n"
        "tuer_nr: 1.02 | breite: 900 | hoehe: 2050 | brandschutz: EI60 | schallschutz: Rw 32dB | tuertyp: Stahl\n"
        "tuer_nr: T2.03 | breite: 800 | hoehe: 2000 | brandschutz: | schallschutz: | tuertyp: Holz\n"
    )
    return ParseResult(
        text=text,
        format="xlsx",
        page_count=1,
        warnings=[],
        metadata={
            "detected_columns": {
                "Tuerliste": {
                    "Tuer Nr.": "tuer_nr",
                    "Breite (mm)": "breite",
                    "Hoehe (mm)": "hoehe",
                    "Brandschutz": "brandschutz",
                    "Schallschutz (dB)": "schallschutz",
                    "Material": "tuertyp",
                }
            }
        },
        source_file="test_tuerliste.xlsx",
        tables=[],
    )


@pytest.fixture
def non_door_parse_result():
    """ParseResult with too few door-related columns."""
    text = (
        "=== Sheet: Allgemein ===\n"
        "Projekt: Schulhaus Buochs | Datum: 2026-01-15\n"
        "Auftraggeber: Gemeinde Buochs\n"
    )
    return ParseResult(
        text=text,
        format="xlsx",
        page_count=1,
        warnings=[],
        metadata={
            "detected_columns": {
                "Allgemein": {
                    "Projekt": "projekt",
                }
            }
        },
        source_file="test_allgemein.xlsx",
        tables=[],
    )


@pytest.fixture
def pdf_parse_result_with_tables():
    """ParseResult simulating PDF with markdown tables."""
    table_md = (
        "| Pos. | Breite | Hoehe | Brandschutz |\n"
        "|---|---|---|---|\n"
        "| 1.01 | 1000 | 2100 | EI30 |\n"
        "| 1.02 | 900 | 2050 | EI60 |\n"
    )
    return ParseResult(
        text="Tuerliste Projekt XY\n\n" + table_md,
        format="pdf",
        page_count=3,
        warnings=[],
        metadata={},
        source_file="ausschreibung.pdf",
        tables=[table_md],
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestPass1ExtractStructural:

    def test_pass1_extracts_positions_from_xlsx(self, xlsx_parse_result):
        """Given XLSX ParseResult with door-list text, extract positions."""
        from v2.extraction.pass1_structural import extract_structural

        positions = extract_structural(xlsx_parse_result)
        assert len(positions) >= 2
        pos_nrs = [p.positions_nr for p in positions]
        assert "1.01" in pos_nrs
        assert "1.02" in pos_nrs

        # Check field values on first position
        pos1 = next(p for p in positions if p.positions_nr == "1.01")
        assert pos1.breite_mm == 1000
        assert pos1.hoehe_mm == 2100

    def test_pass1_skips_non_door_sheets(self, non_door_parse_result):
        """Sheets with < _MIN_DOOR_FIELDS matched columns produce empty list."""
        from v2.extraction.pass1_structural import extract_structural

        positions = extract_structural(non_door_parse_result)
        assert positions == []

    def test_pass1_extracts_from_pdf_tables(self, pdf_parse_result_with_tables):
        """PDF ParseResult with markdown tables should yield positions."""
        from v2.extraction.pass1_structural import extract_structural

        positions = extract_structural(pdf_parse_result_with_tables)
        assert len(positions) >= 2
        pos_nrs = [p.positions_nr for p in positions]
        assert "1.01" in pos_nrs
        assert "1.02" in pos_nrs

    def test_pass1_sets_field_source(self, xlsx_parse_result):
        """Every extracted field must have a FieldSource entry in quellen."""
        from v2.extraction.pass1_structural import extract_structural

        positions = extract_structural(xlsx_parse_result)
        assert len(positions) > 0
        pos1 = positions[0]
        # quellen should have entries for extracted fields
        assert len(pos1.quellen) > 0
        for field_name, source in pos1.quellen.items():
            assert isinstance(source, FieldSource)
            assert source.dokument == "test_tuerliste.xlsx"
            assert source.konfidenz == 0.8

    def test_pass1_extracts_fire_sound_material(self, xlsx_parse_result):
        """Regex extracts brandschutz, schallschutz, and material."""
        from v2.extraction.pass1_structural import extract_structural

        positions = extract_structural(xlsx_parse_result)
        pos1 = next(p for p in positions if p.positions_nr == "1.01")

        # Fire protection
        assert pos1.brandschutz_klasse is not None
        assert pos1.brandschutz_klasse.value == "EI30"

        # Sound protection
        assert pos1.schallschutz_klasse is not None
        assert "37" in pos1.schallschutz_klasse.value

        # Material
        assert pos1.material_blatt is not None
        assert pos1.material_blatt.value == "Holz"
