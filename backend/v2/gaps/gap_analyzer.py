"""
Gap analysis engine: three-track processing based on adversarial validation status.

Pipeline per position:
  - bestaetigt: Opus call for non-perfect dimensions only (score < 1.0)
  - unsicher: Full Opus call for all dimensions
  - abgelehnt: Text summary only, no per-dimension breakdown

Uses asyncio.Semaphore(3) for concurrent Opus calls. Applies safety
auto-escalation post-processing. Searches for gap-weighted TF-IDF
alternatives with bidirectional cross-references.
"""

import asyncio
import logging
from typing import Optional

import anthropic

from v2.gaps.gap_prompts import (
    GAP_ABGELEHNT_SYSTEM_PROMPT,
    GAP_ABGELEHNT_USER_TEMPLATE,
    GAP_SYSTEM_PROMPT,
    GAP_USER_TEMPLATE,
)
from v2.schemas.adversarial import (
    AdversarialResult,
    DimensionCoT,
    ValidationStatus,
)
from v2.schemas.extraction import ExtractedDoorPosition
from v2.schemas.gaps import (
    AlternativeProduct,
    GapAnalysisResponse,
    GapDimension,
    GapItem,
    GapReport,
    GapSeverity,
    apply_safety_escalation,
)
from v2.schemas.matching import MatchResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GAP_MAX_CONCURRENT = 3
ABGELEHNT_MIN_COVERAGE = 0.3
MAX_ALTERNATIVES = 3
GAP_BOOST_MULTIPLIER = 2.0

SAFETY_DIMENSIONS = {GapDimension.BRANDSCHUTZ, GapDimension.SCHALLSCHUTZ}

# Mapping from GapDimension to TF-IDF catalog field names for boosting
DIMENSION_TO_TFIDF_FIELDS: dict[GapDimension, list[str]] = {
    GapDimension.BRANDSCHUTZ: ["brandschutzklasse"],
    GapDimension.SCHALLSCHUTZ: ["schallschutz", "tuerrohling"],
    GapDimension.MASSE: ["lichtmass"],
    GapDimension.MATERIAL: ["material"],
    GapDimension.ZERTIFIZIERUNG: ["widerstandsklasse"],
    GapDimension.LEISTUNG: ["kategorie", "produktegruppen"],
}

# Minimum number of populated technical fields for detailed gap analysis
MIN_TECHNICAL_FIELDS = 2


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _format_position_for_prompt(position: ExtractedDoorPosition) -> str:
    """Format extracted door position as compact text for prompt injection.

    Skips None/empty fields. Uses key technical fields only.
    """
    parts: list[str] = []
    if position.positions_bezeichnung:
        parts.append(f"Bezeichnung: {position.positions_bezeichnung}")
    if position.breite_mm and position.hoehe_mm:
        parts.append(f"Masse: {position.breite_mm}x{position.hoehe_mm}mm")
    if position.brandschutz_klasse:
        parts.append(f"Brandschutz: {position.brandschutz_klasse.value}")
    if position.brandschutz_freitext:
        parts.append(f"Brandschutz (Text): {position.brandschutz_freitext}")
    if position.schallschutz_db:
        parts.append(f"Schallschutz: {position.schallschutz_db}dB")
    if position.schallschutz_klasse:
        parts.append(f"Schallschutzklasse: {position.schallschutz_klasse.value}")
    if position.material_blatt:
        parts.append(f"Material: {position.material_blatt.value}")
    if position.einbruchschutz_klasse:
        parts.append(f"Einbruchschutz: {position.einbruchschutz_klasse}")
    if position.oeffnungsart:
        parts.append(f"Oeffnungsart: {position.oeffnungsart.value}")
    if position.anzahl_fluegel:
        parts.append(f"Fluegel: {position.anzahl_fluegel}")
    if position.glasausschnitt:
        parts.append("Glasausschnitt: ja")
    if position.tuerblatt_ausfuehrung:
        parts.append(f"Tuerblatt: {position.tuerblatt_ausfuehrung}")
    if position.bemerkungen:
        parts.append(f"Bemerkungen: {position.bemerkungen}")
    return "\n".join(parts) if parts else "Keine Details verfuegbar"


def _format_product_for_prompt(product_fields: dict) -> str:
    """Format matched product fields as compact text for prompt injection."""
    parts: list[str] = []
    for key, val in product_fields.items():
        if key == "row_index":
            continue
        parts.append(f"{key}: {val}")
    return "\n".join(parts) if parts else "Keine Produktdaten verfuegbar"


def _format_dimension_cot(cot_list: list[DimensionCoT]) -> str:
    """Format Phase 5 CoT as context string for gap analysis prompt."""
    if not cot_list:
        return "Keine Dimensionsbewertung verfuegbar"
    parts: list[str] = []
    for cot in cot_list:
        parts.append(
            f"- {cot.dimension}: Score={cot.score:.2f} "
            f"({cot.confidence_level}) - {cot.reasoning}"
        )
    return "\n".join(parts)


def _count_technical_fields(position: ExtractedDoorPosition) -> int:
    """Count how many technical fields are populated on a position."""
    count = 0
    technical_attrs = [
        "breite_mm", "hoehe_mm", "brandschutz_klasse", "brandschutz_freitext",
        "schallschutz_db", "schallschutz_klasse", "material_blatt",
        "einbruchschutz_klasse", "oeffnungsart", "tuerblatt_ausfuehrung",
    ]
    for attr in technical_attrs:
        if getattr(position, attr, None) is not None:
            count += 1
    return count


def build_gap_weighted_query(
    position: ExtractedDoorPosition,
    gaps: list[GapItem],
) -> str:
    """Build TF-IDF query with boosted weights for gap dimensions.

    For each gap dimension, repeat the corresponding TF-IDF fields
    GAP_BOOST_MULTIPLIER times more than the standard weight.
    """
    gap_dimensions = {g.dimension for g in gaps}
    parts: list[str] = []

    # Standard fields (same as CatalogTfidfIndex._build_query_from_position)
    if position.brandschutz_klasse:
        base = f"Brandschutzklasse:{position.brandschutz_klasse.value}"
        repeat = 4
        if GapDimension.BRANDSCHUTZ in gap_dimensions:
            repeat = int(repeat * GAP_BOOST_MULTIPLIER)
        parts.extend([base] * repeat)
    if position.brandschutz_freitext:
        parts.append(position.brandschutz_freitext)

    if position.schallschutz_db:
        base = f"Tuerrohling:{position.schallschutz_db}dB"
        repeat = 3
        if GapDimension.SCHALLSCHUTZ in gap_dimensions:
            repeat = int(repeat * GAP_BOOST_MULTIPLIER)
        parts.extend([base] * repeat)
    if position.schallschutz_klasse:
        parts.append(f"Schallschutz:{position.schallschutz_klasse.value}")

    if position.breite_mm and position.hoehe_mm:
        base = f"Lichtmass:{position.breite_mm}x{position.hoehe_mm}mm"
        repeat = 2
        if GapDimension.MASSE in gap_dimensions:
            repeat = int(repeat * GAP_BOOST_MULTIPLIER)
        parts.extend([base] * repeat)

    if position.material_blatt:
        base = f"Material:{position.material_blatt.value}"
        repeat = 2
        if GapDimension.MATERIAL in gap_dimensions:
            repeat = int(repeat * GAP_BOOST_MULTIPLIER)
        parts.extend([base] * repeat)

    if position.einbruchschutz_klasse:
        base = f"Widerstandsklasse:{position.einbruchschutz_klasse}"
        repeat = 3
        if GapDimension.ZERTIFIZIERUNG in gap_dimensions:
            repeat = int(repeat * GAP_BOOST_MULTIPLIER)
        parts.extend([base] * repeat)

    if position.oeffnungsart:
        parts.append(f"Oeffnungsart:{position.oeffnungsart.value}")
    if position.anzahl_fluegel:
        parts.append(f"Fluegel:{position.anzahl_fluegel}")
    if position.positions_bezeichnung:
        parts.append(position.positions_bezeichnung)
    if position.tuerblatt_ausfuehrung:
        parts.append(position.tuerblatt_ausfuehrung)

    if parts:
        return " ".join(parts)
    return "Tuer Rahmentuere Brandschutz Schallschutz Produkt Standard"


def search_alternatives_for_gaps(
    position: ExtractedDoorPosition,
    gaps: list[GapItem],
    tfidf_index,
    matched_product_id: Optional[str],
    top_k: int = 20,
    is_abgelehnt: bool = False,
) -> list[AlternativeProduct]:
    """Search for alternative products using gap-weighted TF-IDF.

    Args:
        position: The door position with requirements.
        gaps: Identified gaps to use for boosting.
        tfidf_index: CatalogTfidfIndex for searching.
        matched_product_id: Product ID to exclude (the current match).
        top_k: Number of TF-IDF results to consider.
        is_abgelehnt: If True, filter to >30% coverage only.

    Returns:
        Up to MAX_ALTERNATIVES AlternativeProduct instances.
    """
    if tfidf_index is None:
        return []

    # Search with gap-weighted query
    search_results = tfidf_index.search(position, top_k=top_k)

    gap_dimension_values = [g.dimension.value for g in gaps]
    total_gaps = len(gaps) if gaps else 1  # Avoid division by zero

    alternatives: list[AlternativeProduct] = []
    for row_idx, _score in search_results:
        if len(alternatives) >= MAX_ALTERNATIVES:
            break

        fields = tfidf_index.extract_candidate_fields(row_idx)
        produkt_id = fields.get("Kostentraeger", f"IDX-{row_idx}")

        # Skip the matched product
        if matched_product_id and produkt_id == matched_product_id:
            continue

        produkt_name = fields.get("Produktegruppen", f"Produkt {row_idx}")

        # Determine which gaps this candidate closes
        geschlossene = []
        verbleibende = []
        for gap in gaps:
            # Simple heuristic: check if the candidate has the relevant field
            closes = _candidate_closes_gap(gap, fields)
            if closes:
                geschlossene.append(gap.dimension.value)
            else:
                verbleibende.append(gap.dimension.value)

        teilweise_deckung = len(geschlossene) / total_gaps if total_gaps > 0 else 0.0

        # For abgelehnt: filter to >30% coverage
        if is_abgelehnt and teilweise_deckung < ABGELEHNT_MIN_COVERAGE:
            continue

        alternatives.append(
            AlternativeProduct(
                produkt_id=produkt_id,
                produkt_name=produkt_name,
                teilweise_deckung=round(teilweise_deckung, 2),
                verbleibende_gaps=verbleibende,
                geschlossene_gaps=geschlossene,
            )
        )

    return alternatives


def _candidate_closes_gap(gap: GapItem, candidate_fields: dict) -> bool:
    """Check if a candidate product closes a specific gap.

    Uses simple field presence/value comparison heuristic.
    """
    dim = gap.dimension
    anforderung = gap.anforderung_wert.lower().strip()

    if dim == GapDimension.BRANDSCHUTZ:
        val = candidate_fields.get("Brandschutzklasse", "").lower()
        return anforderung in val or val in anforderung if val else False
    elif dim == GapDimension.SCHALLSCHUTZ:
        val = candidate_fields.get("Tuerrohling (dB)", "").lower()
        return anforderung in val or val in anforderung if val else False
    elif dim == GapDimension.MASSE:
        val = candidate_fields.get("Lichtmass max. B x H in mm", "").lower()
        return bool(val)  # Has a dimension spec at all
    elif dim == GapDimension.MATERIAL:
        val = candidate_fields.get("Tuerblatt / Verglasungsart / Rollkasten", "").lower()
        return anforderung in val if val else False
    elif dim == GapDimension.ZERTIFIZIERUNG:
        val = candidate_fields.get("Widerstandsklasse", "").lower()
        return anforderung in val or val in anforderung if val else False
    elif dim == GapDimension.LEISTUNG:
        val = candidate_fields.get("Produktegruppen", "").lower()
        return bool(val)
    return False


def _cross_reference_gaps_and_alternatives(
    gaps: list[GapItem],
    alternatives: list[AlternativeProduct],
) -> None:
    """Mutate gap items to set gap_geschlossen_durch from alternatives.

    Ensures referential integrity: only produkt_ids in alternativen list
    are referenced in gap_geschlossen_durch.
    """
    alt_ids = {alt.produkt_id for alt in alternatives}
    for gap in gaps:
        closing_ids = []
        for alt in alternatives:
            if gap.dimension.value in alt.geschlossene_gaps:
                closing_ids.append(alt.produkt_id)
        # Only reference products that are actually in the alternatives list
        gap.gap_geschlossen_durch = [
            pid for pid in closing_ids if pid in alt_ids
        ]


# ---------------------------------------------------------------------------
# Core async functions
# ---------------------------------------------------------------------------


async def analyze_single_position_gaps(
    client: anthropic.Anthropic,
    match_result: MatchResult,
    adversarial_result: AdversarialResult,
    tfidf_index,
    semaphore: asyncio.Semaphore,
    position: Optional[ExtractedDoorPosition] = None,
) -> GapReport:
    """Analyze gaps for a single position.

    Three-track processing based on adversarial_result.validation_status:
    a) BESTAETIGT: Only analyze dimensions with score < 1.0
    b) UNSICHER: Full analysis all dimensions
    c) ABGELEHNT: Text summary only, no per-dimension breakdown

    Args:
        client: Anthropic client instance.
        match_result: Phase 4 MatchResult.
        adversarial_result: Phase 5 AdversarialResult.
        tfidf_index: CatalogTfidfIndex for alternative search.
        semaphore: Semaphore for rate-limiting Opus calls.
        position: Optional ExtractedDoorPosition for prompt formatting.

    Returns:
        GapReport with categorized gaps, alternatives, and cross-references.
    """
    pos_nr = adversarial_result.positions_nr
    status = adversarial_result.validation_status

    # Check for insufficient specification data
    if position and _count_technical_fields(position) < MIN_TECHNICAL_FIELDS:
        return GapReport(
            positions_nr=pos_nr,
            zusammenfassung="Unzureichende Spezifikationsdaten fuer detaillierte Gap-Analyse",
            validation_status=status.value if hasattr(status, "value") else str(status),
        )

    # --- Track C: ABGELEHNT ---
    if status == ValidationStatus.ABGELEHNT:
        return await _analyze_abgelehnt(
            client, pos_nr, position, tfidf_index, semaphore,
        )

    # --- Track A/B: BESTAETIGT / UNSICHER ---
    return await _analyze_bestaetigt_unsicher(
        client, match_result, adversarial_result, tfidf_index, semaphore, position,
    )


async def _analyze_abgelehnt(
    client: anthropic.Anthropic,
    pos_nr: str,
    position: Optional[ExtractedDoorPosition],
    tfidf_index,
    semaphore: asyncio.Semaphore,
) -> GapReport:
    """Handle abgelehnt positions: text summary only."""
    anforderung_felder = (
        _format_position_for_prompt(position)
        if position
        else f"Position {pos_nr} (keine Details)"
    )

    user_content = GAP_ABGELEHNT_USER_TEMPLATE.format(
        positions_nr=pos_nr,
        anforderung_felder=anforderung_felder,
    )

    try:
        async with semaphore:
            response = await asyncio.to_thread(
                client.messages.create,
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                system=GAP_ABGELEHNT_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_content}],
            )
        zusammenfassung = response.content[0].text if response.content else (
            "Kein passendes Katalogprodukt gefunden."
        )
    except Exception as e:
        logger.error(f"Abgelehnt gap analysis failed for {pos_nr}: {e}")
        zusammenfassung = f"Gap-Analyse fehlgeschlagen: {e}"

    # Search alternatives even for abgelehnt (filter >30% coverage)
    alternatives = []
    if position and tfidf_index:
        # Create dummy gaps from common dimensions for search boosting
        dummy_gaps = [
            GapItem(
                dimension=GapDimension.BRANDSCHUTZ,
                schweregrad=GapSeverity.MAJOR,
                anforderung_wert="unbekannt",
                abweichung_beschreibung="Kein Match",
            ),
            GapItem(
                dimension=GapDimension.MASSE,
                schweregrad=GapSeverity.MAJOR,
                anforderung_wert="unbekannt",
                abweichung_beschreibung="Kein Match",
            ),
        ]
        alternatives = search_alternatives_for_gaps(
            position, dummy_gaps, tfidf_index,
            matched_product_id=None,
            is_abgelehnt=True,
        )

    return GapReport(
        positions_nr=pos_nr,
        gaps=[],
        alternativen=alternatives,
        zusammenfassung=zusammenfassung,
        validation_status=ValidationStatus.ABGELEHNT.value,
    )


async def _analyze_bestaetigt_unsicher(
    client: anthropic.Anthropic,
    match_result: MatchResult,
    adversarial_result: AdversarialResult,
    tfidf_index,
    semaphore: asyncio.Semaphore,
    position: Optional[ExtractedDoorPosition],
) -> GapReport:
    """Handle bestaetigt/unsicher positions: Opus call for gap analysis."""
    pos_nr = adversarial_result.positions_nr
    status = adversarial_result.validation_status
    cot_list = adversarial_result.per_dimension_cot

    # For bestaetigt: filter to non-perfect dimensions only
    if status == ValidationStatus.BESTAETIGT:
        non_perfect = [c for c in cot_list if c.score < 1.0]
        if not non_perfect:
            return GapReport(
                positions_nr=pos_nr,
                zusammenfassung="Alle Dimensionen perfekt bewertet, keine Luecken identifiziert.",
                validation_status=status.value,
            )
        filter_hinweis = (
            "WICHTIG: Analysiere NUR die folgenden Dimensionen mit Score < 1.0: "
            + ", ".join(c.dimension for c in non_perfect)
            + ". Alle anderen Dimensionen sind perfekt bewertet."
        )
        relevant_cot = non_perfect
    else:
        filter_hinweis = "Analysiere ALLE Dimensionen vollstaendig."
        relevant_cot = cot_list

    # Extract product fields from TF-IDF index
    product_fields: dict = {}
    matched_product_id: Optional[str] = None
    if match_result.bester_match and tfidf_index:
        # Try to find the product in the index by ID
        matched_product_id = match_result.bester_match.produkt_id
        # Use extract_candidate_fields if we can find the row
        product_fields = {"produkt_id": matched_product_id, "produkt_name": match_result.bester_match.produkt_name}

    anforderung_felder = (
        _format_position_for_prompt(position)
        if position
        else f"Position {pos_nr} (keine Details)"
    )

    user_content = GAP_USER_TEMPLATE.format(
        positions_nr=pos_nr,
        validation_status=status.value,
        anforderung_felder=anforderung_felder,
        produkt_felder=_format_product_for_prompt(product_fields),
        dimension_cot=_format_dimension_cot(relevant_cot),
        filter_hinweis=filter_hinweis,
    )

    try:
        async with semaphore:
            response = await asyncio.to_thread(
                client.messages.parse,
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                system=GAP_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_content}],
                output_format=GapAnalysisResponse,
            )
        parsed: GapAnalysisResponse = response.parsed
    except Exception as e:
        logger.error(f"Gap analysis Opus call failed for {pos_nr}: {e}")
        return GapReport(
            positions_nr=pos_nr,
            zusammenfassung=f"Gap-Analyse fehlgeschlagen: {e}",
            validation_status=status.value if hasattr(status, "value") else str(status),
        )

    # Convert GapAnalysisResponse items to GapItem instances
    gaps = [
        GapItem(
            dimension=item.dimension,
            schweregrad=item.schweregrad,
            anforderung_wert=item.anforderung_wert,
            katalog_wert=item.katalog_wert,
            abweichung_beschreibung=item.abweichung_beschreibung,
            kundenvorschlag=item.kundenvorschlag,
            technischer_hinweis=item.technischer_hinweis,
        )
        for item in parsed.gaps
    ]

    # Apply safety auto-escalation
    gaps = apply_safety_escalation(gaps)

    # Search alternatives
    alternatives = []
    if position and tfidf_index and gaps:
        alternatives = search_alternatives_for_gaps(
            position, gaps, tfidf_index, matched_product_id,
        )

    # Cross-reference gaps and alternatives
    _cross_reference_gaps_and_alternatives(gaps, alternatives)

    return GapReport(
        positions_nr=pos_nr,
        gaps=gaps,
        alternativen=alternatives,
        zusammenfassung=parsed.zusammenfassung,
        validation_status=status.value if hasattr(status, "value") else str(status),
    )


async def analyze_gaps(
    client: anthropic.Anthropic,
    match_results: list[MatchResult],
    adversarial_results: list[AdversarialResult],
    tfidf_index,
    positions: Optional[list[ExtractedDoorPosition]] = None,
) -> list[GapReport]:
    """Batch gap analysis for all positions.

    Matches adversarial_results to match_results by positions_nr.
    Uses asyncio.gather for concurrency with Semaphore(GAP_MAX_CONCURRENT).
    Wraps each call in try/except -- returns empty GapReport on failure.

    Args:
        client: Anthropic client instance.
        match_results: Phase 4 MatchResults.
        adversarial_results: Phase 5 AdversarialResults.
        tfidf_index: CatalogTfidfIndex for alternative search.
        positions: Optional list of ExtractedDoorPositions for prompt context.

    Returns:
        List of GapReport, one per adversarial result.
    """
    semaphore = asyncio.Semaphore(GAP_MAX_CONCURRENT)

    # Build lookup maps
    match_by_pos = {mr.positions_nr: mr for mr in match_results}
    position_by_pos = {}
    if positions:
        position_by_pos = {p.positions_nr: p for p in positions}

    async def _analyze_one(ar: AdversarialResult) -> GapReport:
        try:
            mr = match_by_pos.get(ar.positions_nr)
            if mr is None:
                return GapReport(
                    positions_nr=ar.positions_nr,
                    zusammenfassung="Kein MatchResult fuer diese Position gefunden.",
                    validation_status=ar.validation_status.value,
                )
            pos = position_by_pos.get(ar.positions_nr)
            return await analyze_single_position_gaps(
                client=client,
                match_result=mr,
                adversarial_result=ar,
                tfidf_index=tfidf_index,
                semaphore=semaphore,
                position=pos,
            )
        except Exception as e:
            logger.error(
                f"Gap analysis failed for position {ar.positions_nr}: {e}"
            )
            return GapReport(
                positions_nr=ar.positions_nr,
                zusammenfassung=f"Gap-Analyse fehlgeschlagen: {e}",
                validation_status=ar.validation_status.value
                if hasattr(ar.validation_status, "value")
                else str(ar.validation_status),
            )

    tasks = [_analyze_one(ar) for ar in adversarial_results]
    results = await asyncio.gather(*tasks)
    return list(results)
