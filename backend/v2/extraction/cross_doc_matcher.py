"""
Cross-document position matcher.

Matches door positions across multiple documents using tiered confidence:
- Tier 1: Exact positions_nr match (confidence 1.0, auto-merge)
- Tier 2: Normalized ID match (confidence 0.92, auto-merge)
- Tier 3: Room+floor+type fallback (confidence 0.7, flagged for review)

Separate from Phase 2's intra-doc dedup (different matching criteria).
"""

import logging
import re
from itertools import combinations
from typing import Optional

from v2.schemas.extraction import (
    ConflictSeverity,
    CrossDocMatch,
    ExtractedDoorPosition,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Field classification for conflict severity
# ---------------------------------------------------------------------------

SAFETY_FIELDS: set[str] = {
    "brandschutz_klasse",
    "brandschutz_freitext",
    "rauchschutz",
    "rauchschutz_freitext",
    "einbruchschutz_klasse",
}

MAJOR_FIELDS: set[str] = {
    "breite_mm",
    "hoehe_mm",
    "wandstaerke_mm",
    "falzmass_breite_mm",
    "falzmass_hoehe_mm",
    "lichtmass_breite_mm",
    "lichtmass_hoehe_mm",
    "tuerblatt_staerke_mm",
    "material_blatt",
    "material_blatt_freitext",
    "material_zarge",
    "material_zarge_freitext",
    "schallschutz_klasse",
    "schallschutz_db",
    "schallschutz_freitext",
    "oeffnungsart",
    "oeffnungsart_freitext",
    "anzahl_fluegel",
    "anschlag_richtung",
    "glasausschnitt",
    "glasart",
    "glasgroesse",
    "tuerblatt_ausfuehrung",
    "drueckergarnitur",
    "schlossart",
    "schliesszylinder",
    "tuerband",
    "tuerschliesser",
    "tuerstopper",
    "bodendichtung",
    "obentuerband",
    "klimaklasse",
    "nassraumeignung",
    "barrierefreiheit",
    "ce_kennzeichnung",
    "strahlenschutz",
    "hygieneschutz",
    "beschusshemmend",
    "seitenteil",
    "oberlicht",
}

# Regex pattern for stripping known Swiss tender ID prefixes
_PREFIX_PATTERN = re.compile(
    r"^(?:Tuer|Tür|Pos\.?|Element|T-|Nr\.?|E)\s*",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Public helpers (exported for testing)
# ---------------------------------------------------------------------------


def _normalize_position_id(id_str: str) -> str:
    """Normalize a position ID by stripping known prefixes.

    Examples:
        "Tuer 1.01" -> "1.01"
        "Pos. 1.01" -> "1.01"
        "Element 1.01" -> "1.01"
        "T-1.01" -> "1.01"
        "Nr. 1.01" -> "1.01"
    """
    normalized = _PREFIX_PATTERN.sub("", id_str.strip())
    return normalized.strip()


def _classify_severity(field_name: str) -> ConflictSeverity:
    """Classify a field's conflict severity deterministically.

    CRITICAL: Safety fields (fire, smoke, burglary protection)
    MAJOR: Spec fields (dimensions, material, sound, hardware)
    MINOR: Everything else (color, surface, remarks)
    """
    if field_name in SAFETY_FIELDS:
        return ConflictSeverity.CRITICAL
    if field_name in MAJOR_FIELDS:
        return ConflictSeverity.MAJOR
    return ConflictSeverity.MINOR


# ---------------------------------------------------------------------------
# Main matching function
# ---------------------------------------------------------------------------


def match_positions_across_docs(
    positions_by_doc: dict[str, list[ExtractedDoorPosition]],
) -> list[CrossDocMatch]:
    """Match positions across documents using tiered confidence.

    For each pair of documents, compares all positions using:
    - Tier 1: Exact positions_nr match -> confidence 1.0, auto_merge=True
    - Tier 2: Normalized ID match -> confidence 0.92, auto_merge=True
    - Tier 3: Room+floor match -> confidence 0.7, auto_merge=False

    Args:
        positions_by_doc: Mapping of document name to list of positions.

    Returns:
        List of CrossDocMatch objects describing matched position pairs.
        Indices reference a flat list: all positions concatenated in doc order.
    """
    if len(positions_by_doc) < 2:
        return []

    # Build flat position list with doc-to-offset mapping
    doc_names = list(positions_by_doc.keys())
    doc_offsets: dict[str, int] = {}
    offset = 0
    for doc_name in doc_names:
        doc_offsets[doc_name] = offset
        offset += len(positions_by_doc[doc_name])

    matches: list[CrossDocMatch] = []
    matched_pairs: set[tuple[int, int]] = set()  # Avoid duplicate matches

    # Compare each document pair
    for doc_a, doc_b in combinations(doc_names, 2):
        offset_a = doc_offsets[doc_a]
        offset_b = doc_offsets[doc_b]
        positions_a = positions_by_doc[doc_a]
        positions_b = positions_by_doc[doc_b]

        # Track which positions in B have been matched (prevent 1:N)
        matched_b_indices: set[int] = set()

        # Tier 1: Exact positions_nr match
        for i, pos_a in enumerate(positions_a):
            for j, pos_b in enumerate(positions_b):
                if j in matched_b_indices:
                    continue
                if pos_a.positions_nr == pos_b.positions_nr:
                    global_a = offset_a + i
                    global_b = offset_b + j
                    pair = (min(global_a, global_b), max(global_a, global_b))
                    if pair not in matched_pairs:
                        matches.append(CrossDocMatch(
                            position_a_index=global_a,
                            position_b_index=global_b,
                            confidence=1.0,
                            match_method="exact_id",
                            auto_merge=True,
                        ))
                        matched_pairs.add(pair)
                        matched_b_indices.add(j)
                    break  # Each A matches at most one B per tier

        # Tier 2: Normalized ID match
        for i, pos_a in enumerate(positions_a):
            global_a = offset_a + i
            # Skip if already matched
            if any(global_a in (p[0], p[1]) for p in matched_pairs):
                continue
            norm_a = _normalize_position_id(pos_a.positions_nr)

            for j, pos_b in enumerate(positions_b):
                if j in matched_b_indices:
                    continue
                global_b = offset_b + j
                if any(global_b in (p[0], p[1]) for p in matched_pairs):
                    continue

                norm_b = _normalize_position_id(pos_b.positions_nr)
                if norm_a == norm_b and norm_a:
                    pair = (min(global_a, global_b), max(global_a, global_b))
                    if pair not in matched_pairs:
                        matches.append(CrossDocMatch(
                            position_a_index=global_a,
                            position_b_index=global_b,
                            confidence=0.92,
                            match_method="normalized_id",
                            auto_merge=True,
                        ))
                        matched_pairs.add(pair)
                        matched_b_indices.add(j)
                    break

        # Tier 3: Room + floor + type match (lower confidence, no auto-merge)
        for i, pos_a in enumerate(positions_a):
            global_a = offset_a + i
            if any(global_a in (p[0], p[1]) for p in matched_pairs):
                continue

            if not pos_a.raum_nr or not pos_a.geschoss:
                continue

            for j, pos_b in enumerate(positions_b):
                if j in matched_b_indices:
                    continue
                global_b = offset_b + j
                if any(global_b in (p[0], p[1]) for p in matched_pairs):
                    continue

                if (
                    pos_b.raum_nr
                    and pos_b.geschoss
                    and pos_a.raum_nr == pos_b.raum_nr
                    and pos_a.geschoss == pos_b.geschoss
                ):
                    pair = (min(global_a, global_b), max(global_a, global_b))
                    if pair not in matched_pairs:
                        matches.append(CrossDocMatch(
                            position_a_index=global_a,
                            position_b_index=global_b,
                            confidence=0.7,
                            match_method="room_floor_type",
                            auto_merge=False,
                        ))
                        matched_pairs.add(pair)
                        matched_b_indices.add(j)
                    break

    logger.info(
        f"Cross-doc matching: {len(matches)} matches found across "
        f"{len(positions_by_doc)} documents"
    )
    return matches
