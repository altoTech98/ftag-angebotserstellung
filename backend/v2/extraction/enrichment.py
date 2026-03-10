"""
Cross-document enrichment engine.

Fills empty fields from matched positions across documents,
upgrades low-confidence fields when another document has higher confidence,
and applies general specifications to matching positions.

All enrichment is tracked via FieldSource.enrichment_source and enrichment_type.
"""

import logging
from typing import Optional

from v2.schemas.common import BrandschutzKlasse, FieldSource, SchallschutzKlasse
from v2.schemas.extraction import (
    CrossDocMatch,
    DocumentEnrichmentStats,
    EnrichmentReport,
    ExtractedDoorPosition,
    GeneralSpec,
)

logger = logging.getLogger(__name__)

# Fields to skip during enrichment iteration
_SKIP_FIELDS = {"quellen", "positions_nr"}


def _get_field_value_str(pos: ExtractedDoorPosition, field_name: str) -> Optional[str]:
    """Get a field value as a comparable string, or None if not set."""
    val = getattr(pos, field_name, None)
    if val is None:
        return None
    if hasattr(val, "value"):  # Enum
        return val.value
    return str(val)


def _match_scope(pos: ExtractedDoorPosition, scope: str) -> bool:
    """Check if a position matches a GeneralSpec scope filter.

    Supported scope formats:
    - "all": matches everything
    - "geschoss==OG": matches positions with geschoss == "OG"
    - "field==value": generic equality check
    """
    if scope == "all":
        return True

    if "==" in scope:
        field, value = scope.split("==", 1)
        field = field.strip()
        value = value.strip()
        pos_val = getattr(pos, field, None)
        if pos_val is None:
            return False
        if hasattr(pos_val, "value"):
            return pos_val.value == value
        return str(pos_val) == value

    return False


def _try_set_enum_field(
    pos: ExtractedDoorPosition,
    field_name: str,
    value_str: str,
) -> Optional[ExtractedDoorPosition]:
    """Try to set a field value, handling enum conversion.

    Returns updated position or None if conversion fails.
    """
    field_info = pos.model_fields.get(field_name)
    if field_info is None:
        return None

    # Get the field's annotation to check for enum types
    annotation = field_info.annotation

    # Handle Optional[EnumType] by extracting inner type
    origin = getattr(annotation, "__origin__", None)
    if origin is not None:
        # It's a generic like Optional[X] = Union[X, None]
        args = getattr(annotation, "__args__", ())
        enum_types = [a for a in args if isinstance(a, type) and issubclass(a, type(None)) is False]
        for t in enum_types:
            if hasattr(t, "__members__"):
                # It's an enum - try to convert
                try:
                    enum_val = t(value_str)
                    return pos.model_copy(update={field_name: enum_val})
                except (ValueError, KeyError):
                    pass

    # Non-enum field: try direct set
    try:
        return pos.model_copy(update={field_name: value_str})
    except Exception:
        return None


def enrich_positions(
    matches: list[CrossDocMatch],
    all_positions: list[ExtractedDoorPosition],
    general_specs: Optional[list[GeneralSpec]] = None,
) -> tuple[list[ExtractedDoorPosition], EnrichmentReport]:
    """Enrich positions using cross-document data.

    For each auto_merge match (confidence >= 0.9):
    1. Gap fill: Copy non-None fields from secondary to empty fields in primary
    2. Confidence upgrade: Replace low-konfidenz (<0.7) with higher-konfidenz values
    3. Never downgrade high-confidence fields

    Then apply general specs to empty fields with konfidenz=0.7.

    Args:
        matches: Cross-document position matches.
        all_positions: Flat list of all positions (indices match CrossDocMatch).
        general_specs: Optional list of general specifications to apply.

    Returns:
        Tuple of (enriched positions, enrichment report).
    """
    # Work on copies
    enriched = [pos.model_copy(deep=True) for pos in all_positions]

    # Track stats
    total_felder_enriched = 0
    matched_position_indices: set[int] = set()
    doc_stats: dict[str, dict] = {}  # doc_name -> {matched, enriched, conflicts}

    # Phase 1: Process auto-merge matches (confidence >= 0.9)
    for match in matches:
        if not match.auto_merge:
            continue

        idx_a = match.position_a_index
        idx_b = match.position_b_index

        if idx_a >= len(enriched) or idx_b >= len(enriched):
            logger.warning(f"Match index out of range: {idx_a}, {idx_b}")
            continue

        matched_position_indices.add(idx_a)
        matched_position_indices.add(idx_b)

        pos_a = enriched[idx_a]
        pos_b = enriched[idx_b]

        # Enrich A from B and B from A
        felder_a = _enrich_one_from_other(pos_a, pos_b)
        felder_b = _enrich_one_from_other(pos_b, pos_a)

        enriched[idx_a] = pos_a
        enriched[idx_b] = pos_b

        total_felder_enriched += felder_a + felder_b

    # Phase 2: Apply general specs
    general_specs_applied = 0
    if general_specs:
        for spec in general_specs:
            for i, pos in enumerate(enriched):
                if _match_scope(pos, spec.scope):
                    applied = _apply_general_spec(pos, spec)
                    if applied > 0:
                        enriched[i] = pos
                        general_specs_applied += applied
                        total_felder_enriched += applied

    # Build enrichment report
    report = EnrichmentReport(
        total_positionen=len(all_positions),
        positionen_matched_cross_doc=len(matched_position_indices),
        felder_enriched=total_felder_enriched,
        konflikte_total=0,  # Conflicts are tracked by conflict_detector
        konflikte_critical=0,
        konflikte_major=0,
        konflikte_minor=0,
        general_specs_applied=general_specs_applied,
        dokument_stats=[],  # Simplified: per-doc stats would need doc tracking
        zusammenfassung=_build_summary(
            len(all_positions),
            len(matched_position_indices),
            total_felder_enriched,
            general_specs_applied,
        ),
    )

    logger.info(
        f"Enrichment: {total_felder_enriched} fields enriched, "
        f"{len(matched_position_indices)} positions matched, "
        f"{general_specs_applied} general specs applied"
    )

    return enriched, report


def _enrich_one_from_other(
    primary: ExtractedDoorPosition,
    secondary: ExtractedDoorPosition,
) -> int:
    """Enrich primary position from secondary. Modifies primary in place.

    Returns count of fields enriched.
    """
    fields_enriched = 0
    # Determine secondary document name from quellen
    secondary_doc = _get_doc_name(secondary)

    for field_name in primary.model_fields:
        if field_name in _SKIP_FIELDS:
            continue

        primary_val = getattr(primary, field_name)
        secondary_val = getattr(secondary, field_name)

        if secondary_val is None:
            continue

        primary_source = primary.quellen.get(field_name)
        secondary_source = secondary.quellen.get(field_name)

        # Gap fill: primary is None, secondary has value
        if primary_val is None:
            setattr(primary, field_name, secondary_val)
            new_source = FieldSource(
                dokument=secondary_doc,
                konfidenz=secondary_source.konfidenz if secondary_source else 0.7,
                enrichment_source=secondary_doc,
                enrichment_type="gap_fill",
            )
            if secondary_source:
                new_source = secondary_source.model_copy(update={
                    "enrichment_source": secondary_doc,
                    "enrichment_type": "gap_fill",
                })
            primary.quellen[field_name] = new_source
            fields_enriched += 1
            continue

        # Confidence upgrade: primary has low confidence, secondary has higher
        if primary_source and secondary_source:
            if (
                primary_source.konfidenz < 0.7
                and secondary_source.konfidenz >= 0.7
                and secondary_source.konfidenz > primary_source.konfidenz
            ):
                setattr(primary, field_name, secondary_val)
                primary.quellen[field_name] = secondary_source.model_copy(update={
                    "enrichment_source": secondary_doc,
                    "enrichment_type": "confidence_upgrade",
                })
                fields_enriched += 1

    return fields_enriched


def _apply_general_spec(
    pos: ExtractedDoorPosition,
    spec: GeneralSpec,
) -> int:
    """Apply a general spec to a position. Only fills empty fields.

    Returns count of fields applied.
    """
    applied = 0
    doc_name = spec.source.dokument if spec.source else "general_spec"

    for field_name, value_str in spec.affected_fields.items():
        current_val = getattr(pos, field_name, None)
        if current_val is not None:
            continue  # Do NOT override existing specific values

        # Try to set the field (handling enum conversion)
        updated = _try_set_enum_field(pos, field_name, value_str)
        if updated is not None:
            # Copy the value back to the original pos
            new_val = getattr(updated, field_name)
            setattr(pos, field_name, new_val)
            pos.quellen[field_name] = FieldSource(
                dokument=doc_name,
                konfidenz=spec.konfidenz,
                enrichment_source=doc_name,
                enrichment_type="general_spec",
            )
            applied += 1

    return applied


def _get_doc_name(pos: ExtractedDoorPosition) -> str:
    """Extract document name from a position's quellen."""
    for source in pos.quellen.values():
        if source.dokument:
            return source.dokument
    return "unknown"


def _build_summary(
    total: int,
    matched: int,
    enriched: int,
    general_specs: int,
) -> str:
    """Build human-readable enrichment summary for sales team."""
    parts = []
    if matched > 0:
        parts.append(f"{matched} Positionen dokumentuebergreifend zugeordnet")
    if enriched > 0:
        parts.append(f"{enriched} Felder ergaenzt")
    if general_specs > 0:
        parts.append(f"{general_specs} allgemeine Spezifikationen angewendet")

    if not parts:
        return f"Keine dokumentuebergreifende Anreicherung bei {total} Positionen."

    return f"Cross-Document Analyse: {', '.join(parts)}."
