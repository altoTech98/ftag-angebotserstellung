"""
Phase 2: Multi-Pass Extraction.

AI-powered extraction of structured door positions from parsed text.
Uses Claude with Pydantic schemas via messages.parse().
"""

from v2.extraction.pass1_structural import extract_structural
from v2.extraction.pass2_semantic import extract_semantic
from v2.extraction.pass3_validation import validate_and_enrich
from v2.extraction.pipeline import run_extraction_pipeline
from v2.extraction.chunking import chunk_by_pages
from v2.extraction.dedup import merge_positions, ai_dedup_cluster
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
    "chunk_by_pages",
    "merge_positions",
    "ai_dedup_cluster",
    "PASS2_SYSTEM_PROMPT",
    "PASS2_USER_TEMPLATE",
    "PASS3_SYSTEM_PROMPT",
    "PASS3_USER_TEMPLATE",
    "DEDUP_PROMPT_TEMPLATE",
]
