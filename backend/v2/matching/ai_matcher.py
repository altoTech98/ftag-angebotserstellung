"""
AI matching engine: one-position-per-call Claude Sonnet matching
with structured output, safety caps, and concurrent execution.

Pipeline per position:
  1. TF-IDF candidates (from tfidf_index)
  2. Claude Sonnet evaluation (messages.parse -> MatchResult)
  3. Safety cap (Brandschutz < 0.5 -> cap at 0.6)
  4. hat_match threshold (>= 0.95)
  5. Limit alternatives to 3
"""

import asyncio
import json
import logging
from typing import Optional, Callable

import anthropic

from v2.matching.prompts import (
    MATCHING_SYSTEM_PROMPT,
    MATCHING_USER_TEMPLATE,
    format_feedback_section,
)
from v2.matching.tfidf_index import CatalogTfidfIndex
from v2.schemas.extraction import ExtractedDoorPosition
from v2.schemas.matching import (
    MatchCandidate,
    MatchDimension,
    MatchResult,
)

logger = logging.getLogger(__name__)

# Concurrency limit for parallel API calls
MAX_CONCURRENT = 5

# Confidence threshold for confirmed match
HAT_MATCH_THRESHOLD = 0.95

# Safety cap: if Brandschutz < this, cap gesamt_konfidenz
BRANDSCHUTZ_MIN = 0.5
SAFETY_CAP_MAX = 0.6


def _apply_safety_caps(result: MatchResult) -> MatchResult:
    """Apply safety caps to a MatchResult.

    If any Brandschutz DimensionScore < 0.5, cap gesamt_konfidenz
    at max 0.6 and set hat_match=False. Applied to bester_match
    and all alternative_matches.
    """

    def _cap_candidate(candidate: MatchCandidate) -> MatchCandidate:
        brandschutz_scores = [
            ds.score
            for ds in candidate.dimension_scores
            if ds.dimension == MatchDimension.BRANDSCHUTZ
        ]
        if brandschutz_scores and any(s < BRANDSCHUTZ_MIN for s in brandschutz_scores):
            candidate.gesamt_konfidenz = min(
                candidate.gesamt_konfidenz, SAFETY_CAP_MAX
            )
        return candidate

    if result.bester_match:
        result.bester_match = _cap_candidate(result.bester_match)
    result.alternative_matches = [
        _cap_candidate(alt) for alt in result.alternative_matches
    ]

    # If best match was capped, it cannot be a confirmed match
    if result.bester_match and result.bester_match.gesamt_konfidenz <= SAFETY_CAP_MAX:
        # Check if it was actually capped (brandschutz was low)
        brandschutz_scores = [
            ds.score
            for ds in result.bester_match.dimension_scores
            if ds.dimension == MatchDimension.BRANDSCHUTZ
        ]
        if brandschutz_scores and any(s < BRANDSCHUTZ_MIN for s in brandschutz_scores):
            result.hat_match = False

    return result


def _set_hat_match(result: MatchResult) -> MatchResult:
    """Set hat_match based on gesamt_konfidenz threshold.

    hat_match=True only if bester_match exists and
    bester_match.gesamt_konfidenz >= 0.95.
    """
    if result.bester_match and result.bester_match.gesamt_konfidenz >= HAT_MATCH_THRESHOLD:
        result.hat_match = True
    else:
        result.hat_match = False
    result.match_methode = "tfidf_ai"
    return result


def _limit_alternatives(result: MatchResult) -> MatchResult:
    """Limit alternative_matches to at most 3 entries."""
    result.alternative_matches = result.alternative_matches[:3]
    return result


async def match_single_position(
    client: anthropic.Anthropic,
    position: ExtractedDoorPosition,
    candidates: list[dict],
    feedback_examples: list[dict] | None = None,
) -> MatchResult:
    """Match one position against candidates using Claude Sonnet.

    Uses asyncio.to_thread to wrap the synchronous messages.parse() call.

    Args:
        client: Anthropic client instance.
        position: Extracted door position to match.
        candidates: List of candidate product dicts from TF-IDF.
        feedback_examples: Optional past corrections for few-shot learning.

    Returns:
        MatchResult with safety caps and thresholds applied.
    """
    feedback_section = format_feedback_section(feedback_examples)

    user_content = MATCHING_USER_TEMPLATE.format(
        position_json=position.model_dump_json(exclude_none=True),
        candidates_json=json.dumps(candidates, ensure_ascii=False, indent=None),
        feedback_section=feedback_section,
    )

    response = await asyncio.to_thread(
        client.messages.parse,
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=MATCHING_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
        output_format=MatchResult,
    )
    result = response.parsed

    # Post-processing pipeline
    result = _apply_safety_caps(result)
    result = _set_hat_match(result)
    result = _limit_alternatives(result)

    return result


async def match_positions(
    client: anthropic.Anthropic,
    positions: list[ExtractedDoorPosition],
    tfidf_index: CatalogTfidfIndex,
    feedback_examples_fn: Optional[Callable] = None,
) -> list[MatchResult]:
    """Match multiple positions concurrently through TF-IDF + Claude pipeline.

    Uses asyncio.Semaphore(5) to limit concurrent API calls.

    Args:
        client: Anthropic client instance.
        positions: List of positions to match.
        tfidf_index: TF-IDF index for candidate retrieval.
        feedback_examples_fn: Optional callable returning feedback examples
            for a given position.

    Returns:
        List of MatchResult, one per position (in order).
    """
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)

    async def _match_one(pos: ExtractedDoorPosition) -> MatchResult:
        async with semaphore:
            try:
                # Step 1: TF-IDF candidate retrieval
                tfidf_results = tfidf_index.search(pos, top_k=50)
                candidates = [
                    tfidf_index.extract_candidate_fields(idx)
                    for idx, _score in tfidf_results
                ]

                # Step 2: Get feedback examples if available
                feedback = None
                if feedback_examples_fn:
                    try:
                        feedback = feedback_examples_fn(pos)
                    except Exception as e:
                        logger.debug(f"Feedback lookup failed: {e}")

                # Step 3: AI matching
                result = await match_single_position(
                    client=client,
                    position=pos,
                    candidates=candidates,
                    feedback_examples=feedback,
                )
                # Ensure positions_nr matches
                result.positions_nr = pos.positions_nr
                return result

            except Exception as e:
                logger.error(
                    f"Matching failed for position {pos.positions_nr}: {e}"
                )
                # Return empty result for failed position
                return MatchResult(
                    positions_nr=pos.positions_nr,
                    bester_match=None,
                    alternative_matches=[],
                    hat_match=False,
                    match_methode="tfidf_ai",
                )

    tasks = [_match_one(pos) for pos in positions]
    results = await asyncio.gather(*tasks)
    return list(results)
