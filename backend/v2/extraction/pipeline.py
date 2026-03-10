"""
Pipeline orchestrator: coordinates all 3 extraction passes.

Runs Pass 1 (structural) and Pass 2 (semantic) per-file with dedup,
then Pass 3 (validation) across all files. Returns ExtractionResult.
"""

import logging
from typing import Optional

import anthropic

from v2.extraction.dedup import merge_positions
from v2.extraction.pass1_structural import extract_structural
from v2.extraction.pass2_semantic import extract_semantic
from v2.extraction.pass3_validation import validate_and_enrich
from v2.parsers.base import ParseResult
from v2.schemas.common import DokumentTyp
from v2.schemas.extraction import ExtractionResult, ExtractedDoorPosition

logger = logging.getLogger(__name__)

# Format priority for file processing order: XLSX first, then PDF, then DOCX
_FORMAT_PRIORITY = {
    "xlsx": 0,
    "xls": 0,
    "pdf": 1,
    "docx": 2,
    "doc": 2,
    "txt": 3,
}


def _sort_by_format(results: list[ParseResult]) -> list[ParseResult]:
    """Sort ParseResults by format priority: xlsx > pdf > docx > other.

    Args:
        results: List of ParseResult objects.

    Returns:
        Sorted list with XLSX first, then PDF, then DOCX.
    """
    return sorted(
        results,
        key=lambda r: _FORMAT_PRIORITY.get(r.format, 9),
    )


def _detect_dokument_typ(parse_results: list[ParseResult]) -> DokumentTyp:
    """Determine the primary document type from parse results."""
    if not parse_results:
        return DokumentTyp.UNKNOWN

    # Use the first (highest priority) file's format
    fmt = parse_results[0].format
    mapping = {
        "xlsx": DokumentTyp.XLSX,
        "xls": DokumentTyp.XLSX,
        "pdf": DokumentTyp.PDF,
        "docx": DokumentTyp.DOCX,
        "txt": DokumentTyp.TXT,
    }
    return mapping.get(fmt, DokumentTyp.UNKNOWN)


async def run_extraction_pipeline(
    parse_results: list[ParseResult],
    tender_id: str,
    client: Optional[anthropic.Anthropic] = None,
) -> ExtractionResult:
    """Run the full 3-pass extraction pipeline.

    Processing order:
    1. Sort files: XLSX first, then PDF, then DOCX
    2. For each file: Pass 1 (structural) -> dedup -> Pass 2 (semantic) -> dedup
    3. After all files: Pass 3 (cross-reference validation)

    Args:
        parse_results: Parsed documents to extract from.
        tender_id: Tender session ID for logging.
        client: Anthropic client (created if not provided).

    Returns:
        ExtractionResult with all positions, summary, and warnings.
    """
    if client is None:
        client = anthropic.Anthropic()

    sorted_results = _sort_by_format(parse_results)
    all_positions: list[ExtractedDoorPosition] = []
    all_warnings: list[str] = []
    original_texts: list[str] = []
    source_files: list[str] = []

    logger.info(
        f"Pipeline [{tender_id}]: Processing {len(sorted_results)} files "
        f"in order: {[r.source_file for r in sorted_results]}"
    )

    # Per-file: Pass 1 + Pass 2 with dedup
    for pr in sorted_results:
        original_texts.append(pr.text)
        source_files.append(pr.source_file)

        # Pass 1: Structural extraction (regex, no AI)
        logger.info(f"Pipeline [{tender_id}]: Pass 1 on {pr.source_file}")
        pass1_results = extract_structural(pr)
        all_positions = merge_positions(
            all_positions, pass1_results, pass_priority=1
        )
        logger.info(
            f"Pipeline [{tender_id}]: Pass 1 -> {len(pass1_results)} positions "
            f"(total: {len(all_positions)})"
        )

        # Pass 2: Semantic AI extraction
        logger.info(f"Pipeline [{tender_id}]: Pass 2 on {pr.source_file}")
        pass2_results = await extract_semantic(
            pr, existing_positions=all_positions, client=client
        )
        all_positions = merge_positions(
            all_positions, pass2_results, pass_priority=2
        )
        logger.info(
            f"Pipeline [{tender_id}]: Pass 2 -> {len(pass2_results)} positions "
            f"(total: {len(all_positions)})"
        )

    # Pass 3: Cross-reference validation across all files
    if all_positions:
        logger.info(
            f"Pipeline [{tender_id}]: Pass 3 validating {len(all_positions)} positions"
        )
        all_positions = await validate_and_enrich(
            all_positions, original_texts, source_files, client=client
        )
        logger.info(
            f"Pipeline [{tender_id}]: Pass 3 -> {len(all_positions)} final positions"
        )

    # Build summary
    file_summary = ", ".join(
        f"{r.source_file} ({r.format})" for r in sorted_results
    )
    summary = (
        f"Extraktion aus {len(sorted_results)} Dokumenten: {file_summary}. "
        f"{len(all_positions)} Tuerpositionen extrahiert."
    )

    dokument_typ = _detect_dokument_typ(sorted_results)

    return ExtractionResult(
        positionen=all_positions,
        dokument_zusammenfassung=summary,
        warnungen=all_warnings,
        dokument_typ=dokument_typ,
    )
