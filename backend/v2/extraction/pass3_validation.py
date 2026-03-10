"""
Pass 3: Cross-reference validation and adversarial review.

Receives all positions and original texts, sends to Claude for
critical validation. Corrects errors, fills gaps, adds missed positions.
"""

import asyncio
import json
import logging
from typing import Optional

import anthropic

from v2.extraction.dedup import merge_positions
from v2.extraction.prompts import PASS3_SYSTEM_PROMPT, PASS3_USER_TEMPLATE
from v2.schemas.common import FieldSource
from v2.schemas.extraction import ExtractionResult, ExtractedDoorPosition

logger = logging.getLogger(__name__)

# Retry configuration
_MAX_RETRIES = 3
_BASE_BACKOFF_SECONDS = 2

# Batching thresholds
_MAX_POSITIONS_PER_BATCH = 25
_MAX_TEXT_CHARS = 100_000


def _summarize_positions(positions: list[ExtractedDoorPosition]) -> str:
    """Create a compact summary of positions for Pass 3 prompt.

    Only sends key fields to avoid context overflow (Pitfall 5).
    """
    summaries = []
    for pos in positions:
        summary = {
            "positions_nr": pos.positions_nr,
            "breite_mm": pos.breite_mm,
            "hoehe_mm": pos.hoehe_mm,
            "brandschutz_klasse": (
                pos.brandschutz_klasse.value if pos.brandschutz_klasse else None
            ),
            "schallschutz_klasse": (
                pos.schallschutz_klasse.value if pos.schallschutz_klasse else None
            ),
            "material_blatt": (
                pos.material_blatt.value if pos.material_blatt else None
            ),
            "anzahl_fluegel": pos.anzahl_fluegel,
            "oeffnungsart": (
                pos.oeffnungsart.value if pos.oeffnungsart else None
            ),
            "bemerkungen": pos.bemerkungen,
        }
        summaries.append(summary)
    return json.dumps(summaries, ensure_ascii=False, indent=2)


async def _call_pass3_parse(
    client: anthropic.Anthropic,
    positions_json: str,
    original_texts: str,
) -> ExtractionResult:
    """Call Claude messages.parse() for Pass 3 validation."""
    messages = [
        {
            "role": "user",
            "content": PASS3_USER_TEMPLATE.format(
                all_positions_json=positions_json,
                original_texts=original_texts,
            ),
        }
    ]

    response = await asyncio.to_thread(
        client.messages.parse,
        model="claude-sonnet-4-20250514",
        max_tokens=16384,
        system=PASS3_SYSTEM_PROMPT,
        messages=messages,
        output_format=ExtractionResult,
    )

    if hasattr(response, "stop_reason") and response.stop_reason == "max_tokens":
        logger.warning("Pass 3: Response truncated (max_tokens reached)")

    return response.output


async def _validate_batch_with_retry(
    client: anthropic.Anthropic,
    positions: list[ExtractedDoorPosition],
    original_texts: str,
    batch_index: int,
    total_batches: int,
) -> tuple[list[ExtractedDoorPosition], list[str]]:
    """Validate a batch of positions with 3x retry.

    Returns:
        Tuple of (validated_positions, warnings).
    """
    positions_json = _summarize_positions(positions)
    warnings = []

    for attempt in range(_MAX_RETRIES):
        try:
            result = await _call_pass3_parse(
                client, positions_json, original_texts
            )
            logger.info(
                f"Pass 3: Batch {batch_index + 1}/{total_batches} "
                f"validated {len(result.positionen)} positions"
            )
            return result.positionen, result.warnungen
        except Exception as e:
            backoff = _BASE_BACKOFF_SECONDS ** (attempt + 1)
            logger.warning(
                f"Pass 3: Batch {batch_index + 1}/{total_batches} "
                f"attempt {attempt + 1}/{_MAX_RETRIES} failed: {e}. "
                f"Retrying in {backoff}s..."
            )
            if attempt < _MAX_RETRIES - 1:
                await asyncio.sleep(backoff)

    # All retries exhausted -- return unchanged with warning
    warning = (
        f"Pass 3: Batch {batch_index + 1}/{total_batches} "
        f"failed after {_MAX_RETRIES} attempts, returning positions unchanged"
    )
    logger.warning(warning)
    warnings.append(warning)
    return positions, warnings


def _tag_pass3_provenance(
    positions: list[ExtractedDoorPosition],
    source_files: list[str],
) -> list[ExtractedDoorPosition]:
    """Tag Pass 3 positions with validation provenance."""
    tagged = []
    doc_name = ", ".join(source_files) if source_files else "validation"
    for pos in positions:
        source = FieldSource(
            dokument=doc_name,
            konfidenz=0.95,
        )
        new_quellen = dict(pos.quellen)
        for field_name in pos.model_fields:
            if field_name == "quellen":
                continue
            val = getattr(pos, field_name)
            if val is not None and field_name not in new_quellen:
                new_quellen[field_name] = source
        tagged.append(pos.model_copy(update={"quellen": new_quellen}))
    return tagged


async def validate_and_enrich(
    positions: list[ExtractedDoorPosition],
    original_texts: list[str],
    source_files: list[str],
    client: Optional[anthropic.Anthropic] = None,
) -> list[ExtractedDoorPosition]:
    """Pass 3: Cross-reference validation and adversarial review.

    Sends all positions and original texts to Claude for critical review.
    Batches large position sets to avoid context overflow.

    Args:
        positions: All positions from Pass 1+2.
        original_texts: Original document texts for cross-reference.
        source_files: Source filenames for provenance.
        client: Anthropic client (created if not provided).

    Returns:
        Validated and enriched positions (Pass 3 wins conflicts).
    """
    if client is None:
        client = anthropic.Anthropic()

    if not positions:
        return []

    # Combine original texts
    combined_texts = "\n\n---\n\n".join(original_texts)

    # Truncate if too large
    if len(combined_texts) > _MAX_TEXT_CHARS:
        combined_texts = combined_texts[:_MAX_TEXT_CHARS] + "\n...[truncated]"

    # Determine batching
    all_validated: list[ExtractedDoorPosition] = []
    all_warnings: list[str] = []

    if len(positions) <= _MAX_POSITIONS_PER_BATCH:
        # Single batch
        validated, warnings = await _validate_batch_with_retry(
            client, positions, combined_texts, 0, 1
        )
        all_validated.extend(validated)
        all_warnings.extend(warnings)
    else:
        # Multiple batches
        total_batches = (len(positions) + _MAX_POSITIONS_PER_BATCH - 1) // _MAX_POSITIONS_PER_BATCH
        for batch_idx in range(total_batches):
            start = batch_idx * _MAX_POSITIONS_PER_BATCH
            end = min(start + _MAX_POSITIONS_PER_BATCH, len(positions))
            batch = positions[start:end]

            validated, warnings = await _validate_batch_with_retry(
                client, batch, combined_texts, batch_idx, total_batches
            )
            all_validated.extend(validated)
            all_warnings.extend(warnings)

    # Tag with Pass 3 provenance
    tagged = _tag_pass3_provenance(all_validated, source_files)

    # Merge: Pass 3 results win over existing (pass_priority=3)
    merged = merge_positions(positions, tagged, pass_priority=3)

    logger.info(
        f"Pass 3: Validated {len(positions)} -> {len(merged)} positions"
    )

    return merged
