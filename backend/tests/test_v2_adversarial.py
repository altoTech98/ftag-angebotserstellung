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
