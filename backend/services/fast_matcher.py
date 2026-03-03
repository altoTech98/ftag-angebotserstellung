"""
Fast rule-based door matcher – no AI, no accessories.

Matches customer door positions against FTAG catalog using:
1. Category detection (keywords)
2. Fire class compatibility (EI30=T30, higher fulfills lower)
3. Sound class (dB comparison)
4. Resistance class (RC2=WK2)
5. Dimension check (breite x hoehe within product max)
6. Leaf count (1-flg / 2-flg)

Returns machbar/nicht_machbar per position with best matching product.
"""

import re
import logging
from typing import Optional, Callable

from services.catalog_index import get_catalog_index, ProductProfile

logger = logging.getLogger(__name__)

# ── Fire class hierarchy (higher fulfills lower) ──
FIRE_CLASS_RANK = {
    "ohne": 0, "keine": 0, "": 0, "--": 0, "nicht definiert": 0,
    "ei30": 1, "t30": 1, "f30": 1,
    "ei60": 2, "t60": 2, "f60": 2,
    "ei90": 3, "t90": 3, "f90": 3,
    "ei120": 4, "t120": 4, "f120": 4,
}

# ── Resistance class hierarchy ──
RESISTANCE_RANK = {
    "": 0, "ohne": 0, "keine": 0, "--": 0, "nicht definiert": 0,
    "rc1": 1, "wk1": 1,
    "rc2": 2, "wk2": 2,
    "rc3": 3, "wk3": 3,
    "rc4": 4, "wk4": 4,
}

# ── Category detection keywords ──
CATEGORY_KEYWORDS = {
    "Rahmentüre": [
        "rahmen", "fluegel", "flügel", "innentür", "innentuer",
        "unternehmerkollektion", "standardtür", "standardtuer",
    ],
    "Zargentüre": ["zargen"],
    "Futtertüre": ["futter"],
    "Schiebetüre": ["schiebe", "sliding"],
    "Brandschutztor": ["tor", "sektional", "schnelllauf", "rolltor"],
    "Brandschutzvorhang": ["vorhang", "rollkasten"],
    "Festverglasung": ["festverglas", "festvergl"],
    "Ganzglas Tür": ["ganzglas", "glas tür", "glastür", "glastuere"],
    "Pendeltüre": ["pendel"],
    "Vollwand": ["vollwand", "trennwand"],
    "Steigzonen/Elektrofronten": ["steigzone", "elektrofront", "revision"],
}


def _normalize_fire_class(val: str) -> int:
    """Normalize fire class string to rank number."""
    if not val:
        return 0
    val = val.lower().strip().replace(" ", "").replace("-", "")
    # Extract EI/T/F + number pattern
    m = re.search(r'(ei|t|f)(\d+)', val)
    if m:
        key = m.group(1) + m.group(2)
        return FIRE_CLASS_RANK.get(key, 0)
    return FIRE_CLASS_RANK.get(val, 0)


def _normalize_resistance(val: str) -> int:
    """Normalize resistance class to rank number."""
    if not val:
        return 0
    val = val.lower().strip().replace(" ", "").replace("-", "")
    m = re.search(r'(rc|wk)(\d+)', val)
    if m:
        key = m.group(1) + m.group(2)
        return RESISTANCE_RANK.get(key, 0)
    return RESISTANCE_RANK.get(val, 0)


def _extract_db(val: str) -> Optional[int]:
    """Extract dB value from string like '32 dB', 'Rw=35dB', '29'."""
    if not val:
        return None
    val = str(val)
    m = re.search(r'(\d+)\s*d[bB]', val)
    if m:
        return int(m.group(1))
    m = re.search(r'[Rr]w\s*=?\s*(\d+)', val)
    if m:
        return int(m.group(1))
    try:
        n = int(val)
        if 15 <= n <= 60:
            return n
    except (ValueError, TypeError):
        pass
    return None


def _parse_max_dimensions(light_opening: str) -> tuple[Optional[int], Optional[int]]:
    """Parse max dimensions from light_opening like '1150 x 2415'."""
    if not light_opening:
        return None, None
    m = re.search(r'(\d+)\s*[xX×]\s*(\d+)', light_opening)
    if m:
        return int(m.group(1)), int(m.group(2))
    return None, None


def _normalize_dimension(val, unit_hint: str = "") -> Optional[int]:
    """Normalize dimension to mm. Values < 20 assumed m, 20-400 assumed cm, >400 assumed mm."""
    if val is None:
        return None
    try:
        n = float(val)
    except (ValueError, TypeError):
        return None
    if n <= 0:
        return None
    if n < 20:
        return int(n * 1000)  # meters -> mm
    if n <= 400:
        return int(n * 10)    # cm -> mm (most common: 95cm = 950mm)
    return int(n)              # already mm


def _detect_leaves(door: dict) -> Optional[str]:
    """Detect leaf count from door data."""
    fl = door.get("fluegel_anzahl") or ""
    if fl:
        fl = str(fl).lower()
        if "2" in fl:
            return "2-flg"
        if "1" in fl:
            return "1-flg"

    # Check description/type
    for field in ("tuertyp", "beschreibung", "besonderheiten"):
        val = str(door.get(field) or "").lower()
        if "2-fl" in val or "2 fl" in val or "zweifl" in val or "doppel" in val:
            return "2-flg"
    return "1-flg"  # default


def _detect_category(door: dict) -> str:
    """Detect product category from door fields using keywords."""
    # Combine all text fields for matching
    text_parts = []
    for field in ("tuertyp", "beschreibung", "besonderheiten", "zargentyp"):
        val = door.get(field)
        if val:
            text_parts.append(str(val).lower())
    text = " ".join(text_parts)

    # Check each category's keywords
    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                return category

    # Fallback: if has fire class -> Rahmentüre (most common)
    if door.get("brandschutz"):
        bs = str(door["brandschutz"]).lower()
        if "ei" in bs or "t30" in bs or "t60" in bs:
            return "Rahmentüre"

    # Default to Rahmentüre (largest category)
    return "Rahmentüre"


def _score_product(door: dict, product: ProductProfile) -> tuple[float, list[str]]:
    """
    Score how well a product matches a door requirement.
    Returns (score 0-100, list of gap reasons).
    Higher score = better match.
    """
    score = 0.0
    max_score = 0.0
    gaps = []
    kf = product.key_fields

    # ── 1. Fire class (30 points) ──
    door_fire = _normalize_fire_class(str(door.get("brandschutz") or ""))
    prod_fire = _normalize_fire_class(kf.get("fire_class", ""))

    if door_fire > 0:
        max_score += 30
        if prod_fire >= door_fire:
            score += 30  # Product fulfills or exceeds requirement
        elif prod_fire > 0:
            score += 10  # Has fire protection, just not enough
            gaps.append(f"Brandschutz: braucht {door.get('brandschutz')}, Produkt hat {kf.get('fire_class', 'ohne')}")
        else:
            gaps.append(f"Brandschutz: braucht {door.get('brandschutz')}, Produkt hat keine")
    else:
        # No fire requirement - any product is fine, but prefer "ohne"
        max_score += 10
        if prod_fire == 0:
            score += 10
        else:
            score += 8  # Higher fire class still works

    # ── 2. Sound class (20 points) ──
    door_db = _extract_db(str(door.get("schallschutz") or ""))
    prod_db = _extract_db(kf.get("sound_db", ""))

    if door_db is not None:
        max_score += 20
        if prod_db is not None:
            if prod_db >= door_db:
                score += 20
            elif prod_db >= door_db - 3:
                score += 15  # Close enough (tolerance)
            else:
                score += 5
                gaps.append(f"Schallschutz: braucht {door_db}dB, Produkt hat {prod_db}dB")
        else:
            gaps.append(f"Schallschutz: braucht {door_db}dB, Produkt ohne Angabe")
    else:
        max_score += 5
        score += 5  # No requirement = always fine

    # ── 3. Resistance class (15 points) ──
    door_rc = _normalize_resistance(str(door.get("einbruchschutz") or ""))
    prod_rc = _normalize_resistance(kf.get("resistance", ""))

    if door_rc > 0:
        max_score += 15
        if prod_rc >= door_rc:
            score += 15
        else:
            gaps.append(f"Einbruchschutz: braucht RC{door_rc}, Produkt hat {kf.get('resistance', 'ohne')}")
    else:
        max_score += 5
        score += 5

    # ── 4. Dimensions (20 points) ──
    door_b = _normalize_dimension(door.get("breite"))
    door_h = _normalize_dimension(door.get("hoehe"))
    prod_max_b, prod_max_h = _parse_max_dimensions(kf.get("light_opening", ""))

    if door_b and door_h:
        max_score += 20
        if prod_max_b and prod_max_h:
            if door_b <= prod_max_b and door_h <= prod_max_h:
                score += 20
            elif door_b <= prod_max_b * 1.05 and door_h <= prod_max_h * 1.05:
                score += 15  # Within 5% tolerance
            else:
                score += 5
                gaps.append(
                    f"Masse: braucht {door_b}x{door_h}mm, Produkt max {prod_max_b}x{prod_max_h}mm"
                )
        else:
            score += 12  # No max dimensions = assume it fits
    else:
        max_score += 5
        score += 5

    # ── 5. Leaf count (10 points) ──
    door_leaves = _detect_leaves(door)
    prod_leaves = kf.get("leaves", "")

    if prod_leaves:
        max_score += 10
        if door_leaves == prod_leaves:
            score += 10
        else:
            score += 2
            gaps.append(f"Fluegel: braucht {door_leaves}, Produkt ist {prod_leaves}")
    else:
        max_score += 5
        score += 5

    # ── 6. Glass cutout bonus (5 points) ──
    door_glass = bool(door.get("verglasung") or door.get("glas_typ"))
    prod_glass = kf.get("glass_cutout", "").lower() == "ja"

    if door_glass:
        max_score += 5
        if prod_glass:
            score += 5
        else:
            gaps.append("Verglasung gewuenscht, Produkt ohne Glasausschnitt")
    else:
        max_score += 2
        score += 2

    # Normalize to 0-100
    final_score = (score / max(max_score, 1)) * 100
    return round(final_score, 1), gaps


def match_all(
    positions: list[dict],
    on_progress: Optional[Callable[[str], None]] = None,
) -> dict:
    """
    Fast rule-based matching. No AI calls, no accessories.

    Returns standard matching result dict with matched/partial/unmatched + summary.
    """
    catalog = get_catalog_index()

    if not positions:
        return _empty_result()

    def progress(msg: str):
        logger.info(msg)
        if on_progress:
            on_progress(msg)

    progress(f"Schnell-Matching: {len(positions)} Positionen...")

    matched = []
    partial = []
    unmatched = []

    # Deduplicate
    sig_map = {}  # signature -> (best_product, score, gaps, category)
    sig_groups = {}  # signature -> [indices]

    for i, pos in enumerate(positions):
        sig = _door_signature(pos)
        sig_groups.setdefault(sig, []).append(i)

    unique_count = len(sig_groups)
    progress(f"Dedupliziert: {len(positions)} Positionen -> {unique_count} einzigartige Typen")

    for sig_idx, (sig, indices) in enumerate(sig_groups.items()):
        door = positions[indices[0]]
        category = _detect_category(door)

        # Get products for this category
        cat_products = catalog.get_main_by_category(category)
        if not cat_products:
            # Try broader categories
            for fallback_cat in ("Rahmentüre", "Zargentüre", "Futtertüre"):
                cat_products = catalog.get_main_by_category(fallback_cat)
                if cat_products:
                    category = fallback_cat
                    break

        if not cat_products:
            sig_map[sig] = (None, 0, [f"Keine Produkte in Kategorie '{category}'"], category)
            continue

        # Score all products, pick best
        best_product = None
        best_score = -1
        best_gaps = []

        for product in cat_products:
            score, gaps = _score_product(door, product)
            if score > best_score:
                best_score = score
                best_product = product
                best_gaps = gaps

        sig_map[sig] = (best_product, best_score, best_gaps, category)

    progress("Ergebnisse werden zusammengestellt...")

    # Build results
    MATCH_THRESHOLD = 60  # Score >= 60 = machbar
    PARTIAL_THRESHOLD = 35  # Score 35-59 = teilweise machbar

    for i, pos in enumerate(positions):
        sig = _door_signature(pos)
        best_product, score, gaps, category = sig_map[sig]

        # Get product detail
        matched_products = []
        if best_product is not None:
            detail = catalog.get_product_detail(best_product.row_index)
            if detail:
                detail["_compact"] = best_product.compact_text
                matched_products = [detail]

        if score >= MATCH_THRESHOLD:
            status = "matched"
        elif score >= PARTIAL_THRESHOLD:
            status = "partial"
        else:
            status = "unmatched"

        result_entry = {
            "status": status,
            "confidence": round(score / 100, 2),
            "position": pos.get("position", pos.get("tuer_nr", f"Pos {i+1}")),
            "beschreibung": pos.get("beschreibung", pos.get("tuertyp", "")),
            "menge": pos.get("menge", 1),
            "einheit": pos.get("einheit", "Stk"),
            "matched_products": matched_products,
            "zubehoer_matched": [],
            "zubehoer_gap": [],
            "gap_items": gaps,
            "reason": best_product.compact_text if best_product else "Kein passendes Produkt gefunden",
            "original_position": pos,
            "category": category,
        }

        if status == "matched":
            matched.append(result_entry)
        elif status == "partial":
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
        str(door.get("fluegel_anzahl") or ""),
    ]
    return "|".join(parts).lower()


def _empty_result() -> dict:
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
