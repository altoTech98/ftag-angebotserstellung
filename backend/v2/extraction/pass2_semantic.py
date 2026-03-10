"""
Pass 2: AI semantic extraction using Claude via messages.parse().

Sends page-based chunks to Claude and returns ExtractedDoorPosition objects.
Uses chunking for large documents, retry with exponential backoff,
and FieldSource provenance tracking.
"""

import asyncio
import json
import logging
from typing import Optional

import anthropic

from v2.extraction.chunking import chunk_by_pages
from v2.extraction.prompts import PASS2_SYSTEM_PROMPT, PASS2_USER_TEMPLATE
from v2.parsers.base import ParseResult
from v2.schemas.common import FieldSource
from v2.schemas.extraction import ExtractionResult, ExtractedDoorPosition

logger = logging.getLogger(__name__)

# Retry configuration
_MAX_RETRIES = 3
_BASE_BACKOFF_SECONDS = 2


async def _call_claude_parse(
    client: anthropic.Anthropic,
    chunk_text: str,
    existing_positions_json: str,
) -> ExtractionResult:
    """Call Claude messages.parse() with structured output.

    Uses asyncio.to_thread to wrap the synchronous Anthropic client,
    since messages.parse() may not be available on AsyncAnthropic.
    """
    messages = [
        {
            "role": "user",
            "content": PASS2_USER_TEMPLATE.format(
                chunk_text=chunk_text,
                existing_positions_json=existing_positions_json,
            ),
        }
    ]

    response = await asyncio.to_thread(
        client.messages.parse,
        model="claude-sonnet-4-20250514",
        max_tokens=16384,
        system=PASS2_SYSTEM_PROMPT,
        messages=messages,
        output_format=ExtractionResult,
    )

    # Check for truncation
    if hasattr(response, "stop_reason") and response.stop_reason == "max_tokens":
        logger.warning("Pass 2: Response truncated (max_tokens reached)")

    return response.output


async def _extract_chunk_with_retry(
    client: anthropic.Anthropic,
    chunk: dict,
    existing_positions_json: str,
    chunk_index: int,
    total_chunks: int,
) -> tuple[list[ExtractedDoorPosition], list[str]]:
    """Extract positions from a single chunk with 3x retry.

    Returns:
        Tuple of (positions, warnings).
    """
    warnings = []

    for attempt in range(_MAX_RETRIES):
        try:
            result = await _call_claude_parse(
                client, chunk["text"], existing_positions_json
            )
            logger.info(
                f"Pass 2: Chunk {chunk_index + 1}/{total_chunks} "
                f"extracted {len(result.positionen)} positions"
            )
            return result.positionen, result.warnungen
        except Exception as e:
            backoff = _BASE_BACKOFF_SECONDS ** (attempt + 1)
            logger.warning(
                f"Pass 2: Chunk {chunk_index + 1}/{total_chunks} "
                f"attempt {attempt + 1}/{_MAX_RETRIES} failed: {e}. "
                f"Retrying in {backoff}s..."
            )
            if attempt < _MAX_RETRIES - 1:
                await asyncio.sleep(backoff)

    # All retries exhausted
    warning = (
        f"Pass 2: Chunk {chunk_index + 1}/{total_chunks} "
        f"(pages {chunk['start_page']}-{chunk['end_page']}) "
        f"failed after {_MAX_RETRIES} attempts, skipping"
    )
    logger.warning(warning)
    warnings.append(warning)
    return [], warnings


def _tag_positions_with_source(
    positions: list[ExtractedDoorPosition],
    source_file: str,
    start_page: int,
) -> list[ExtractedDoorPosition]:
    """Tag all position fields with FieldSource provenance from Pass 2."""
    tagged = []
    for pos in positions:
        source = FieldSource(
            dokument=source_file,
            konfidenz=0.9,
            seite=start_page,
        )
        # Tag all non-None fields that don't already have a source
        new_quellen = dict(pos.quellen)
        for field_name in pos.model_fields:
            if field_name == "quellen":
                continue
            val = getattr(pos, field_name)
            if val is not None and field_name not in new_quellen:
                new_quellen[field_name] = source

        tagged.append(pos.model_copy(update={"quellen": new_quellen}))
    return tagged


async def extract_semantic(
    parse_result: ParseResult,
    existing_positions: Optional[list[ExtractedDoorPosition]] = None,
    client: Optional[anthropic.Anthropic] = None,
) -> list[ExtractedDoorPosition]:
    """Pass 2: AI semantic extraction from document text.

    Chunks the document by pages, sends each chunk to Claude via
    messages.parse(), and returns all extracted positions with provenance.

    Args:
        parse_result: Parsed document to extract from.
        existing_positions: Positions from earlier passes (context for AI).
        client: Anthropic client (created if not provided).

    Returns:
        List of ExtractedDoorPosition from all chunks combined.
    """
    if client is None:
        client = anthropic.Anthropic()

    if not parse_result.text:
        return []

    # Chunk the document
    chunks = chunk_by_pages(
        parse_result.text,
        parse_result.page_count,
    )

    # Serialize existing positions for context
    if existing_positions:
        existing_json = json.dumps(
            [
                {
                    "positions_nr": p.positions_nr,
                    "breite_mm": p.breite_mm,
                    "hoehe_mm": p.hoehe_mm,
                    "brandschutz_klasse": (
                        p.brandschutz_klasse.value if p.brandschutz_klasse else None
                    ),
                    "material_blatt": (
                        p.material_blatt.value if p.material_blatt else None
                    ),
                }
                for p in existing_positions
            ],
            ensure_ascii=False,
            indent=2,
        )
    else:
        existing_json = "[]"

    all_positions: list[ExtractedDoorPosition] = []
    all_warnings: list[str] = []

    for i, chunk in enumerate(chunks):
        positions, warnings = await _extract_chunk_with_retry(
            client, chunk, existing_json, i, len(chunks)
        )
        all_warnings.extend(warnings)

        # Tag with provenance
        tagged = _tag_positions_with_source(
            positions, parse_result.source_file, chunk["start_page"]
        )
        all_positions.extend(tagged)

    logger.info(
        f"Pass 2: {parse_result.source_file} -> "
        f"{len(all_positions)} positions from {len(chunks)} chunks"
    )

    return all_positions
