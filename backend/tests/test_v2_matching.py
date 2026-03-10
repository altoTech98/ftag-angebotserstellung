"""
Tests for Phase 4: Product Matching Engine.

Tests TF-IDF index, domain knowledge, AI matcher with safety caps,
and concurrent matching pipeline.
"""

import asyncio
from unittest.mock import MagicMock, AsyncMock, patch

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
from v2.schemas.matching import (
    MatchResult,
    MatchCandidate,
    DimensionScore,
    MatchDimension,
)
from v2.matching.ai_matcher import (
    _apply_safety_caps,
    _set_hat_match,
    match_single_position,
    match_positions,
)


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


# ---------------------------------------------------------------------------
# Helpers for Task 2 tests
# ---------------------------------------------------------------------------


def _make_all_dimension_scores(
    brandschutz_score: float = 0.9,
    base_score: float = 0.8,
) -> list[DimensionScore]:
    """Create a full set of 6 DimensionScores."""
    return [
        DimensionScore(dimension=MatchDimension.MASSE, score=base_score, begruendung="Masse passt"),
        DimensionScore(dimension=MatchDimension.BRANDSCHUTZ, score=brandschutz_score, begruendung="Brandschutz bewertet"),
        DimensionScore(dimension=MatchDimension.SCHALLSCHUTZ, score=base_score, begruendung="Schallschutz passt"),
        DimensionScore(dimension=MatchDimension.MATERIAL, score=base_score, begruendung="Material passt"),
        DimensionScore(dimension=MatchDimension.ZERTIFIZIERUNG, score=base_score, begruendung="Zertifizierung ok"),
        DimensionScore(dimension=MatchDimension.LEISTUNG, score=base_score, begruendung="Leistung ok"),
    ]


def _make_match_result(
    gesamt_konfidenz: float = 0.85,
    brandschutz_score: float = 0.9,
    num_alternatives: int = 2,
    hat_match: bool = False,
) -> MatchResult:
    """Create a MatchResult with configurable scores."""
    bester = MatchCandidate(
        produkt_id="KT-001",
        produkt_name="Prestige 51 EI30",
        gesamt_konfidenz=gesamt_konfidenz,
        dimension_scores=_make_all_dimension_scores(brandschutz_score=brandschutz_score),
        begruendung="Best match overall",
    )
    alternatives = [
        MatchCandidate(
            produkt_id=f"KT-{i+2:03d}",
            produkt_name=f"Alternative {i+1}",
            gesamt_konfidenz=gesamt_konfidenz - 0.05 * (i + 1),
            dimension_scores=_make_all_dimension_scores(brandschutz_score=brandschutz_score),
            begruendung=f"Alternative {i+1}",
        )
        for i in range(num_alternatives)
    ]
    return MatchResult(
        positions_nr="1.01",
        bester_match=bester,
        alternative_matches=alternatives,
        hat_match=hat_match,
        match_methode="tfidf_ai",
    )


# ---------------------------------------------------------------------------
# Task 2: Safety Caps and Threshold Tests
# ---------------------------------------------------------------------------


class TestSafetyCaps:
    def test_safety_cap_applied(self):
        """When Brandschutz dimension < 0.5, gesamt_konfidenz capped at 0.6."""
        result = _make_match_result(
            gesamt_konfidenz=0.92,
            brandschutz_score=0.3,
        )
        capped = _apply_safety_caps(result)
        assert capped.bester_match.gesamt_konfidenz <= 0.6
        assert capped.hat_match is False

    def test_safety_cap_not_applied_when_brandschutz_ok(self):
        """When Brandschutz >= 0.5, no cap applied."""
        result = _make_match_result(
            gesamt_konfidenz=0.92,
            brandschutz_score=0.85,
        )
        capped = _apply_safety_caps(result)
        assert capped.bester_match.gesamt_konfidenz == 0.92

    def test_hat_match_threshold_true(self):
        """hat_match=True only when gesamt_konfidenz >= 0.95."""
        result = _make_match_result(gesamt_konfidenz=0.97)
        updated = _set_hat_match(result)
        assert updated.hat_match is True

    def test_hat_match_threshold_false(self):
        """hat_match=False when gesamt_konfidenz < 0.95."""
        result = _make_match_result(gesamt_konfidenz=0.94)
        updated = _set_hat_match(result)
        assert updated.hat_match is False

    def test_hat_match_no_bester_match(self):
        """hat_match=False when no bester_match."""
        result = MatchResult(
            positions_nr="1.01",
            bester_match=None,
            alternative_matches=[],
            hat_match=True,  # Will be overridden
            match_methode="tfidf_ai",
        )
        updated = _set_hat_match(result)
        assert updated.hat_match is False


class TestDimensionCompleteness:
    def test_dimension_scores_all_present(self):
        """MatchResult.bester_match has exactly 6 DimensionScore entries."""
        result = _make_match_result()
        assert len(result.bester_match.dimension_scores) == 6
        dimensions_present = {ds.dimension for ds in result.bester_match.dimension_scores}
        expected = {
            MatchDimension.MASSE,
            MatchDimension.BRANDSCHUTZ,
            MatchDimension.SCHALLSCHUTZ,
            MatchDimension.MATERIAL,
            MatchDimension.ZERTIFIZIERUNG,
            MatchDimension.LEISTUNG,
        }
        assert dimensions_present == expected


class TestAlternativesLimit:
    def test_alternatives_limited(self):
        """alternative_matches has at most 3 entries after processing."""
        result = _make_match_result(num_alternatives=5)
        # AI matcher should limit to 3
        from v2.matching.ai_matcher import _limit_alternatives
        limited = _limit_alternatives(result)
        assert len(limited.alternative_matches) <= 3


# ---------------------------------------------------------------------------
# Task 2: AI Matcher Integration Tests
# ---------------------------------------------------------------------------


class TestMatchSinglePosition:
    @pytest.mark.asyncio
    async def test_match_single_position_returns_match_result(self, fire_door_position):
        """mock Claude call returns valid MatchResult."""
        mock_result = _make_match_result(gesamt_konfidenz=0.88, brandschutz_score=0.9)

        mock_response = MagicMock()
        mock_response.parsed = mock_result

        mock_client = MagicMock()
        mock_client.messages = MagicMock()
        mock_client.messages.parse = MagicMock(return_value=mock_response)

        candidates = [{"row_index": 0, "Produktegruppen": "Rahmentuere", "Brandschutzklasse": "EI30"}]

        result = await match_single_position(
            client=mock_client,
            position=fire_door_position,
            candidates=candidates,
        )

        assert isinstance(result, MatchResult)
        assert result.match_methode == "tfidf_ai"
        # Verify safety caps and hat_match were applied
        assert result.hat_match is False  # 0.88 < 0.95


# ---------------------------------------------------------------------------
# Task 1 (Plan 02): Feedback V2 Store Tests
# ---------------------------------------------------------------------------


class TestFeedbackSaveAndLoad:
    def test_feedback_save_and_load(self, tmp_path):
        """Save a correction, reload store, correction persists in JSON file."""
        store_path = str(tmp_path / "feedback_v2.json")
        from v2.matching.feedback_v2 import FeedbackStoreV2, FeedbackEntry

        store = FeedbackStoreV2(store_path=store_path)
        entry = FeedbackEntry(
            positions_nr="1.01",
            requirement_summary="Brandschutztuere EI30 einflg",
            original_match={"produkt_id": "KT-001", "gesamt_konfidenz": 0.7},
            corrected_match={"produkt_id": "KT-005", "produkt_name": "Prestige EI30"},
            correction_reason="Falsche Brandschutzklasse",
        )
        store.save_correction(entry)

        # Reload from disk
        store2 = FeedbackStoreV2(store_path=store_path)
        assert len(store2.get_all()) == 1
        loaded = store2.get_all()[0]
        assert loaded.positions_nr == "1.01"
        assert loaded.corrected_match["produkt_id"] == "KT-005"

    def test_feedback_find_relevant(self, tmp_path):
        """Save 3 corrections, query with similar text, returns most similar first."""
        store_path = str(tmp_path / "feedback_v2.json")
        from v2.matching.feedback_v2 import FeedbackStoreV2, FeedbackEntry

        store = FeedbackStoreV2(store_path=store_path)

        entries = [
            FeedbackEntry(
                positions_nr="1.01",
                requirement_summary="Brandschutztuere EI30 Rahmentuere",
                original_match={"produkt_id": "KT-001", "gesamt_konfidenz": 0.6},
                corrected_match={"produkt_id": "KT-010", "produkt_name": "Prestige EI30"},
                correction_reason="Falsches Produkt",
            ),
            FeedbackEntry(
                positions_nr="2.01",
                requirement_summary="Schiebetuer Schallschutz 37dB",
                original_match={"produkt_id": "KT-006", "gesamt_konfidenz": 0.5},
                corrected_match={"produkt_id": "KT-007", "produkt_name": "Schiebe EI60"},
                correction_reason="Schallschutz nicht ausreichend",
            ),
            FeedbackEntry(
                positions_nr="3.01",
                requirement_summary="Holztuer Innentuer ohne Brandschutz",
                original_match={"produkt_id": "KT-004", "gesamt_konfidenz": 0.8},
                corrected_match={"produkt_id": "KT-003", "produkt_name": "Confort 51"},
                correction_reason="Holztuer besser",
            ),
        ]
        for e in entries:
            store.save_correction(e)

        # Query for Brandschutz-related text
        results = store.find_relevant_feedback("Brandschutztuere EI30 Rahmentuere Standard")
        assert len(results) > 0
        # Most similar should be the Brandschutz entry
        assert results[0]["corrected_match"]["produkt_id"] == "KT-010"

    def test_feedback_tfidf_similarity(self, tmp_path):
        """Corrections with matching Brandschutz/Schallschutz terms score higher."""
        store_path = str(tmp_path / "feedback_v2.json")
        from v2.matching.feedback_v2 import FeedbackStoreV2, FeedbackEntry

        store = FeedbackStoreV2(store_path=store_path)

        store.save_correction(FeedbackEntry(
            positions_nr="1.01",
            requirement_summary="Brandschutz EI60 Stahltuer Widerstandsklasse RC2",
            original_match={"produkt_id": "KT-001", "gesamt_konfidenz": 0.5},
            corrected_match={"produkt_id": "KT-002", "produkt_name": "Prestige EI60"},
            correction_reason="Brandschutz korrekt",
        ))
        store.save_correction(FeedbackEntry(
            positions_nr="2.01",
            requirement_summary="Pendeltuere ohne Brandschutz ohne Schallschutz",
            original_match={"produkt_id": "KT-009", "gesamt_konfidenz": 0.4},
            corrected_match={"produkt_id": "KT-008", "produkt_name": "Pendel 51"},
            correction_reason="Falscher Typ",
        ))

        results = store.find_relevant_feedback("Brandschutz EI60 Stahltuer")
        assert len(results) >= 1
        # The Brandschutz entry should score highest
        assert results[0]["corrected_match"]["produkt_name"] == "Prestige EI60"

    def test_feedback_injection_in_prompt(self, tmp_path):
        """Feedback examples formatted correctly for prompt injection."""
        store_path = str(tmp_path / "feedback_v2.json")
        from v2.matching.feedback_v2 import FeedbackStoreV2, FeedbackEntry
        from v2.matching.prompts import format_feedback_section

        store = FeedbackStoreV2(store_path=store_path)
        store.save_correction(FeedbackEntry(
            positions_nr="1.01",
            requirement_summary="Brandschutztuere EI30",
            original_match={"produkt_id": "KT-001", "gesamt_konfidenz": 0.6},
            corrected_match={"produkt_id": "KT-005", "produkt_name": "Prestige EI30"},
            correction_reason="Falsche Zuordnung",
        ))

        results = store.find_relevant_feedback("Brandschutztuere EI30")
        formatted = format_feedback_section(results)
        assert "Korrekturen" in formatted
        assert "Prestige EI30" in formatted


class TestFeedbackEndpoint:
    def test_feedback_endpoint_save(self, tmp_path):
        """POST /api/v2/feedback with valid body returns 200 and saves correction."""
        from fastapi.testclient import TestClient
        from unittest.mock import patch

        # Need to patch the singleton to use tmp_path
        from v2.matching import feedback_v2 as fb_module

        test_store_path = str(tmp_path / "feedback_v2.json")
        test_store = fb_module.FeedbackStoreV2(store_path=test_store_path)

        with patch.object(fb_module, "_feedback_store", test_store):
            with patch.object(fb_module, "get_feedback_store", return_value=test_store):
                # Import app after patching
                from v2.routers.feedback_v2 import router as feedback_router
                from fastapi import FastAPI

                test_app = FastAPI()
                test_app.include_router(feedback_router)
                client = TestClient(test_app)

                response = client.post(
                    "/api/v2/feedback",
                    json={
                        "positions_nr": "1.01",
                        "requirement_summary": "Brandschutztuere EI30",
                        "original_produkt_id": "KT-001",
                        "original_konfidenz": 0.7,
                        "corrected_produkt_id": "KT-005",
                        "corrected_produkt_name": "Prestige EI30",
                        "correction_reason": "Falsche Brandschutzklasse",
                    },
                )

                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "saved"
                assert data["feedback_id"].startswith("fb_v2_")

    def test_feedback_endpoint_validation(self):
        """POST /api/v2/feedback with missing fields returns 422."""
        from fastapi.testclient import TestClient
        from v2.routers.feedback_v2 import router as feedback_router
        from fastapi import FastAPI

        test_app = FastAPI()
        test_app.include_router(feedback_router)
        client = TestClient(test_app)

        response = client.post(
            "/api/v2/feedback",
            json={"positions_nr": "1.01"},  # Missing required fields
        )

        assert response.status_code == 422


class TestMatchPositionsConcurrent:
    @pytest.mark.asyncio
    async def test_match_positions_concurrent(self, tfidf_index):
        """match_positions processes multiple positions concurrently."""
        positions = [
            ExtractedDoorPosition(
                positions_nr=f"{i}.01",
                brandschutz_klasse=BrandschutzKlasse.EI30,
                breite_mm=1000,
                hoehe_mm=2100,
            )
            for i in range(3)
        ]

        mock_result = _make_match_result(gesamt_konfidenz=0.85)
        mock_response = MagicMock()
        mock_response.parsed = mock_result

        mock_client = MagicMock()
        mock_client.messages = MagicMock()
        mock_client.messages.parse = MagicMock(return_value=mock_response)

        results = await match_positions(
            client=mock_client,
            positions=positions,
            tfidf_index=tfidf_index,
        )

        assert len(results) == 3
        for r in results:
            assert isinstance(r, MatchResult)
            assert r.match_methode == "tfidf_ai"
