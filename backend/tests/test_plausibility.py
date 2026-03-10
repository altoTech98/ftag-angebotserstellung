"""
Tests for PlausibilityChecker - validates matching results for quality issues.
"""

import pytest
from unittest.mock import MagicMock

from v2.validation.plausibility import (
    check_plausibility,
    PlausibilityResult,
    PlausibilityIssue,
    IssueSeverity,
)


# ---------------------------------------------------------------------------
# Helpers to build mock objects matching schema shapes
# ---------------------------------------------------------------------------


def _position(nr: str):
    """Create a mock ExtractedDoorPosition."""
    p = MagicMock()
    p.positions_nr = nr
    return p


def _match(nr: str, hat_match: bool = True, konfidenz: float = 0.85):
    """Create a mock MatchResult."""
    m = MagicMock()
    m.positions_nr = nr
    m.hat_match = hat_match
    if hat_match:
        best = MagicMock()
        best.gesamt_konfidenz = konfidenz
        m.bester_match = best
    else:
        m.bester_match = None
    return m


def _adversarial(nr: str, status: str = "bestaetigt", confidence: float = 0.9):
    """Create a mock AdversarialResult."""
    a = MagicMock()
    a.positions_nr = nr
    a.validation_status = status
    a.adjusted_confidence = confidence
    return a


# ---------------------------------------------------------------------------
# Test: UNCOVERED_POSITIONS
# ---------------------------------------------------------------------------


class TestUncoveredPositions:
    def test_uncovered_positions_detected(self):
        """Positions without match results produce ERROR-level issue."""
        positions = [_position("1.01"), _position("1.02"), _position("1.03")]
        matches = [_match("1.01")]  # Only 1 of 3 matched
        adversarial = [_adversarial("1.01")]

        result = check_plausibility(positions, matches, adversarial)

        assert result.passed is False
        codes = [i.code for i in result.issues]
        assert "UNCOVERED_POSITIONS" in codes
        issue = next(i for i in result.issues if i.code == "UNCOVERED_POSITIONS")
        assert issue.severity == IssueSeverity.ERROR
        assert result.positions_unmatched == 2


# ---------------------------------------------------------------------------
# Test: DUPLICATE_POSITIONS
# ---------------------------------------------------------------------------


class TestDuplicatePositions:
    def test_duplicate_positions_detected(self):
        """Duplicate position numbers produce WARNING-level issue."""
        positions = [_position("1.01"), _position("1.01"), _position("1.02")]
        matches = [_match("1.01"), _match("1.02")]
        adversarial = [_adversarial("1.01"), _adversarial("1.02")]

        result = check_plausibility(positions, matches, adversarial)

        codes = [i.code for i in result.issues]
        assert "DUPLICATE_POSITIONS" in codes
        issue = next(i for i in result.issues if i.code == "DUPLICATE_POSITIONS")
        assert issue.severity == IssueSeverity.WARNING
        assert "1.01" in result.duplicate_positions


# ---------------------------------------------------------------------------
# Test: ALL_MATCHED (size-aware)
# ---------------------------------------------------------------------------


class TestAllMatched:
    def test_all_matched_warning_for_large_tenders(self):
        """ALL_MATCHED flagged when >10 positions all matched."""
        nrs = [f"P{i}" for i in range(15)]
        positions = [_position(nr) for nr in nrs]
        matches = [_match(nr, hat_match=True) for nr in nrs]
        adversarial = [_adversarial(nr) for nr in nrs]

        result = check_plausibility(positions, matches, adversarial)

        codes = [i.code for i in result.issues]
        assert "ALL_MATCHED" in codes
        issue = next(i for i in result.issues if i.code == "ALL_MATCHED")
        assert issue.severity == IssueSeverity.WARNING

    def test_all_matched_not_flagged_for_small_tenders(self):
        """ALL_MATCHED NOT flagged when <=10 positions."""
        nrs = [f"P{i}" for i in range(5)]
        positions = [_position(nr) for nr in nrs]
        matches = [_match(nr, hat_match=True) for nr in nrs]
        adversarial = [_adversarial(nr) for nr in nrs]

        result = check_plausibility(positions, matches, adversarial)

        codes = [i.code for i in result.issues]
        assert "ALL_MATCHED" not in codes


# ---------------------------------------------------------------------------
# Test: NONE_MATCHED (size-aware)
# ---------------------------------------------------------------------------


class TestNoneMatched:
    def test_none_matched_warning_for_large_tenders(self):
        """NONE_MATCHED flagged when >10 positions none matched."""
        nrs = [f"P{i}" for i in range(15)]
        positions = [_position(nr) for nr in nrs]
        matches = [_match(nr, hat_match=False) for nr in nrs]
        adversarial = [_adversarial(nr, status="abgelehnt", confidence=0.0) for nr in nrs]

        result = check_plausibility(positions, matches, adversarial)

        codes = [i.code for i in result.issues]
        assert "NONE_MATCHED" in codes
        issue = next(i for i in result.issues if i.code == "NONE_MATCHED")
        assert issue.severity == IssueSeverity.WARNING

    def test_none_matched_not_flagged_for_small_tenders(self):
        """NONE_MATCHED NOT flagged when <=10 positions."""
        nrs = [f"P{i}" for i in range(5)]
        positions = [_position(nr) for nr in nrs]
        matches = [_match(nr, hat_match=False) for nr in nrs]
        adversarial = [_adversarial(nr, status="abgelehnt", confidence=0.0) for nr in nrs]

        result = check_plausibility(positions, matches, adversarial)

        codes = [i.code for i in result.issues]
        assert "NONE_MATCHED" not in codes


# ---------------------------------------------------------------------------
# Test: IDENTICAL_CONFIDENCES
# ---------------------------------------------------------------------------


class TestIdenticalConfidences:
    def test_identical_confidences_flagged(self):
        """IDENTICAL_CONFIDENCES flagged when all same value and >5 positions."""
        nrs = [f"P{i}" for i in range(8)]
        positions = [_position(nr) for nr in nrs]
        matches = [_match(nr, hat_match=True, konfidenz=0.85) for nr in nrs]
        adversarial = [_adversarial(nr) for nr in nrs]

        result = check_plausibility(positions, matches, adversarial)

        codes = [i.code for i in result.issues]
        assert "IDENTICAL_CONFIDENCES" in codes
        issue = next(i for i in result.issues if i.code == "IDENTICAL_CONFIDENCES")
        assert issue.severity == IssueSeverity.WARNING

    def test_identical_confidences_not_flagged_for_small(self):
        """IDENTICAL_CONFIDENCES NOT flagged when <=5 positions."""
        nrs = [f"P{i}" for i in range(3)]
        positions = [_position(nr) for nr in nrs]
        matches = [_match(nr, hat_match=True, konfidenz=0.85) for nr in nrs]
        adversarial = [_adversarial(nr) for nr in nrs]

        result = check_plausibility(positions, matches, adversarial)

        codes = [i.code for i in result.issues]
        assert "IDENTICAL_CONFIDENCES" not in codes


# ---------------------------------------------------------------------------
# Test: Healthy result set
# ---------------------------------------------------------------------------


class TestHealthyResults:
    def test_healthy_result_passes(self):
        """A normal healthy result set returns passed=True with no issues."""
        nrs = [f"P{i}" for i in range(5)]
        positions = [_position(nr) for nr in nrs]
        # Mix of match/no-match with varying confidences
        matches = [
            _match("P0", hat_match=True, konfidenz=0.92),
            _match("P1", hat_match=True, konfidenz=0.78),
            _match("P2", hat_match=False),
            _match("P3", hat_match=True, konfidenz=0.65),
            _match("P4", hat_match=True, konfidenz=0.88),
        ]
        adversarial = [_adversarial(nr) for nr in nrs]

        result = check_plausibility(positions, matches, adversarial)

        assert result.passed is True
        assert len(result.issues) == 0
        assert result.positions_total == 5
        assert result.positions_matched == 4
        assert result.positions_unmatched == 1
