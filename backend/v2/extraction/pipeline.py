"""
Pipeline orchestrator: coordinates all 3 extraction passes.

Runs Pass 1 (structural) and Pass 2 (semantic) per-file with dedup,
then Pass 3 (validation) across all files. Returns ExtractionResult.
"""

import logging
from typing import Optional

import anthropic

from v2.extraction.conflict_detector import detect_and_resolve_conflicts
from v2.extraction.cross_doc_matcher import match_positions_across_docs
from v2.extraction.dedup import merge_positions
from v2.extraction.enrichment import enrich_positions
from v2.extraction.pass1_structural import extract_structural
from v2.extraction.pass2_semantic import extract_semantic
from v2.extraction.pass3_validation import validate_and_enrich
from v2.parsers.base import ParseResult
from v2.schemas.common import DokumentTyp
from v2.schemas.extraction import (
    EnrichmentReport,
    ExtractionResult,
    ExtractedDoorPosition,
    FieldConflict,
)

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


async def run_cross_doc_intelligence(
    all_positions: list[ExtractedDoorPosition],
    sorted_results: list[ParseResult],
    client: Optional[anthropic.Anthropic] = None,
) -> tuple[list[ExtractedDoorPosition], Optional[EnrichmentReport], list[FieldConflict]]:
    """Run cross-document intelligence on positions from multiple files.

    Groups positions by source document, matches across documents,
    detects/resolves conflicts, and enriches positions.

    Args:
        all_positions: Flat list of all extracted positions.
        sorted_results: ParseResult objects (used for source file names).
        client: Anthropic client for AI-powered resolution.

    Returns:
        Tuple of (enriched positions, enrichment report, conflicts).
    """
    # Group positions by source document using quellen
    positions_by_doc: dict[str, list[ExtractedDoorPosition]] = {}
    source_filenames = {r.source_file for r in sorted_results}

    for pos in all_positions:
        # Determine source doc from quellen
        doc_name = None
        for source in pos.quellen.values():
            if source.dokument and source.dokument in source_filenames:
                doc_name = source.dokument
                break

        if doc_name is None:
            # Fallback: assign to first source file
            doc_name = sorted_results[0].source_file

        if doc_name not in positions_by_doc:
            positions_by_doc[doc_name] = []
        positions_by_doc[doc_name].append(pos)

    # Step 1: Match positions across documents
    matches = match_positions_across_docs(positions_by_doc)

    if not matches:
        logger.info("Cross-doc: No matches found across documents")
        return all_positions, None, []

    # Step 2: Separate auto-merge from possible matches
    auto_merge_matches = [m for m in matches if m.auto_merge]
    possible_matches = [m for m in matches if not m.auto_merge]

    # Step 3: Detect and resolve conflicts on auto-merge matches
    conflicts = detect_and_resolve_conflicts(
        auto_merge_matches, all_positions, client=client
    )

    # Step 4: Enrich positions using auto-merge matches
    enriched_positions, enrichment_report = enrich_positions(
        auto_merge_matches, all_positions, general_specs=None
    )

    # Update enrichment report with conflict counts
    enrichment_report = enrichment_report.model_copy(update={
        "konflikte_total": len(conflicts),
        "konflikte_critical": sum(
            1 for c in conflicts if c.severity.value == "critical"
        ),
        "konflikte_major": sum(
            1 for c in conflicts if c.severity.value == "major"
        ),
        "konflikte_minor": sum(
            1 for c in conflicts if c.severity.value == "minor"
        ),
    })

    logger.info(
        f"Cross-doc: {len(auto_merge_matches)} auto-merge, "
        f"{len(possible_matches)} possible, {len(conflicts)} conflicts"
    )

    return enriched_positions, enrichment_report, conflicts


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

    # Cross-document intelligence (multi-file only)
    enrichment_report = None
    conflicts: list[FieldConflict] = []

    if len(sorted_results) >= 2:
        logger.info(
            f"Pipeline [{tender_id}]: Cross-document intelligence on "
            f"{len(all_positions)} positions from {len(sorted_results)} files"
        )
        all_positions, enrichment_report, conflicts = await run_cross_doc_intelligence(
            all_positions, sorted_results, client=client
        )
        logger.info(
            f"Pipeline [{tender_id}]: Cross-doc complete - "
            f"{enrichment_report.felder_enriched if enrichment_report else 0} fields enriched, "
            f"{len(conflicts)} conflicts"
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
        enrichment_report=enrichment_report,
        conflicts=conflicts,
    )
