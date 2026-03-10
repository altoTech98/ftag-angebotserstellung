"""
Cross-document conflict detector.

Detects fields with different non-None values across matched positions,
classifies severity deterministically, and resolves via AI.
"""

import logging
from typing import Optional

from v2.extraction.cross_doc_matcher import _classify_severity
from v2.schemas.common import FieldSource
from v2.schemas.extraction import (
    ConflictSeverity,
    CrossDocMatch,
    ExtractedDoorPosition,
    FieldConflict,
)

logger = logging.getLogger(__name__)

# Fields to skip during conflict detection
_SKIP_FIELDS = {"quellen", "positions_nr", "anzahl", "bemerkungen"}


def _get_comparable_value(val) -> Optional[str]:
    """Convert a field value to a comparable string."""
    if val is None:
        return None
    if isinstance(val, bool):
        return str(val).lower()
    if hasattr(val, "value"):  # Enum
        return val.value
    return str(val)


def _resolve_conflicts_with_ai(
    raw_conflicts: list[dict],
    client,
) -> list[FieldConflict]:
    """Resolve conflicts using AI.

    This is the AI integration point. When client is None or AI fails,
    falls back to rule-based resolution (higher confidence wins).
    """
    resolved = []
    for rc in raw_conflicts:
        # Default: higher confidence wins
        conf_a = rc["quelle_a"].konfidenz if rc["quelle_a"] else 0.5
        conf_b = rc["quelle_b"].konfidenz if rc["quelle_b"] else 0.5

        if conf_b >= conf_a:
            resolution = rc["wert_b"]
            reason = f"Quelle B ({rc['quelle_b'].dokument}) hat hoehere Konfidenz ({conf_b:.2f} vs {conf_a:.2f})"
        else:
            resolution = rc["wert_a"]
            reason = f"Quelle A ({rc['quelle_a'].dokument}) hat hoehere Konfidenz ({conf_a:.2f} vs {conf_b:.2f})"

        resolved.append(FieldConflict(
            positions_nr=rc["positions_nr"],
            field_name=rc["field_name"],
            wert_a=rc["wert_a"],
            quelle_a=rc["quelle_a"],
            wert_b=rc["wert_b"],
            quelle_b=rc["quelle_b"],
            severity=rc["severity"],
            resolution=resolution,
            resolution_reason=reason,
            resolved_by="rule",
        ))

    return resolved


def detect_and_resolve_conflicts(
    matches: list[CrossDocMatch],
    all_positions: list[ExtractedDoorPosition],
    client=None,
) -> list[FieldConflict]:
    """Detect and resolve cross-document field conflicts.

    For each auto_merge match, compares all fields between matched positions.
    Fields with different non-None values are flagged as conflicts.
    Severity is classified deterministically. Resolution via AI (or rule fallback).

    Args:
        matches: Cross-document position matches.
        all_positions: Flat list of all positions.
        client: Optional Anthropic client for AI resolution.

    Returns:
        List of detected and resolved FieldConflict objects.
    """
    raw_conflicts: list[dict] = []

    for match in matches:
        if not match.auto_merge:
            continue

        idx_a = match.position_a_index
        idx_b = match.position_b_index

        if idx_a >= len(all_positions) or idx_b >= len(all_positions):
            continue

        pos_a = all_positions[idx_a]
        pos_b = all_positions[idx_b]

        # Compare all fields
        for field_name in pos_a.model_fields:
            if field_name in _SKIP_FIELDS:
                continue

            val_a = _get_comparable_value(getattr(pos_a, field_name))
            val_b = _get_comparable_value(getattr(pos_b, field_name))

            # Skip if either is None (that's enrichment, not conflict)
            if val_a is None or val_b is None:
                continue

            # Skip if same value
            if val_a == val_b:
                continue

            # Conflict detected
            severity = _classify_severity(field_name)
            source_a = pos_a.quellen.get(
                field_name,
                FieldSource(dokument="unknown", konfidenz=0.5),
            )
            source_b = pos_b.quellen.get(
                field_name,
                FieldSource(dokument="unknown", konfidenz=0.5),
            )

            raw_conflicts.append({
                "positions_nr": pos_a.positions_nr,
                "field_name": field_name,
                "wert_a": val_a,
                "quelle_a": source_a,
                "wert_b": val_b,
                "quelle_b": source_b,
                "severity": severity,
            })

    if not raw_conflicts:
        return []

    logger.info(
        f"Conflict detection: {len(raw_conflicts)} conflicts found "
        f"({sum(1 for c in raw_conflicts if c['severity'] == ConflictSeverity.CRITICAL)} critical, "
        f"{sum(1 for c in raw_conflicts if c['severity'] == ConflictSeverity.MAJOR)} major, "
        f"{sum(1 for c in raw_conflicts if c['severity'] == ConflictSeverity.MINOR)} minor)"
    )

    # Resolve conflicts
    resolved = _resolve_conflicts_with_ai(raw_conflicts, client)

    return resolved
