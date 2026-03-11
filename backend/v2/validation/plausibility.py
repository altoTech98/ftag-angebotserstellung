"""
Plausibility Checker - validates matching results for quality issues.

Detects uncovered positions, duplicates, suspicious patterns (all-match,
no-match, identical confidences) with size-aware thresholds.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class IssueSeverity(str, Enum):
    """Severity levels for plausibility issues."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class PlausibilityIssue(BaseModel):
    """A single plausibility issue found during validation."""

    code: str = Field(description="Issue code e.g. UNCOVERED_POSITIONS")
    severity: IssueSeverity = Field(description="Issue severity level")
    message: str = Field(description="Human-readable description of the issue")
    details: dict = Field(default_factory=dict, description="Additional issue details")


class PlausibilityResult(BaseModel):
    """Result of plausibility validation."""

    passed: bool = Field(description="True if no ERROR-level issues found")
    issues: list[PlausibilityIssue] = Field(
        default_factory=list, description="All detected issues"
    )
    positions_total: int = Field(description="Total number of positions")
    positions_matched: int = Field(description="Number of positions with matches")
    positions_unmatched: int = Field(description="Number of positions without matches")
    duplicate_positions: list[str] = Field(
        default_factory=list, description="Position numbers that appear more than once"
    )


def check_plausibility(
    positions: list,
    match_results: list,
    adversarial_results: list,
    gap_reports: list | None = None,
) -> PlausibilityResult:
    """Run plausibility checks on pipeline results.

    Args:
        positions: List of ExtractedDoorPosition (or duck-typed with positions_nr).
        match_results: List of MatchResult (or duck-typed with positions_nr, hat_match, bester_match).
        adversarial_results: List of AdversarialResult (or duck-typed).
        gap_reports: Optional list of gap reports.

    Returns:
        PlausibilityResult with all detected issues.
    """
    issues: list[PlausibilityIssue] = []
    total = len(positions)

    # Build lookup sets
    position_nrs = [p.positions_nr for p in positions]
    matched_nrs = {m.positions_nr for m in match_results}

    # Count matched vs unmatched
    matches_with_hit = [m for m in match_results if m.hat_match]
    matched_count = len(matches_with_hit)
    unmatched_count = total - matched_count

    # ---- Check 1: UNCOVERED_POSITIONS (ERROR) ----
    uncovered = [nr for nr in position_nrs if nr not in matched_nrs]
    if uncovered:
        issues.append(
            PlausibilityIssue(
                code="UNCOVERED_POSITIONS",
                severity=IssueSeverity.ERROR,
                message=f"{len(uncovered)} Position(en) ohne Matching-Ergebnis: {', '.join(uncovered[:10])}",
                details={"uncovered": uncovered},
            )
        )
        # Adjust unmatched to include uncovered
        unmatched_count = total - matched_count

    # ---- Check 2: DUPLICATE_POSITIONS (WARNING) ----
    seen: dict[str, int] = {}
    for nr in position_nrs:
        seen[nr] = seen.get(nr, 0) + 1
    duplicates = [nr for nr, count in seen.items() if count > 1]
    if duplicates:
        issues.append(
            PlausibilityIssue(
                code="DUPLICATE_POSITIONS",
                severity=IssueSeverity.WARNING,
                message=f"Doppelte Positionsnummern gefunden: {', '.join(duplicates)}",
                details={"duplicates": duplicates},
            )
        )

    # ---- Check 3: ALL_MATCHED (WARNING, only >10 positions) ----
    if total > 10 and matched_count == total and len(match_results) == total:
        issues.append(
            PlausibilityIssue(
                code="ALL_MATCHED",
                severity=IssueSeverity.WARNING,
                message=f"Alle {total} Positionen haben ein Match - bei grossen Ausschreibungen ungewoehnlich",
                details={"total": total, "matched": matched_count},
            )
        )

    # ---- Check 4: NONE_MATCHED (WARNING, only >10 positions) ----
    if total > 10 and matched_count == 0 and len(match_results) == total:
        issues.append(
            PlausibilityIssue(
                code="NONE_MATCHED",
                severity=IssueSeverity.WARNING,
                message=f"Keine der {total} Positionen hat ein Match - moeglicherweise falscher Produktkatalog",
                details={"total": total},
            )
        )

    # ---- Check 5: IDENTICAL_CONFIDENCES (WARNING, only >5 matched positions) ----
    confidences = []
    for m in match_results:
        if m.hat_match and m.bester_match is not None:
            confidences.append(m.bester_match.gesamt_konfidenz)
    if len(confidences) > 5 and len(set(confidences)) == 1:
        issues.append(
            PlausibilityIssue(
                code="IDENTICAL_CONFIDENCES",
                severity=IssueSeverity.WARNING,
                message=f"Alle {len(confidences)} Konfidenzwerte sind identisch ({confidences[0]}) - moeglicherweise fehlerhaftes Matching",
                details={"value": confidences[0], "count": len(confidences)},
            )
        )

    # Determine pass/fail: passed = no ERROR-level issues
    has_errors = any(i.severity == IssueSeverity.ERROR for i in issues)

    return PlausibilityResult(
        passed=not has_errors,
        issues=issues,
        positions_total=total,
        positions_matched=matched_count,
        positions_unmatched=unmatched_count,
        duplicate_positions=duplicates,
    )
