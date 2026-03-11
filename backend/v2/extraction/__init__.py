"""
Phase 2+3: Multi-Pass Extraction + Cross-Document Intelligence.

AI-powered extraction of structured door positions from parsed text.
Uses Claude with Pydantic schemas via messages.parse().

Phase 3 adds cross-document intelligence: position matching, enrichment,
and conflict detection across multiple tender documents.
"""

from v2.extraction.pass1_structural import extract_structural
from v2.extraction.pass2_semantic import extract_semantic
from v2.extraction.pass3_validation import validate_and_enrich
from v2.extraction.pipeline import run_extraction_pipeline, run_cross_doc_intelligence
from v2.extraction.chunking import chunk_by_pages
from v2.extraction.dedup import merge_positions, ai_dedup_cluster
from v2.extraction.cross_doc_matcher import match_positions_across_docs
from v2.extraction.enrichment import enrich_positions
from v2.extraction.conflict_detector import detect_and_resolve_conflicts
from v2.extraction.prompts import (
    PASS2_SYSTEM_PROMPT,
    PASS2_USER_TEMPLATE,
    PASS3_SYSTEM_PROMPT,
    PASS3_USER_TEMPLATE,
    DEDUP_PROMPT_TEMPLATE,
)

__all__ = [
    "extract_structural",
    "extract_semantic",
    "validate_and_enrich",
    "run_extraction_pipeline",
    "run_cross_doc_intelligence",
    "chunk_by_pages",
    "merge_positions",
    "ai_dedup_cluster",
    "match_positions_across_docs",
    "enrich_positions",
    "detect_and_resolve_conflicts",
    "PASS2_SYSTEM_PROMPT",
    "PASS2_USER_TEMPLATE",
    "PASS3_SYSTEM_PROMPT",
    "PASS3_USER_TEMPLATE",
    "DEDUP_PROMPT_TEMPLATE",
]
