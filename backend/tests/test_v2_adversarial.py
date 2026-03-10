"""
Tests for Phase 5: Adversarial Validation Engine.

Tests adversarial schemas, debate prompts, FOR/AGAINST validation,
resolution logic, and concurrent pipeline.
"""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from v2.schemas.adversarial import (
    AdversarialResult,
    AdversarialCandidate,
    CandidateDebate,
    DimensionCoT,
    ValidationStatus,
    ForArgument,
    ForDimensionBewertung,
    AgainstArgument,
    AgainstDimensionBewertung,
)


# ---------------------------------------------------------------------------
# Task 1: Schema Construction and Validation Tests
# ---------------------------------------------------------------------------


class TestValidationStatus:
    def test_has_exactly_three_values(self):
        """ValidationStatus enum has exactly 3 values: bestaetigt, unsicher, abgelehnt."""
        values = [v.value for v in ValidationStatus]
        assert len(values) == 3
        assert "bestaetigt" in values
        assert "unsicher" in values
        assert "abgelehnt" in values


class TestDimensionCoT:
    def test_dimension_cot_construction(self):
        """DimensionCoT stores dimension, score, reasoning, confidence_level."""
        cot = DimensionCoT(
            dimension="Brandschutz",
            score=0.95,
            reasoning="EI60 erfuellt geforderte EI30",
            confidence_level="hoch",
        )
        assert cot.dimension == "Brandschutz"
        assert cot.score == 0.95
        assert cot.reasoning == "EI60 erfuellt geforderte EI30"
        assert cot.confidence_level == "hoch"


class TestCandidateDebate:
    def test_candidate_debate_stores_for_and_against(self):
        """CandidateDebate stores for_argument and against_argument per candidate."""
        debate = CandidateDebate(
            produkt_id="KT-001",
            produkt_name="Prestige 51 EI30",
            for_argument="Alle Masse passen, Brandschutz EI30 stimmt.",
            against_argument="Schallschutz nur 32dB, gefordert 37dB.",
            for_confidence=0.88,
            against_confidence=0.72,
        )
        assert debate.produkt_id == "KT-001"
        assert debate.for_argument.startswith("Alle")
        assert debate.against_argument.startswith("Schallschutz")
        assert debate.for_confidence == 0.88
        assert debate.against_confidence == 0.72


class TestAdversarialCandidate:
    def test_adversarial_candidate_construction(self):
        """AdversarialCandidate stores adjusted_confidence and dimension_scores."""
        cot_list = [
            DimensionCoT(
                dimension="Masse",
                score=0.9,
                reasoning="Passt.",
                confidence_level="hoch",
            ),
        ]
        candidate = AdversarialCandidate(
            produkt_id="KT-001",
            produkt_name="Prestige 51 EI30",
            adjusted_confidence=0.92,
            dimension_scores=cot_list,
            reasoning_summary="Guter Match insgesamt.",
        )
        assert candidate.adjusted_confidence == 0.92
        assert len(candidate.dimension_scores) == 1


class TestAdversarialResult:
    def test_full_construction(self):
        """AdversarialResult can be constructed with all required fields."""
        result = AdversarialResult(
            positions_nr="1.01",
            validation_status=ValidationStatus.BESTAETIGT,
            adjusted_confidence=0.96,
            bester_match=AdversarialCandidate(
                produkt_id="KT-001",
                produkt_name="Prestige 51 EI30",
                adjusted_confidence=0.96,
                dimension_scores=[
                    DimensionCoT(
                        dimension="Masse",
                        score=0.95,
                        reasoning="Passt perfekt.",
                        confidence_level="hoch",
                    ),
                ],
                reasoning_summary="Sehr guter Match.",
            ),
            debate=[
                CandidateDebate(
                    produkt_id="KT-001",
                    produkt_name="Prestige 51 EI30",
                    for_argument="Passt in allen Dimensionen.",
                    against_argument="Keine wesentlichen Maengel.",
                    for_confidence=0.96,
                    against_confidence=0.94,
                ),
            ],
            resolution_reasoning="FOR ueberzeugender als AGAINST.",
            per_dimension_cot=[
                DimensionCoT(
                    dimension="Masse",
                    score=0.95,
                    reasoning="Passt perfekt.",
                    confidence_level="hoch",
                ),
            ],
        )
        assert result.positions_nr == "1.01"
        assert result.validation_status == ValidationStatus.BESTAETIGT
        assert result.adjusted_confidence == 0.96
        assert result.bester_match is not None
        assert len(result.debate) == 1
        assert len(result.per_dimension_cot) == 1

    def test_alternative_candidates_default_empty(self):
        """alternative_candidates defaults to empty list."""
        result = AdversarialResult(
            positions_nr="1.01",
            validation_status=ValidationStatus.UNSICHER,
            adjusted_confidence=0.80,
            debate=[],
            resolution_reasoning="Keine klare Zuordnung.",
            per_dimension_cot=[],
        )
        assert result.alternative_candidates == []

    def test_triple_check_used_default_false(self):
        """triple_check_used defaults to False."""
        result = AdversarialResult(
            positions_nr="1.01",
            validation_status=ValidationStatus.UNSICHER,
            adjusted_confidence=0.80,
            debate=[],
            resolution_reasoning="Test.",
            per_dimension_cot=[],
        )
        assert result.triple_check_used is False

    def test_api_calls_count_default_2(self):
        """api_calls_count defaults to 2."""
        result = AdversarialResult(
            positions_nr="1.01",
            validation_status=ValidationStatus.BESTAETIGT,
            adjusted_confidence=0.96,
            debate=[],
            resolution_reasoning="Test.",
            per_dimension_cot=[],
        )
        assert result.api_calls_count == 2


class TestForArgument:
    def test_for_argument_construction(self):
        """ForArgument model for structured Opus output."""
        fa = ForArgument(
            produkt_id="KT-001",
            produkt_name="Prestige 51 EI30",
            for_konfidenz=0.92,
            dimension_bewertungen=[
                ForDimensionBewertung(
                    dimension="Masse",
                    score=0.95,
                    begruendung="Masse passt.",
                ),
            ],
            zusammenfassung="Guter Match.",
        )
        assert fa.for_konfidenz == 0.92
        assert len(fa.dimension_bewertungen) == 1


class TestAgainstArgument:
    def test_against_argument_construction(self):
        """AgainstArgument model for structured Opus output."""
        aa = AgainstArgument(
            produkt_id="KT-001",
            produkt_name="Prestige 51 EI30",
            against_konfidenz=0.75,
            dimension_bewertungen=[
                AgainstDimensionBewertung(
                    dimension="Brandschutz",
                    score=0.60,
                    begruendung="Nur EI30, gefordert EI60.",
                ),
            ],
            zusammenfassung="Brandschutz nicht ausreichend.",
        )
        assert aa.against_konfidenz == 0.75
        assert aa.dimension_bewertungen[0].score == 0.60


# ---------------------------------------------------------------------------
# Task 2: Adversarial Debate Engine Tests
# ---------------------------------------------------------------------------

from v2.schemas.matching import (
    MatchResult,
    MatchCandidate,
    DimensionScore,
    MatchDimension,
)


def _make_dimension_scores(base_score: float = 0.85) -> list[DimensionScore]:
    """Create a full set of 6 DimensionScores for testing."""
    return [
        DimensionScore(dimension=MatchDimension.MASSE, score=base_score, begruendung="Masse ok"),
        DimensionScore(dimension=MatchDimension.BRANDSCHUTZ, score=base_score, begruendung="Brandschutz ok"),
        DimensionScore(dimension=MatchDimension.SCHALLSCHUTZ, score=base_score, begruendung="Schallschutz ok"),
        DimensionScore(dimension=MatchDimension.MATERIAL, score=base_score, begruendung="Material ok"),
        DimensionScore(dimension=MatchDimension.ZERTIFIZIERUNG, score=base_score, begruendung="Zertifizierung ok"),
        DimensionScore(dimension=MatchDimension.LEISTUNG, score=base_score, begruendung="Leistung ok"),
    ]


def _make_test_match_result(
    gesamt_konfidenz: float = 0.88,
    num_alternatives: int = 2,
) -> MatchResult:
    """Create a MatchResult for adversarial testing."""
    bester = MatchCandidate(
        produkt_id="KT-001",
        produkt_name="Prestige 51 EI30",
        gesamt_konfidenz=gesamt_konfidenz,
        dimension_scores=_make_dimension_scores(),
        begruendung="Best match overall",
    )
    alternatives = [
        MatchCandidate(
            produkt_id=f"KT-{i + 2:03d}",
            produkt_name=f"Alternative {i + 1}",
            gesamt_konfidenz=gesamt_konfidenz - 0.05 * (i + 1),
            dimension_scores=_make_dimension_scores(),
            begruendung=f"Alternative {i + 1}",
        )
        for i in range(num_alternatives)
    ]
    return MatchResult(
        positions_nr="1.01",
        bester_match=bester,
        alternative_matches=alternatives,
        hat_match=True,
        match_methode="tfidf_ai",
    )


def _make_mock_for_response(
    konfidenz: float = 0.92,
    dim_scores: dict[str, float] | None = None,
) -> ForArgument:
    """Create a mock ForArgument as if returned by Opus."""
    default_scores = {
        "Masse": 0.95, "Brandschutz": 0.90, "Schallschutz": 0.85,
        "Material": 0.90, "Zertifizierung": 0.88, "Leistung": 0.90,
    }
    scores = dim_scores or default_scores
    return ForArgument(
        produkt_id="KT-001",
        produkt_name="Prestige 51 EI30",
        for_konfidenz=konfidenz,
        dimension_bewertungen=[
            ForDimensionBewertung(dimension=d, score=s, begruendung=f"{d} passt.")
            for d, s in scores.items()
        ],
        zusammenfassung="Guter Match in allen Dimensionen.",
    )


def _make_mock_against_response(
    konfidenz: float = 0.30,
    dim_scores: dict[str, float] | None = None,
) -> AgainstArgument:
    """Create a mock AgainstArgument as if returned by Opus."""
    default_scores = {
        "Masse": 0.95, "Brandschutz": 0.90, "Schallschutz": 0.80,
        "Material": 0.85, "Zertifizierung": 0.85, "Leistung": 0.88,
    }
    scores = dim_scores or default_scores
    return AgainstArgument(
        produkt_id="KT-001",
        produkt_name="Prestige 51 EI30",
        against_konfidenz=konfidenz,
        dimension_bewertungen=[
            AgainstDimensionBewertung(dimension=d, score=s, begruendung=f"{d} ok.")
            for d, s in scores.items()
        ],
        zusammenfassung="Keine wesentlichen Maengel gefunden.",
    )


def _make_mock_opus_client(
    for_konfidenz: float = 0.92,
    against_konfidenz: float = 0.30,
    for_dim_scores: dict[str, float] | None = None,
    against_dim_scores: dict[str, float] | None = None,
):
    """Create a mock Anthropic client that returns FOR/AGAINST responses.

    First call returns FOR, second call returns AGAINST.
    """
    for_response = MagicMock()
    for_response.parsed = _make_mock_for_response(for_konfidenz, for_dim_scores)

    against_response = MagicMock()
    against_response.parsed = _make_mock_against_response(against_konfidenz, against_dim_scores)

    mock_client = MagicMock()
    mock_client.messages = MagicMock()
    # First call = FOR, second call = AGAINST (per candidate)
    mock_client.messages.parse = MagicMock(
        side_effect=[for_response, against_response] * 10  # enough for multiple candidates
    )
    return mock_client


class TestAdversarialPrompts:
    def test_for_system_prompt_exists(self):
        """FOR_SYSTEM_PROMPT is defined and references key concepts."""
        from v2.matching.adversarial_prompts import FOR_SYSTEM_PROMPT
        assert "FUER" in FOR_SYSTEM_PROMPT or "fuer" in FOR_SYSTEM_PROMPT.lower()
        assert "Brandschutz" in FOR_SYSTEM_PROMPT
        assert "Masse" in FOR_SYSTEM_PROMPT

    def test_against_system_prompt_exists(self):
        """AGAINST_SYSTEM_PROMPT is defined and references safety-critical dimensions."""
        from v2.matching.adversarial_prompts import AGAINST_SYSTEM_PROMPT
        assert "widerlegen" in AGAINST_SYSTEM_PROMPT or "GEGEN" in AGAINST_SYSTEM_PROMPT or "AGAINST" in AGAINST_SYSTEM_PROMPT or "kritisch" in AGAINST_SYSTEM_PROMPT.lower()
        assert "Brandschutz" in AGAINST_SYSTEM_PROMPT
        assert "Leistung" in AGAINST_SYSTEM_PROMPT or "Oberflaeche" in AGAINST_SYSTEM_PROMPT

    def test_for_user_template_has_placeholders(self):
        """FOR_USER_TEMPLATE has anforderung and kandidaten placeholders."""
        from v2.matching.adversarial_prompts import FOR_USER_TEMPLATE
        assert "{anforderung}" in FOR_USER_TEMPLATE
        assert "{kandidaten}" in FOR_USER_TEMPLATE

    def test_against_user_template_has_placeholders(self):
        """AGAINST_USER_TEMPLATE has anforderung and kandidaten placeholders."""
        from v2.matching.adversarial_prompts import AGAINST_USER_TEMPLATE
        assert "{anforderung}" in AGAINST_USER_TEMPLATE
        assert "{kandidaten}" in AGAINST_USER_TEMPLATE

    def test_resolution_prompt_exists(self):
        """RESOLUTION_PROMPT references domain knowledge."""
        from v2.matching.adversarial_prompts import RESOLUTION_PROMPT
        assert "Brandschutz" in RESOLUTION_PROMPT


class TestValidateSinglePosition:
    @pytest.mark.asyncio
    async def test_returns_adversarial_result(self):
        """validate_single_position returns AdversarialResult with debate."""
        from v2.matching.adversarial import validate_single_position

        mock_client = _make_mock_opus_client(for_konfidenz=0.92, against_konfidenz=0.25)
        match_result = _make_test_match_result(gesamt_konfidenz=0.88, num_alternatives=2)
        semaphore = asyncio.Semaphore(3)

        result = await validate_single_position(
            client=mock_client,
            match_result=match_result,
            semaphore=semaphore,
        )

        assert isinstance(result, AdversarialResult)
        assert result.positions_nr == "1.01"

    @pytest.mark.asyncio
    async def test_debate_for_best_match_and_alternatives(self):
        """Debate covers best match AND up to 3 alternatives."""
        from v2.matching.adversarial import validate_single_position

        mock_client = _make_mock_opus_client()
        match_result = _make_test_match_result(num_alternatives=3)
        semaphore = asyncio.Semaphore(3)

        result = await validate_single_position(
            client=mock_client,
            match_result=match_result,
            semaphore=semaphore,
        )

        # Should have debate entries for best + up to 3 alternatives
        assert len(result.debate) >= 1
        # Best match should always be debated
        best_ids = [d.produkt_id for d in result.debate]
        assert "KT-001" in best_ids

    @pytest.mark.asyncio
    async def test_for_and_against_both_present(self):
        """FOR and AGAINST arguments are both present for each debated candidate."""
        from v2.matching.adversarial import validate_single_position

        mock_client = _make_mock_opus_client()
        match_result = _make_test_match_result(num_alternatives=1)
        semaphore = asyncio.Semaphore(3)

        result = await validate_single_position(
            client=mock_client,
            match_result=match_result,
            semaphore=semaphore,
        )

        for debate in result.debate:
            assert debate.for_argument != ""
            assert debate.against_argument != ""
            assert debate.for_confidence > 0
            assert debate.against_confidence >= 0

    @pytest.mark.asyncio
    async def test_bestaetigt_when_high_confidence(self):
        """validation_status=bestaetigt when adjusted_confidence >= 0.95."""
        from v2.matching.adversarial import validate_single_position

        # Both FOR and AGAINST agree: all scores very high -> adjusted >= 0.95
        high_scores = {
            "Masse": 0.98, "Brandschutz": 0.97, "Schallschutz": 0.96,
            "Material": 0.97, "Zertifizierung": 0.96, "Leistung": 0.98,
        }
        mock_client = _make_mock_opus_client(
            for_konfidenz=0.98,
            against_konfidenz=0.05,
            for_dim_scores=high_scores,
            against_dim_scores=high_scores,
        )
        match_result = _make_test_match_result(gesamt_konfidenz=0.97)
        semaphore = asyncio.Semaphore(3)

        result = await validate_single_position(
            client=mock_client,
            match_result=match_result,
            semaphore=semaphore,
        )

        assert result.adjusted_confidence >= 0.95
        assert result.validation_status == ValidationStatus.BESTAETIGT

    @pytest.mark.asyncio
    async def test_unsicher_when_low_confidence(self):
        """validation_status=unsicher when adjusted_confidence < 0.95."""
        from v2.matching.adversarial import validate_single_position

        # Low dimension scores -> adjusted well below 0.95
        low_scores = {
            "Masse": 0.70, "Brandschutz": 0.60, "Schallschutz": 0.55,
            "Material": 0.65, "Zertifizierung": 0.60, "Leistung": 0.70,
        }
        mock_client = _make_mock_opus_client(
            for_konfidenz=0.65,
            against_konfidenz=0.70,
            for_dim_scores=low_scores,
            against_dim_scores=low_scores,
        )
        match_result = _make_test_match_result(gesamt_konfidenz=0.65)
        semaphore = asyncio.Semaphore(3)

        result = await validate_single_position(
            client=mock_client,
            match_result=match_result,
            semaphore=semaphore,
        )

        assert result.adjusted_confidence < 0.95
        assert result.validation_status == ValidationStatus.UNSICHER

    @pytest.mark.asyncio
    async def test_per_dimension_cot_present(self):
        """per_dimension_cot contains entries for dimensions."""
        from v2.matching.adversarial import validate_single_position

        mock_client = _make_mock_opus_client()
        match_result = _make_test_match_result()
        semaphore = asyncio.Semaphore(3)

        result = await validate_single_position(
            client=mock_client,
            match_result=match_result,
            semaphore=semaphore,
        )

        assert len(result.per_dimension_cot) == 6  # 6 dimensions

    @pytest.mark.asyncio
    async def test_adaptive_verbosity(self):
        """Adaptive verbosity: hoch for score > 0.9, niedrig for score <= 0.9."""
        from v2.matching.adversarial import validate_single_position

        mock_client = _make_mock_opus_client()
        match_result = _make_test_match_result()
        semaphore = asyncio.Semaphore(3)

        result = await validate_single_position(
            client=mock_client,
            match_result=match_result,
            semaphore=semaphore,
        )

        for cot in result.per_dimension_cot:
            if cot.score > 0.9:
                assert cot.confidence_level == "hoch"
            else:
                assert cot.confidence_level == "niedrig"

    @pytest.mark.asyncio
    async def test_api_calls_count_is_2(self):
        """api_calls_count is 2 for standard debate (FOR + AGAINST)."""
        from v2.matching.adversarial import validate_single_position

        mock_client = _make_mock_opus_client()
        match_result = _make_test_match_result(num_alternatives=0)
        semaphore = asyncio.Semaphore(3)

        result = await validate_single_position(
            client=mock_client,
            match_result=match_result,
            semaphore=semaphore,
        )

        # 1 candidate (best only) * 2 calls = 2
        assert result.api_calls_count == 2


class TestValidatePositions:
    @pytest.mark.asyncio
    async def test_concurrent_processing(self):
        """validate_positions processes multiple positions concurrently with semaphore."""
        from v2.matching.adversarial import validate_positions

        mock_client = _make_mock_opus_client()
        match_results = [
            _make_test_match_result(gesamt_konfidenz=0.88 + i * 0.01)
            for i in range(3)
        ]
        # Give each a different positions_nr
        for i, mr in enumerate(match_results):
            mr.positions_nr = f"{i + 1}.01"

        results = await validate_positions(
            client=mock_client,
            match_results=match_results,
        )

        assert len(results) == 3
        for r in results:
            assert isinstance(r, AdversarialResult)
        # Check different position numbers preserved
        pos_nrs = {r.positions_nr for r in results}
        assert pos_nrs == {"1.01", "2.01", "3.01"}
