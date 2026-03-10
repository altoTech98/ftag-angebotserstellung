"""
Tests for Phase 4: Product Matching Engine.

Tests TF-IDF index, domain knowledge, AI matcher with safety caps,
and concurrent matching pipeline.
"""

import pytest
import pandas as pd
import numpy as np

from v2.matching.domain_knowledge import (
    FIRE_CLASS_RANK,
    RESISTANCE_RANK,
    CATEGORY_KEYWORDS,
    detect_category,
    normalize_fire_class,
    normalize_resistance,
)
from v2.matching.tfidf_index import CatalogTfidfIndex
from v2.schemas.extraction import ExtractedDoorPosition
from v2.schemas.common import BrandschutzKlasse, SchallschutzKlasse, MaterialTyp


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_mock_catalog_df() -> pd.DataFrame:
    """Create a realistic mock catalog DataFrame with ~10 products."""
    data = {
        "Produktegruppen": [
            "Rahmentuere", "Rahmentuere", "Rahmentuere",
            "Zargentuere", "Zargentuere",
            "Schiebetuere", "Schiebetuere",
            "Festverglasung", "Pendeltuere",
            "Brandschutztor",
        ],
        "Kostentraeger": [
            "KT-001", "KT-002", "KT-003",
            "KT-004", "KT-005",
            "KT-006", "KT-007",
            "KT-008", "KT-009",
            "KT-010",
        ],
        "Anzahl Fluegel": [
            "1-flg", "1-flg", "2-flg",
            "1-flg", "2-flg",
            "1-flg", "2-flg",
            "1-flg", "2-flg",
            "1-flg",
        ],
        "Tuerblatt / Verglasungsart / Rollkasten": [
            "Prestige 51 EI30", "Prestige 51 EI60", "Confort 51 EI30",
            "Nova 40", "Maxima 55 EI60",
            "Schiebe EI30", "Schiebe EI60",
            "Festverglasung EI30", "Pendel 51",
            "Brandschutztor EI90",
        ],
        "Tuerblattausfuehrung": [
            "Standard", "Standard", "Standard",
            "Schmal", "Breit",
            "Standard", "Standard",
            "Fest", "Pendel",
            "Sektional",
        ],
        "Brandschutzklasse": [
            "EI30", "EI60", "EI30",
            "", "EI60",
            "EI30", "EI60",
            "EI30", "",
            "EI90",
        ],
        "VKF.Nr": [
            "VKF-001", "VKF-002", "VKF-003",
            "", "VKF-005",
            "VKF-006", "VKF-007",
            "VKF-008", "",
            "VKF-010",
        ],
        "Unused Col": ["x"] * 10,
        "Lichtmass max. B x H in mm": [
            "1100 x 2400", "1100 x 2400", "1800 x 2400",
            "1000 x 2200", "1800 x 2200",
            "1200 x 2400", "2000 x 2400",
            "1100 x 2400", "1800 x 2400",
            "3000 x 3000",
        ],
        "Tuerflaece max. in m2": [
            "2.64", "2.64", "4.32",
            "2.2", "3.96",
            "2.88", "4.8",
            "2.64", "4.32",
            "9.0",
        ],
        "Col10": [""] * 10,
        "Col11": [""] * 10,
        "Col12": [""] * 10,
        "Col13": [""] * 10,
        "Col14": [""] * 10,
        "Glasausschnitt": [
            "ja", "nein", "ja",
            "nein", "nein",
            "nein", "nein",
            "ja", "nein",
            "nein",
        ],
        "Col16": [""] * 10,
        "Tuerrohling (dB)": [
            "32", "37", "32",
            "27", "37",
            "32", "37",
            "32", "27",
            "",
        ],
        "Widerstandsklasse": [
            "", "RC2", "",
            "", "RC3",
            "", "",
            "", "",
            "",
        ],
        "Bleigleichwert (2mm)": [""] * 10,
        "VKF.Nr / Klasse S200": [
            "", "S200", "",
            "", "",
            "", "",
            "", "",
            "",
        ],
        "Umfassung Materialisierung": [
            "grundiert", "grundiert", "grundiert",
            "Stahl", "Stahl",
            "grundiert", "grundiert",
            "grundiert", "grundiert",
            "Stahl",
        ],
        "Giessharzbeschichtung Orsopal": [
            "ja", "ja", "ja",
            "nein", "nein",
            "ja", "ja",
            "ja", "ja",
            "nein",
        ],
        "Oberflaechenfolie Senosan": [
            "nein", "nein", "nein",
            "ja", "ja",
            "nein", "nein",
            "nein", "nein",
            "nein",
        ],
    }
    return pd.DataFrame(data)


@pytest.fixture
def mock_catalog_df() -> pd.DataFrame:
    return _make_mock_catalog_df()


@pytest.fixture
def tfidf_index(mock_catalog_df) -> CatalogTfidfIndex:
    """Build a TF-IDF index from mock catalog."""
    return CatalogTfidfIndex(catalog_df=mock_catalog_df)


@pytest.fixture
def fire_door_position() -> ExtractedDoorPosition:
    """A fire-rated door position for testing TF-IDF search."""
    return ExtractedDoorPosition(
        positions_nr="1.01",
        positions_bezeichnung="Brandschutztuere EI30",
        brandschutz_klasse=BrandschutzKlasse.EI30,
        schallschutz_db=32,
        breite_mm=1000,
        hoehe_mm=2100,
        material_blatt=MaterialTyp.HOLZ,
    )


@pytest.fixture
def sparse_position() -> ExtractedDoorPosition:
    """A position with only positions_nr."""
    return ExtractedDoorPosition(positions_nr="9.99")


# ---------------------------------------------------------------------------
# Task 1: Domain Knowledge Tests
# ---------------------------------------------------------------------------


class TestFireClassRank:
    def test_fire_class_rank_mapping(self):
        """FIRE_CLASS_RANK maps ei30->1, ei60->2, etc."""
        assert FIRE_CLASS_RANK["ei30"] == 1
        assert FIRE_CLASS_RANK["ei60"] == 2
        assert FIRE_CLASS_RANK["ei90"] == 3
        assert FIRE_CLASS_RANK["ei120"] == 4
        assert FIRE_CLASS_RANK["t30"] == 1
        assert FIRE_CLASS_RANK["f60"] == 2
        assert FIRE_CLASS_RANK["ohne"] == 0

    def test_normalize_fire_class(self):
        """normalize_fire_class handles various formats."""
        assert normalize_fire_class("EI30") == 1
        assert normalize_fire_class("ei 60") == 2
        assert normalize_fire_class("T90") == 3
        assert normalize_fire_class("") == 0
        assert normalize_fire_class(None) == 0


class TestResistanceRank:
    def test_resistance_rank_mapping(self):
        """RESISTANCE_RANK maps rc1->1, rc2->2, etc."""
        assert RESISTANCE_RANK["rc1"] == 1
        assert RESISTANCE_RANK["rc2"] == 2
        assert RESISTANCE_RANK["rc3"] == 3
        assert RESISTANCE_RANK["rc4"] == 4
        assert RESISTANCE_RANK["wk2"] == 2
        assert RESISTANCE_RANK["ohne"] == 0

    def test_normalize_resistance(self):
        """normalize_resistance handles various formats."""
        assert normalize_resistance("RC2") == 2
        assert normalize_resistance("wk3") == 3
        assert normalize_resistance("") == 0
        assert normalize_resistance(None) == 0


class TestCategoryDetection:
    def test_detect_category_schiebetuer(self):
        """detect_category returns correct category for Schiebetuer."""
        assert detect_category("Schiebetuer EI30") == "Schiebetuere"

    def test_detect_category_rahmen(self):
        assert detect_category("rahmentuer standard") == "Rahmentuere"

    def test_detect_category_unknown(self):
        """Unknown text returns None."""
        assert detect_category("something completely unrelated xyz") is None

    def test_detect_category_case_insensitive(self):
        assert detect_category("SCHIEBE EI60") == "Schiebetuere"


# ---------------------------------------------------------------------------
# Task 1: TF-IDF Index Tests
# ---------------------------------------------------------------------------


class TestTfidfIndex:
    def test_tfidf_index_builds_from_catalog(self, tfidf_index):
        """CatalogTfidfIndex loads catalog DataFrame and builds vectorizer."""
        assert tfidf_index is not None
        assert tfidf_index._tfidf_matrix is not None
        assert tfidf_index._tfidf_matrix.shape[0] == 10  # 10 products

    def test_tfidf_returns_candidates(self, tfidf_index, fire_door_position):
        """search() for a fire-rated door returns candidates with scores > 0."""
        results = tfidf_index.search(fire_door_position, top_k=50)
        assert len(results) > 0
        # All results have positive scores
        for idx, score in results:
            assert score > 0

    def test_tfidf_category_boost(self, tfidf_index):
        """Products in detected category score higher with category boost."""
        # Create a position that should match Schiebetuere category
        pos = ExtractedDoorPosition(
            positions_nr="2.01",
            positions_bezeichnung="Schiebetuer EI30",
            brandschutz_klasse=BrandschutzKlasse.EI30,
        )
        results = tfidf_index.search(pos, top_k=10)
        # Schiebetuere products (indices 5, 6) should appear in top results
        top_indices = [idx for idx, _ in results[:5]]
        # At least one Schiebetuere product in top 5
        schiebe_indices = {5, 6}
        assert len(schiebe_indices & set(top_indices)) > 0, (
            f"Expected Schiebetuere products in top 5, got indices: {top_indices}"
        )

    def test_tfidf_sparse_position(self, tfidf_index, sparse_position):
        """Position with only positions_nr still returns candidates."""
        results = tfidf_index.search(sparse_position, top_k=50)
        # Should return at least some results (fallback to "Tuer" query)
        assert len(results) > 0

    def test_extract_candidate_fields(self, tfidf_index):
        """extract_candidate_fields returns relevant fields for a product."""
        fields = tfidf_index.extract_candidate_fields(0)
        assert "row_index" in fields
        assert fields["row_index"] == 0
        # Should have at least Produktegruppen
        assert "Produktegruppen" in fields
