"""
AI Matching Pipeline – Full Claude-based product matching for FTAG.

5-stage pipeline:
A) Deduplication – group identical door types by signature
B) Category classification – Claude assigns each unique type to a product category
C) Main product matching – Claude matches doors against category products (batched)
D) Accessory matching – Claude matches lock/glass/strike plate requirements (batched)
E) Result assembly – combine main + accessory matches, determine feasibility
"""

import logging
from typing import Callable, Optional

from services.catalog_index import (
    CatalogIndex,
    format_products_for_claude,
    get_catalog_index,
)
from services.claude_client import (
    classify_door_categories,
    match_main_products_batch,
    match_accessories_batch,
)

logger = logging.getLogger(__name__)

# Max door types per Claude batch call (main product matching)
BATCH_SIZE_MAIN = 8
# Max accessory requirements per batch call
BATCH_SIZE_ACCESSORY = 15


def _door_signature(door: dict) -> str:
    """Create a signature for grouping identical door types."""
    parts = [
        str(door.get("tuertyp") or ""),
        str(door.get("brandschutz") or ""),
        str(door.get("schallschutz") or ""),
        str(door.get("einbruchschutz") or ""),
        str(door.get("breite") or ""),
        str(door.get("hoehe") or ""),
        str(door.get("verglasung") or ""),
        str(door.get("oberflaechenbehandlung") or ""),
        str(door.get("schloss_typ") or ""),
        str(door.get("glas_typ") or ""),
        str(door.get("fluegel_anzahl") or ""),
        str(door.get("zargentyp") or ""),
    ]
    return "|".join(parts).lower()


def match_all(
    positions: list[dict],
    on_progress: Optional[Callable[[str], None]] = None,
) -> dict:
    """
    Full AI matching pipeline.

    Args:
        positions: List of door position dicts from normalization
        on_progress: Callback for progress updates

    Returns:
        Standard matching result dict with matched/partial/unmatched lists + summary
    """
    catalog = get_catalog_index()

    if not positions:
        return _empty_result()

    def progress(msg: str):
        logger.info(msg)
        if on_progress:
            on_progress(msg)

    # ── Stage A: Deduplication ──────────────────────────────
    progress(f"Deduplizierung von {len(positions)} Positionen...")
    sig_groups = {}      # signature -> [position_indices]
    sig_representative = {}  # signature -> first position dict

    for i, pos in enumerate(positions):
        sig = _door_signature(pos)
        if sig not in sig_groups:
            sig_groups[sig] = []
            sig_representative[sig] = pos
        sig_groups[sig].append(i)

    unique_doors = list(sig_representative.values())
    unique_sigs = list(sig_representative.keys())
    progress(
        f"Dedupliziert: {len(positions)} Positionen -> {len(unique_doors)} einzigartige Typen"
    )

    # ── Stage B: Category Classification ────────────────────
    progress(f"Kategorie-Klassifikation ({len(unique_doors)} Typen)...")
    category_results = classify_door_categories(
        unique_doors, catalog.main_category_names
    )

    # Map results back to signatures
    sig_category = {}  # signature -> category
    for result in category_results:
        idx = result.get("door_index", 0)
        if 0 <= idx < len(unique_sigs):
            cat = result.get("category", "Rahmentüre")
            # Validate category exists
            if cat not in catalog.main_category_names:
                # Try fuzzy match
                cat_lower = cat.lower()
                matched_cat = None
                for real_cat in catalog.main_category_names:
                    if cat_lower in real_cat.lower() or real_cat.lower() in cat_lower:
                        matched_cat = real_cat
                        break
                cat = matched_cat or catalog.main_category_names[0]
            sig_category[unique_sigs[idx]] = cat

    # Group unique doors by category
    doors_by_category = {}  # category -> [(sig, door)]
    for sig, door in zip(unique_sigs, unique_doors):
        cat = sig_category.get(sig, catalog.main_category_names[0])
        doors_by_category.setdefault(cat, []).append((sig, door))

    for cat, doors in doors_by_category.items():
        progress(f"  {cat}: {len(doors)} Typen")

    # ── Stage C: Main Product Matching ──────────────────────
    sig_match_result = {}  # signature -> match result dict

    for cat, door_list in doors_by_category.items():
        cat_products = catalog.get_main_by_category(cat)
        if not cat_products:
            # No products in this category -> all unmatched
            for sig, door in door_list:
                sig_match_result[sig] = {
                    "status": "nicht_machbar",
                    "matched_row": None,
                    "confidence": 0.0,
                    "reason": f"Keine Produkte in Kategorie '{cat}' verfügbar",
                    "zubehoer_bedarf": {},
                    "gap_hinweise": [f"Kategorie '{cat}' nicht im FTAG-Sortiment"],
                }
            continue

        products_text = format_products_for_claude(cat_products)

        # Process in batches
        for batch_start in range(0, len(door_list), BATCH_SIZE_MAIN):
            batch = door_list[batch_start:batch_start + BATCH_SIZE_MAIN]
            batch_doors = [door for _, door in batch]
            batch_sigs = [sig for sig, _ in batch]

            batch_end = min(batch_start + BATCH_SIZE_MAIN, len(door_list))
            progress(
                f"Hauptprodukt-Matching: {cat} ({batch_start + 1}-{batch_end}/{len(door_list)} Typen)..."
            )

            results = match_main_products_batch(
                batch_doors, products_text, cat
            )

            for result in results:
                idx = result.get("door_index", 0)
                if 0 <= idx < len(batch_sigs):
                    sig_match_result[batch_sigs[idx]] = result

    # ── Stage D: Accessory Matching ─────────────────────────
    # Collect all accessory requirements from main matching results
    accessory_reqs = {"Schloss": [], "Glas": [], "Schliessblech": []}

    for sig, match in sig_match_result.items():
        door = sig_representative[sig]
        zubehoer = match.get("zubehoer_bedarf", {})

        # Check both explicit requirements from door data and Claude's suggestions
        schloss_req = zubehoer.get("schloss") or door.get("schloss_typ") or door.get("beschlaege")
        glas_req = zubehoer.get("glas") or door.get("glas_typ") or door.get("verglasung")
        schliessblech_req = zubehoer.get("schliessblech") or door.get("schliessblech")

        if schloss_req:
            accessory_reqs["Schloss"].append({
                "sig": sig,
                "description": schloss_req,
                "door_ref": door.get("tuer_nr", door.get("position", "?")),
            })
        if glas_req:
            accessory_reqs["Glas"].append({
                "sig": sig,
                "description": glas_req,
                "door_ref": door.get("tuer_nr", door.get("position", "?")),
            })
        if schliessblech_req:
            accessory_reqs["Schliessblech"].append({
                "sig": sig,
                "description": schliessblech_req,
                "door_ref": door.get("tuer_nr", door.get("position", "?")),
            })

    sig_accessories = {}  # sig -> {"Schloss": result, "Glas": result, ...}

    for acc_type, reqs in accessory_reqs.items():
        if not reqs:
            continue

        zz_type = f"ZZ ({acc_type})"
        acc_products = catalog.get_accessories_by_type(zz_type)
        if not acc_products:
            for req in reqs:
                sig_accessories.setdefault(req["sig"], {})[acc_type] = {
                    "status": "gap",
                    "reason": f"Keine {acc_type}-Produkte im Katalog",
                }
            continue

        acc_text = format_products_for_claude(acc_products)

        for batch_start in range(0, len(reqs), BATCH_SIZE_ACCESSORY):
            batch = reqs[batch_start:batch_start + BATCH_SIZE_ACCESSORY]
            batch_end = min(batch_start + BATCH_SIZE_ACCESSORY, len(reqs))
            progress(
                f"Zubehör-Matching: {acc_type} ({batch_start + 1}-{batch_end}/{len(reqs)})..."
            )

            results = match_accessories_batch(batch, acc_text, acc_type)

            for result in results:
                idx = result.get("req_index", 0)
                if 0 <= idx < len(batch):
                    sig = batch[idx]["sig"]
                    sig_accessories.setdefault(sig, {})[acc_type] = result

    # ── Stage E: Result Assembly ────────────────────────────
    progress("Ergebnisse werden zusammengestellt...")

    matched = []
    partial = []
    unmatched = []

    for i, pos in enumerate(positions):
        sig = _door_signature(pos)
        main_result = sig_match_result.get(sig, {})
        acc_results = sig_accessories.get(sig, {})

        # Determine overall status
        main_status = main_result.get("status", "nicht_machbar")
        matched_row = main_result.get("matched_row")
        confidence = main_result.get("confidence", 0.0)
        reason = main_result.get("reason", "")

        # Get product detail if matched
        matched_products = []
        if matched_row is not None:
            detail = catalog.get_product_detail(matched_row)
            if detail:
                matched_products = [detail]

        # Build accessory info
        zubehoer_matched = []
        zubehoer_gap = []
        for acc_type, acc_result in acc_results.items():
            if acc_result.get("status") == "matched":
                acc_row = acc_result.get("matched_row")
                acc_detail = catalog.get_product_detail(acc_row) if acc_row is not None else {}
                zubehoer_matched.append({
                    "typ": acc_type,
                    "produkt": acc_detail,
                    "reason": acc_result.get("reason", ""),
                })
            else:
                zubehoer_gap.append({
                    "typ": acc_type,
                    "anforderung": acc_result.get("reason", ""),
                })

        # Gap items from main matching
        gap_items = list(main_result.get("gap_hinweise", []))
        for gap in zubehoer_gap:
            gap_items.append(f"{gap['typ']}: {gap['anforderung']}")

        # Determine final status
        if main_status == "machbar" and not zubehoer_gap:
            final_status = "matched"
        elif main_status == "machbar" and zubehoer_gap:
            final_status = "partial"
        elif main_status == "teilweise_machbar":
            final_status = "partial"
        else:
            final_status = "unmatched"

        result_entry = {
            "status": final_status,
            "confidence": round(confidence, 2),
            "position": pos.get("position", pos.get("tuer_nr", f"Pos {i+1}")),
            "beschreibung": pos.get("beschreibung", ""),
            "menge": pos.get("menge", 1),
            "einheit": pos.get("einheit", "Stk"),
            "matched_products": matched_products,
            "zubehoer_matched": zubehoer_matched,
            "zubehoer_gap": zubehoer_gap,
            "gap_items": gap_items,
            "reason": reason,
            "original_position": pos,
            "category": sig_category.get(sig, ""),
        }

        if final_status == "matched":
            matched.append(result_entry)
        elif final_status == "partial":
            partial.append(result_entry)
        else:
            unmatched.append(result_entry)

    total = len(positions)
    progress(
        f"Fertig: {len(matched)} machbar, {len(partial)} teilweise, "
        f"{len(unmatched)} nicht machbar (von {total} Positionen)"
    )

    return {
        "matched": matched,
        "partial": partial,
        "unmatched": unmatched,
        "summary": {
            "total_positions": total,
            "matched_count": len(matched),
            "partial_count": len(partial),
            "unmatched_count": len(unmatched),
            "match_rate": round(
                (len(matched) + len(partial) * 0.5) / max(total, 1) * 100, 1
            ),
        },
    }


def _empty_result() -> dict:
    """Return empty matching result."""
    return {
        "matched": [],
        "partial": [],
        "unmatched": [],
        "summary": {
            "total_positions": 0,
            "matched_count": 0,
            "partial_count": 0,
            "unmatched_count": 0,
            "match_rate": 0,
        },
    }
