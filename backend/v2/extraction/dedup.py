"""
Deduplication module for multi-pass extraction.

Merges door positions from different extraction passes with field-level
conflict resolution and provenance tracking. Later passes win conflicts.
"""

import json
import logging
from typing import Optional

from v2.schemas.common import FieldSource
from v2.schemas.extraction import ExtractedDoorPosition

logger = logging.getLogger(__name__)

# Fields to skip during merge iteration (not actual door properties)
_SKIP_FIELDS = {"quellen"}


def _merge_two_positions(
    existing: ExtractedDoorPosition,
    new: ExtractedDoorPosition,
    pass_priority: int,
) -> ExtractedDoorPosition:
    """Merge two positions with the same positions_nr.

    Later pass (higher pass_priority) wins field conflicts.
    Fields that are None in the new position but set in existing are preserved.
    Quellen dict is updated with the winning value's source.

    Args:
        existing: Position from earlier pass.
        new: Position from later pass.
        pass_priority: Priority of the new pass (higher = wins conflicts).

    Returns:
        Merged ExtractedDoorPosition.
    """
    merged_data = {}
    merged_quellen = dict(existing.quellen)

    # Get all fields from the model
    for field_name in existing.model_fields:
        if field_name in _SKIP_FIELDS:
            continue

        existing_val = getattr(existing, field_name)
        new_val = getattr(new, field_name)

        if new_val is not None and pass_priority >= 1:
            # New pass has a value -> it wins
            merged_data[field_name] = new_val
            # Update provenance if new position has source for this field
            if field_name in new.quellen:
                merged_quellen[field_name] = new.quellen[field_name]
        elif existing_val is not None:
            # Keep existing value (fill gap)
            merged_data[field_name] = existing_val
            # Keep existing provenance
        else:
            # Both None
            merged_data[field_name] = None

    merged_data["quellen"] = merged_quellen
    return ExtractedDoorPosition(**merged_data)


def merge_positions(
    existing: list[ExtractedDoorPosition],
    new_positions: list[ExtractedDoorPosition],
    pass_priority: int = 1,
) -> list[ExtractedDoorPosition]:
    """Merge new positions into existing ones with conflict resolution.

    Two-phase approach:
    1. Pre-filter: Exact positions_nr match -> direct merge (no AI needed)
    2. Remaining unmatched new positions are appended as-is

    Args:
        existing: Positions from earlier passes.
        new_positions: Positions from the current pass.
        pass_priority: Priority of new pass (higher = wins field conflicts).

    Returns:
        Merged list of ExtractedDoorPosition.
    """
    # Build lookup by positions_nr for existing positions
    existing_by_nr: dict[str, int] = {}
    result = list(existing)  # Copy existing list

    for idx, pos in enumerate(result):
        existing_by_nr[pos.positions_nr] = idx

    # Phase 1: Pre-filter - exact positions_nr match
    unmatched_new = []

    for new_pos in new_positions:
        if new_pos.positions_nr in existing_by_nr:
            idx = existing_by_nr[new_pos.positions_nr]
            result[idx] = _merge_two_positions(result[idx], new_pos, pass_priority)
        else:
            unmatched_new.append(new_pos)

    # Phase 2: Add unmatched new positions
    for new_pos in unmatched_new:
        result.append(new_pos)
        existing_by_nr[new_pos.positions_nr] = len(result) - 1

    return result


async def ai_dedup_cluster(
    positions: list[ExtractedDoorPosition],
    anthropic_client,
) -> list[list[int]]:
    """Use AI to cluster positions that represent the same door.

    Sends position summaries to Claude for clustering. Returns groups
    of indices that likely refer to the same physical door.

    Args:
        positions: List of positions to cluster.
        anthropic_client: Anthropic client for API calls.

    Returns:
        List of groups, each group is a list of position indices.
    """
    from v2.extraction.prompts import DEDUP_PROMPT_TEMPLATE

    if len(positions) <= 1:
        return [[i] for i in range(len(positions))]

    # Build position summaries
    summaries = []
    for i, pos in enumerate(positions):
        summary = {
            "index": i,
            "positions_nr": pos.positions_nr,
            "breite_mm": pos.breite_mm,
            "hoehe_mm": pos.hoehe_mm,
            "brandschutz_klasse": (
                pos.brandschutz_klasse.value if pos.brandschutz_klasse else None
            ),
            "material_blatt": (
                pos.material_blatt.value if pos.material_blatt else None
            ),
        }
        summaries.append(summary)

    prompt = DEDUP_PROMPT_TEMPLATE.format(
        positions_json=json.dumps(summaries, ensure_ascii=False, indent=2)
    )

    try:
        response = await anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )

        # Parse response - expect JSON array of arrays
        text = response.content[0].text
        # Find JSON in response
        start = text.find("[")
        end = text.rfind("]") + 1
        if start >= 0 and end > start:
            clusters = json.loads(text[start:end])
            if isinstance(clusters, list) and all(
                isinstance(c, list) for c in clusters
            ):
                return clusters

    except Exception as e:
        logger.warning(f"AI dedup clustering failed: {e}")

    # Fallback: each position is its own group
    return [[i] for i in range(len(positions))]
