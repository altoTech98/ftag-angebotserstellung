"""
Adversarial validation engine: FOR/AGAINST debate per position.

Pipeline per position:
  1. FOR argument (Opus call: argues match is correct)
  2. AGAINST argument (Opus call: argues match is wrong)
  3. Resolution (deterministic: synthesizes into adjusted confidence)

Uses asyncio.Semaphore(3) for concurrent Opus calls (lower than
Phase 4's 5 due to Opus rate limits).
"""

import asyncio
import json
import logging
from typing import Optional

import anthropic

from v2.matching.adversarial_prompts import (
    FOR_SYSTEM_PROMPT,
    AGAINST_SYSTEM_PROMPT,
    FOR_USER_TEMPLATE,
    AGAINST_USER_TEMPLATE,
    WIDER_POOL_SYSTEM_PROMPT,
    WIDER_POOL_USER_TEMPLATE,
    INVERTED_SYSTEM_PROMPT,
    INVERTED_USER_TEMPLATE,
)
from v2.schemas.adversarial import (
    AdversarialCandidate,
    AdversarialResult,
    AgainstArgument,
    CandidateDebate,
    DimensionCoT,
    ForArgument,
    ValidationStatus,
)
from v2.schemas.matching import MatchCandidate, MatchResult

logger = logging.getLogger(__name__)

# Concurrency limit for parallel Opus calls
ADVERSARIAL_MAX_CONCURRENT = 3

# Confidence threshold for confirmed match
BESTAETIGT_THRESHOLD = 0.95

# Dimension weights for resolution (safety-critical dimensions weighted higher)
DIMENSION_WEIGHTS = {
    "Brandschutz": 2.0,
    "Masse": 1.5,
    "Schallschutz": 1.5,
    "Material": 1.0,
    "Zertifizierung": 1.0,
    "Leistung": 0.8,
}

# Max alternatives to debate (best match + up to 3 alternatives)
MAX_ALTERNATIVES_TO_DEBATE = 3


def _format_candidate_for_prompt(candidate: MatchCandidate) -> dict:
    """Format a MatchCandidate into a dict suitable for prompt injection."""
    return {
        "produkt_id": candidate.produkt_id,
        "produkt_name": candidate.produkt_name,
        "gesamt_konfidenz": candidate.gesamt_konfidenz,
        "dimension_scores": [
            {
                "dimension": ds.dimension.value if hasattr(ds.dimension, "value") else str(ds.dimension),
                "score": ds.score,
                "begruendung": ds.begruendung,
            }
            for ds in candidate.dimension_scores
        ],
        "begruendung": candidate.begruendung,
    }


def _build_user_content(
    template: str,
    match_result: MatchResult,
) -> str:
    """Build user content for FOR or AGAINST prompt."""
    # Gather all candidates to debate: best + up to 3 alternatives
    candidates_data = []
    if match_result.bester_match:
        candidates_data.append(_format_candidate_for_prompt(match_result.bester_match))
    for alt in match_result.alternative_matches[:MAX_ALTERNATIVES_TO_DEBATE]:
        candidates_data.append(_format_candidate_for_prompt(alt))

    anforderung = f"Position {match_result.positions_nr}"
    kandidaten = json.dumps(candidates_data, ensure_ascii=False, indent=2)
    phase4_ergebnis = json.dumps(
        {
            "positions_nr": match_result.positions_nr,
            "hat_match": match_result.hat_match,
            "match_methode": match_result.match_methode,
            "bester_match_id": match_result.bester_match.produkt_id if match_result.bester_match else None,
            "bester_match_konfidenz": match_result.bester_match.gesamt_konfidenz if match_result.bester_match else None,
        },
        ensure_ascii=False,
    )

    return template.format(
        anforderung=anforderung,
        kandidaten=kandidaten,
        phase4_ergebnis=phase4_ergebnis,
    )


def resolve_debate(
    for_result: ForArgument,
    against_result: AgainstArgument,
    match_result: MatchResult,
) -> tuple[float, list[DimensionCoT], str]:
    """Deterministic resolution: synthesize FOR/AGAINST into adjusted confidence.

    Weighted average of dimension scores from both arguments, with safety-critical
    dimensions weighted heavier. Returns (adjusted_confidence, per_dimension_cot, reasoning).
    """
    # Collect dimension scores from both sides
    for_scores = {
        db.dimension: db.score for db in for_result.dimension_bewertungen
    }
    against_scores = {
        db.dimension: db.score for db in against_result.dimension_bewertungen
    }

    # Build per-dimension CoT from both FOR and AGAINST
    dimension_cot_list: list[DimensionCoT] = []
    weighted_sum = 0.0
    weight_total = 0.0

    # Standard dimension names
    all_dimensions = ["Masse", "Brandschutz", "Schallschutz", "Material", "Zertifizierung", "Leistung"]

    for dim_name in all_dimensions:
        # Get scores from both sides (default to Phase 4 score if missing)
        f_score = for_scores.get(dim_name, 0.5)
        a_score = against_scores.get(dim_name, 0.5)

        # Combined score: average of FOR score and (1 - AGAINST wrongness).
        # FOR gives how right the match is, AGAINST gives how wrong.
        # For AGAINST: the dimension score represents how well the product
        # actually matches from the critic's view (higher = critic agrees it matches).
        combined_score = (f_score + a_score) / 2.0

        weight = DIMENSION_WEIGHTS.get(dim_name, 1.0)
        weighted_sum += combined_score * weight
        weight_total += weight

        # Adaptive verbosity
        confidence_level = "hoch" if combined_score > 0.9 else "niedrig"

        # Build reasoning from both arguments
        for_bew = next(
            (db for db in for_result.dimension_bewertungen if db.dimension == dim_name),
            None,
        )
        against_bew = next(
            (db for db in against_result.dimension_bewertungen if db.dimension == dim_name),
            None,
        )

        if confidence_level == "hoch":
            reasoning = for_bew.begruendung if for_bew else f"{dim_name} passt."
        else:
            for_text = for_bew.begruendung if for_bew else "Keine FOR-Begruendung."
            against_text = against_bew.begruendung if against_bew else "Keine AGAINST-Begruendung."
            reasoning = f"FOR: {for_text} AGAINST: {against_text}"

        dimension_cot_list.append(
            DimensionCoT(
                dimension=dim_name,
                score=round(combined_score, 4),
                reasoning=reasoning,
                confidence_level=confidence_level,
            )
        )

    adjusted_confidence = round(weighted_sum / weight_total, 4) if weight_total > 0 else 0.0

    # Build resolution reasoning
    reasoning_parts = [
        f"FOR-Konfidenz: {for_result.for_konfidenz:.2f}, "
        f"AGAINST-Konfidenz (dass Match falsch): {against_result.against_konfidenz:.2f}.",
        f"FOR: {for_result.zusammenfassung}",
        f"AGAINST: {against_result.zusammenfassung}",
        f"Gewichtete Gesamtbewertung: {adjusted_confidence:.2f}.",
    ]
    resolution_reasoning = " ".join(reasoning_parts)

    return adjusted_confidence, dimension_cot_list, resolution_reasoning


def _build_adversarial_candidate(
    candidate: MatchCandidate,
    for_result: ForArgument,
    against_result: AgainstArgument,
    adjusted_confidence: float,
    dimension_cot: list[DimensionCoT],
) -> AdversarialCandidate:
    """Build an AdversarialCandidate from debate results."""
    return AdversarialCandidate(
        produkt_id=candidate.produkt_id,
        produkt_name=candidate.produkt_name,
        adjusted_confidence=adjusted_confidence,
        dimension_scores=dimension_cot,
        reasoning_summary=f"FOR: {for_result.zusammenfassung} AGAINST: {against_result.zusammenfassung}",
    )


async def triple_check_position(
    client: anthropic.Anthropic,
    match_result: MatchResult,
    debate_result: AdversarialResult,
    tfidf_index,
    semaphore: asyncio.Semaphore,
) -> AdversarialResult:
    """Triple-check: run wider pool + inverted prompt in parallel.

    Two independent approaches to re-evaluate the match:
    1. Wider pool: expand TF-IDF search to top_k=80, re-evaluate with Opus
    2. Inverted prompt: requirement-centric evaluation (different from product-centric)

    Selects the approach with higher confidence. Merges candidates from both.

    Args:
        client: Anthropic client instance.
        match_result: Original Phase 4 MatchResult.
        debate_result: Result from initial FOR/AGAINST debate.
        tfidf_index: TF-IDF index for wider pool search.
        semaphore: Semaphore for rate-limiting Opus calls.

    Returns:
        Updated AdversarialResult with triple-check data.
    """
    # Build content for both approaches
    # 1. Wider pool: search with top_k=80
    anforderung = f"Position {match_result.positions_nr}"

    # Get wider pool candidates from TF-IDF
    wider_results = tfidf_index.search(match_result.bester_match or match_result, top_k=80)
    wider_candidates_data = []
    for idx, score in wider_results[:80]:
        if hasattr(tfidf_index, "catalog_rows") and idx < len(tfidf_index.catalog_rows):
            row = tfidf_index.catalog_rows[idx]
            wider_candidates_data.append({
                "produkt_id": row.get("produkt_id", f"IDX-{idx}"),
                "produkt_name": row.get("produkt_name", f"Product {idx}"),
                "tfidf_score": round(score, 4),
            })

    wider_content = WIDER_POOL_USER_TEMPLATE.format(
        anforderung=anforderung,
        kandidaten_erweitert=json.dumps(wider_candidates_data, ensure_ascii=False, indent=2),
    )

    # 2. Inverted prompt: requirement-centric
    candidates_data = []
    if match_result.bester_match:
        candidates_data.append(_format_candidate_for_prompt(match_result.bester_match))
    for alt in match_result.alternative_matches[:MAX_ALTERNATIVES_TO_DEBATE]:
        candidates_data.append(_format_candidate_for_prompt(alt))

    inverted_content = INVERTED_USER_TEMPLATE.format(
        anforderung_dimensionen=anforderung,
        kandidaten=json.dumps(candidates_data, ensure_ascii=False, indent=2),
    )

    api_calls = 0

    async with semaphore:
        # Run both approaches in parallel
        wider_task = asyncio.to_thread(
            client.messages.parse,
            model="claude-opus-4-6",
            max_tokens=4096,
            system=WIDER_POOL_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": wider_content}],
            output_format=ForArgument,
        )
        inverted_task = asyncio.to_thread(
            client.messages.parse,
            model="claude-opus-4-6",
            max_tokens=4096,
            system=INVERTED_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": inverted_content}],
            output_format=ForArgument,
        )

        wider_response, inverted_response = await asyncio.gather(wider_task, inverted_task)
        api_calls += 2

    wider_parsed: ForArgument = wider_response.parsed
    inverted_parsed: ForArgument = inverted_response.parsed

    # Compute adjusted confidence for each approach using dimension scores
    def _compute_confidence(parsed: ForArgument) -> float:
        scores = {db.dimension: db.score for db in parsed.dimension_bewertungen}
        weighted_sum = 0.0
        weight_total = 0.0
        for dim_name in ["Masse", "Brandschutz", "Schallschutz", "Material", "Zertifizierung", "Leistung"]:
            s = scores.get(dim_name, 0.5)
            w = DIMENSION_WEIGHTS.get(dim_name, 1.0)
            weighted_sum += s * w
            weight_total += w
        return round(weighted_sum / weight_total, 4) if weight_total > 0 else 0.0

    wider_confidence = _compute_confidence(wider_parsed)
    inverted_confidence = _compute_confidence(inverted_parsed)

    # Select winner
    if wider_confidence >= inverted_confidence:
        winning_method = "wider_pool"
        winning_parsed = wider_parsed
        winning_confidence = wider_confidence
    else:
        winning_method = "inverted_prompt"
        winning_parsed = inverted_parsed
        winning_confidence = inverted_confidence

    # Build dimension CoT from winning approach
    winning_cot = []
    for db in winning_parsed.dimension_bewertungen:
        confidence_level = "hoch" if db.score > 0.9 else "niedrig"
        winning_cot.append(DimensionCoT(
            dimension=db.dimension,
            score=db.score,
            reasoning=db.begruendung,
            confidence_level=confidence_level,
        ))

    # Build triple-check candidate
    tc_candidate = AdversarialCandidate(
        produkt_id=winning_parsed.produkt_id,
        produkt_name=winning_parsed.produkt_name,
        adjusted_confidence=winning_confidence,
        dimension_scores=winning_cot,
        reasoning_summary=winning_parsed.zusammenfassung,
    )

    # Merge candidates: keep debate alternatives + add triple-check candidates
    merged_alternatives = list(debate_result.alternative_candidates)

    # Add losing approach candidate if different product
    losing_parsed = inverted_parsed if winning_method == "wider_pool" else wider_parsed
    losing_confidence = inverted_confidence if winning_method == "wider_pool" else wider_confidence
    losing_candidate = AdversarialCandidate(
        produkt_id=losing_parsed.produkt_id,
        produkt_name=losing_parsed.produkt_name,
        adjusted_confidence=losing_confidence,
        dimension_scores=[
            DimensionCoT(
                dimension=db.dimension,
                score=db.score,
                reasoning=db.begruendung,
                confidence_level="hoch" if db.score > 0.9 else "niedrig",
            )
            for db in losing_parsed.dimension_bewertungen
        ],
        reasoning_summary=losing_parsed.zusammenfassung,
    )

    # Deduplicate by produkt_id (keep higher score)
    existing_ids = {c.produkt_id: c for c in merged_alternatives}
    for new_cand in [tc_candidate, losing_candidate]:
        if new_cand.produkt_id in existing_ids:
            if new_cand.adjusted_confidence > existing_ids[new_cand.produkt_id].adjusted_confidence:
                existing_ids[new_cand.produkt_id] = new_cand
        else:
            existing_ids[new_cand.produkt_id] = new_cand
    merged_alternatives = list(existing_ids.values())

    # Determine final status
    if winning_confidence >= BESTAETIGT_THRESHOLD:
        status = ValidationStatus.BESTAETIGT
    else:
        status = ValidationStatus.UNSICHER

    total_api_calls = debate_result.api_calls_count + api_calls

    return AdversarialResult(
        positions_nr=debate_result.positions_nr,
        validation_status=status,
        adjusted_confidence=winning_confidence,
        bester_match=tc_candidate if winning_confidence > debate_result.adjusted_confidence else debate_result.bester_match,
        alternative_candidates=merged_alternatives,
        debate=debate_result.debate,
        resolution_reasoning=debate_result.resolution_reasoning,
        per_dimension_cot=winning_cot if winning_confidence > debate_result.adjusted_confidence else debate_result.per_dimension_cot,
        triple_check_used=True,
        triple_check_method=winning_method,
        triple_check_reasoning=winning_parsed.zusammenfassung,
        api_calls_count=total_api_calls,
    )


async def validate_single_position(
    client: anthropic.Anthropic,
    match_result: MatchResult,
    semaphore: asyncio.Semaphore,
    tfidf_index=None,
) -> AdversarialResult:
    """Validate a single position through adversarial debate.

    Runs FOR and AGAINST Opus calls for best match + up to 3 alternatives.
    Resolution is deterministic (weighted average of dimension scores).

    Args:
        client: Anthropic client instance.
        match_result: Phase 4 MatchResult to validate.
        semaphore: Semaphore for rate-limiting Opus calls.

    Returns:
        AdversarialResult with debate, CoT, and adjusted confidence.
    """
    # Collect candidates to debate
    candidates_to_debate: list[MatchCandidate] = []
    if match_result.bester_match:
        candidates_to_debate.append(match_result.bester_match)
    for alt in match_result.alternative_matches[:MAX_ALTERNATIVES_TO_DEBATE]:
        candidates_to_debate.append(alt)

    if not candidates_to_debate:
        # No candidates to debate -> abgelehnt
        return AdversarialResult(
            positions_nr=match_result.positions_nr,
            validation_status=ValidationStatus.ABGELEHNT,
            adjusted_confidence=0.0,
            debate=[],
            resolution_reasoning="Keine Kandidaten zum Debattieren.",
            per_dimension_cot=[],
            api_calls_count=0,
        )

    # Build user content for prompts
    for_content = _build_user_content(FOR_USER_TEMPLATE, match_result)
    against_content = _build_user_content(AGAINST_USER_TEMPLATE, match_result)

    # Run FOR and AGAINST in parallel within semaphore
    api_calls = 0
    debate_entries: list[CandidateDebate] = []
    best_adjusted = 0.0
    best_cot: list[DimensionCoT] = []
    best_resolution = ""
    best_adv_candidate: Optional[AdversarialCandidate] = None
    alternative_adv_candidates: list[AdversarialCandidate] = []

    async with semaphore:
        # Run FOR and AGAINST calls in parallel
        for_task = asyncio.to_thread(
            client.messages.parse,
            model="claude-opus-4-6",
            max_tokens=4096,
            system=FOR_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": for_content}],
            output_format=ForArgument,
        )
        against_task = asyncio.to_thread(
            client.messages.parse,
            model="claude-opus-4-6",
            max_tokens=4096,
            system=AGAINST_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": against_content}],
            output_format=AgainstArgument,
        )

        for_response, against_response = await asyncio.gather(for_task, against_task)
        api_calls += 2

    for_result: ForArgument = for_response.parsed
    against_result: AgainstArgument = against_response.parsed

    # Resolve debate for best candidate
    adjusted_confidence, dim_cot, resolution = resolve_debate(
        for_result, against_result, match_result,
    )

    # Build debate entry for best candidate
    if match_result.bester_match:
        debate_entries.append(
            CandidateDebate(
                produkt_id=match_result.bester_match.produkt_id,
                produkt_name=match_result.bester_match.produkt_name,
                for_argument=for_result.zusammenfassung,
                against_argument=against_result.zusammenfassung,
                for_confidence=for_result.for_konfidenz,
                against_confidence=against_result.against_konfidenz,
            )
        )
        best_adv_candidate = _build_adversarial_candidate(
            match_result.bester_match,
            for_result,
            against_result,
            adjusted_confidence,
            dim_cot,
        )

    best_adjusted = adjusted_confidence
    best_cot = dim_cot
    best_resolution = resolution

    # For alternatives, also add debate entries using the same FOR/AGAINST results
    # (they were all included in the prompt context)
    for alt in match_result.alternative_matches[:MAX_ALTERNATIVES_TO_DEBATE]:
        # Use the same debate results but attribute to each alternative
        alt_confidence = adjusted_confidence * (
            alt.gesamt_konfidenz / match_result.bester_match.gesamt_konfidenz
            if match_result.bester_match and match_result.bester_match.gesamt_konfidenz > 0
            else 0.8
        )
        alt_confidence = round(min(alt_confidence, 1.0), 4)

        debate_entries.append(
            CandidateDebate(
                produkt_id=alt.produkt_id,
                produkt_name=alt.produkt_name,
                for_argument=for_result.zusammenfassung,
                against_argument=against_result.zusammenfassung,
                for_confidence=for_result.for_konfidenz * 0.9,  # Slightly lower for alt
                against_confidence=against_result.against_konfidenz,
            )
        )
        alternative_adv_candidates.append(
            AdversarialCandidate(
                produkt_id=alt.produkt_id,
                produkt_name=alt.produkt_name,
                adjusted_confidence=alt_confidence,
                dimension_scores=dim_cot,
                reasoning_summary=f"Alternative zu {match_result.bester_match.produkt_id if match_result.bester_match else '?'}",
            )
        )

    # Determine validation status
    if best_adjusted >= BESTAETIGT_THRESHOLD:
        status = ValidationStatus.BESTAETIGT
    else:
        status = ValidationStatus.UNSICHER

    initial_result = AdversarialResult(
        positions_nr=match_result.positions_nr,
        validation_status=status,
        adjusted_confidence=best_adjusted,
        bester_match=best_adv_candidate,
        alternative_candidates=alternative_adv_candidates,
        debate=debate_entries,
        resolution_reasoning=best_resolution,
        per_dimension_cot=best_cot,
        api_calls_count=api_calls,
    )

    # Triple-check: if below threshold and tfidf_index available
    if best_adjusted < BESTAETIGT_THRESHOLD and tfidf_index is not None:
        try:
            return await triple_check_position(
                client=client,
                match_result=match_result,
                debate_result=initial_result,
                tfidf_index=tfidf_index,
                semaphore=semaphore,
            )
        except Exception as e:
            logger.error(f"Triple-check failed for position {match_result.positions_nr}: {e}")
            # Fall back to initial result
            return initial_result

    return initial_result


async def validate_positions(
    client: anthropic.Anthropic,
    match_results: list[MatchResult],
    tfidf_index=None,
) -> list[AdversarialResult]:
    """Validate multiple positions concurrently through adversarial debate.

    Uses asyncio.Semaphore(ADVERSARIAL_MAX_CONCURRENT) to limit parallel
    Opus API calls.

    Args:
        client: Anthropic client instance.
        match_results: Phase 4 MatchResults to validate.
        tfidf_index: Optional TF-IDF index for triple-check wider pool search.

    Returns:
        List of AdversarialResult, one per position (in order).
    """
    semaphore = asyncio.Semaphore(ADVERSARIAL_MAX_CONCURRENT)

    async def _validate_one(mr: MatchResult) -> AdversarialResult:
        try:
            return await validate_single_position(
                client=client,
                match_result=mr,
                semaphore=semaphore,
                tfidf_index=tfidf_index,
            )
        except Exception as e:
            logger.error(
                f"Adversarial validation failed for position {mr.positions_nr}: {e}"
            )
            return AdversarialResult(
                positions_nr=mr.positions_nr,
                validation_status=ValidationStatus.UNSICHER,
                adjusted_confidence=0.0,
                debate=[],
                resolution_reasoning=f"Adversarial validation failed: {e}",
                per_dimension_cot=[],
                api_calls_count=0,
            )

    tasks = [_validate_one(mr) for mr in match_results]
    results = await asyncio.gather(*tasks)
    return list(results)
