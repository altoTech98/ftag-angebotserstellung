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
from services.feedback_store import find_relevant_feedback

logger = logging.getLogger(__name__)

# ── Matching thresholds ──
MATCH_THRESHOLD = 60   # Score >= 60 = machbar
PARTIAL_THRESHOLD = 35  # Score 35-59 = teilweise machbar

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
    """Normalize dimension to mm. Parses unit from string if present, else uses heuristics."""
    if val is None:
        return None
    val_str = str(val).strip()
    if not val_str:
        return None
    # Check for explicit unit in string
    if "mm" in val_str.lower():
        m = re.search(r'(\d+)', val_str)
        return int(m.group(1)) if m else None
    if "cm" in val_str.lower():
        m = re.search(r'[\d.]+', val_str)
        return int(float(m.group()) * 10) if m else None
    if re.search(r'\d\s*m\b', val_str.lower()) and "mm" not in val_str.lower():
        m = re.search(r'[\d.]+', val_str)
        return int(float(m.group()) * 1000) if m else None
    try:
        n = float(val)
    except (ValueError, TypeError):
        return None
    if n <= 0:
        return None
    # Plausible mm value for doors (400-3500mm)
    if 400 < n < 3500:
        return int(n)
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
    """Detect product category from door fields using keywords and frame type."""
    # ── Step 1: Check explicit frame type fields (zargentyp, umfassungsart) ──
    # These are the most reliable indicators for Rahmentüre vs Zargentüre
    frame_type = str(door.get("zargentyp") or "").lower().strip()
    wall_type = str(door.get("wandtyp") or "").lower().strip()

    if frame_type:
        # "Zarge LBW", "Zarge MW", "Umfassungszarge", "Stahl" → Zargentüre
        if any(kw in frame_type for kw in ("zarge", "lbw", "mw", "stahl", "metall")):
            return "Zargentüre"
        # "Rahmen", "Blockrahmen", "Holzrahmen" → Rahmentüre
        if any(kw in frame_type for kw in ("rahmen", "block", "holz", "futter")):
            if "futter" in frame_type:
                return "Futtertüre"
            return "Rahmentüre"

    # ── Step 2: Check wall type for zarge hints ──
    if wall_type:
        if any(kw in wall_type for kw in ("lbw", "leichtbau", "gips", "trockenbau")):
            return "Zargentüre"
        if any(kw in wall_type for kw in ("mw", "mauerwerk", "beton", "backstein")):
            return "Zargentüre"

    # ── Step 3: Keyword-based detection from text fields ──
    text_parts = []
    for field in ("tuertyp", "beschreibung", "besonderheiten"):
        val = door.get(field)
        if val:
            text_parts.append(str(val).lower())
    text = " ".join(text_parts)

    # Check each category's keywords
    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                return category

    # ── Step 4: Fallback based on fire class ──
    if door.get("brandschutz"):
        bs = str(door["brandschutz"]).lower()
        if "ei" in bs or "t30" in bs or "t60" in bs:
            return "Rahmentüre"

    # Default to Rahmentüre (largest category)
    return "Rahmentüre"


def _product_preference(product: ProductProfile, door_fire: int) -> float:
    """
    Return a preference bonus/penalty for product selection.
    Standard products get 0, premium/niche variants get penalties.
    This ensures "Prestige 51" beats "Prestige Alu 51", etc.
    """
    name = (product.key_fields.get("door_type", "") or "").lower()
    penalty = 0.0

    # Penalize Alu variants (premium, not standard choice)
    if " alu " in f" {name} " or name.endswith(" alu"):
        penalty -= 8.0

    # Penalize Light variants (lighter construction, less common)
    if " light " in f" {name} " or name.endswith(" light"):
        penalty -= 5.0

    # Penalize exotic/niche products
    if "bat" in name or "ftag bat" in name:
        penalty -= 10.0
    if "db-plus" in name or "dB-Plus" in name.lower():
        # dB-Plus is OK for high sound requirements, small penalty
        penalty -= 3.0

    # Prefer standard families slightly (Confort, Prestige, Maxima, Nova, Fries)
    standard_families = ("confort", "prestige", "maxima", "nova", "fries")
    if any(fam in name for fam in standard_families):
        penalty += 2.0

    return penalty


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

    # ── 1. Fire class (35 points) ──
    door_fire = _normalize_fire_class(str(door.get("brandschutz") or ""))
    prod_fire = _normalize_fire_class(kf.get("fire_class", ""))

    if door_fire > 0:
        max_score += 35
        if prod_fire >= door_fire:
            score += 35  # Product fulfills or exceeds requirement
            # Bonus for exact fire class match (prefer EI30 for EI30, not EI60)
            if prod_fire == door_fire:
                score += 5
                max_score += 5
            else:
                max_score += 5  # Over-specified: works but not ideal
                score += 2
        elif prod_fire > 0:
            score += 10  # Has fire protection, just not enough
            gaps.append(f"Brandschutz: braucht {door.get('brandschutz')}, Produkt hat {kf.get('fire_class', 'ohne')}")
        else:
            gaps.append(f"Brandschutz: braucht {door.get('brandschutz')}, Produkt hat keine")
    else:
        # No fire requirement - prefer products WITHOUT fire class (cheaper)
        max_score += 10
        if prod_fire == 0:
            score += 10  # Perfect: no fire requirement, product has none
        else:
            score += 5  # Over-specified: works but costs more

    # ── 2. Sound class (15 points) ──
    door_db = _extract_db(str(door.get("schallschutz") or ""))
    prod_db = _extract_db(kf.get("sound_db", ""))

    if door_db is not None:
        max_score += 15
        if prod_db is not None:
            if prod_db >= door_db:
                score += 15
            elif prod_db >= door_db - 3:
                score += 11  # Close enough (tolerance)
            else:
                score += 4
                gaps.append(f"Schallschutz: braucht {door_db}dB, Produkt hat {prod_db}dB")
        else:
            gaps.append(f"Schallschutz: braucht {door_db}dB, Produkt ohne Angabe")
    else:
        max_score += 5
        score += 5  # No requirement = always fine

    # ── 3. Resistance class (20 points) ──
    door_rc = _normalize_resistance(str(door.get("einbruchschutz") or ""))
    prod_rc = _normalize_resistance(kf.get("resistance", ""))

    if door_rc > 0:
        max_score += 20
        if prod_rc >= door_rc:
            score += 20
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

    # ── 6. Glass cutout bonus (3 points) ──
    door_glass = bool(door.get("verglasung") or door.get("glas_typ"))
    prod_glass = kf.get("glass_cutout", "").lower() == "ja"

    if door_glass:
        max_score += 3
        if prod_glass:
            score += 3
        else:
            gaps.append("Verglasung gewuenscht, Produkt ohne Glasausschnitt")
    else:
        max_score += 2
        score += 2

    # ── 7. Smoke protection (8 points) ──
    door_smoke = str(door.get("rauchschutz") or door.get("besonderheiten") or "").lower()
    prod_smoke = kf.get("smoke_class", "").lower()
    if "s200" in door_smoke or "rauch" in door_smoke:
        max_score += 8
        if prod_smoke and ("s200" in prod_smoke or "rauch" in prod_smoke):
            score += 8
        else:
            gaps.append("Rauchschutz S200 gefordert, Produkt ohne")
    else:
        max_score += 2
        score += 2  # No requirement = fine

    # ── 8. Product preference (tiebreaker) ──
    # Penalize Alu/Light/BAT variants, prefer standard products
    max_score += 7
    score += 7  # Base: all products start equal
    preference = _product_preference(product, door_fire)
    score += preference  # Can go negative (penalty) or positive (bonus)

    # Normalize to 0-100
    final_score = (score / max(max_score, 1)) * 100
    final_score = max(0.0, min(100.0, final_score))  # Clamp
    return round(final_score, 1), gaps


def _build_req_text(door: dict) -> str:
    """Build a compact requirement text for feedback lookup."""
    parts = []
    for key in ("tuertyp", "brandschutz", "einbruchschutz", "schallschutz",
                 "beschreibung", "besonderheiten"):
        val = door.get(key)
        if val:
            parts.append(str(val))
    return " ".join(parts) if parts else "Tuer"


def _enrich_position(pos: dict) -> dict:
    """Fill missing fields from beschreibung text when AI extraction left gaps."""
    desc = str(pos.get("beschreibung") or "").lower()
    if not pos.get("tuertyp"):
        if "stahl" in desc:
            pos["tuertyp"] = "Stahltür"
        elif "holz" in desc:
            pos["tuertyp"] = "Holztür"
        elif "alu" in desc:
            pos["tuertyp"] = "Alutür"
    if not pos.get("brandschutz"):
        m = re.search(r'(ei|t|f)\s*(\d+)', desc)
        if m:
            pos["brandschutz"] = f"EI{m.group(2)}"
    if not pos.get("einbruchschutz"):
        m = re.search(r'(rc|wk)\s*(\d)', desc)
        if m:
            pos["einbruchschutz"] = f"RC{m.group(2)}"
    if not pos.get("rauchschutz"):
        if "s200" in desc or "rauchschutz" in desc:
            pos["rauchschutz"] = "S200"
    return pos


def _verify_critical_fields(
    door: dict, product: ProductProfile, score: float, status: str
) -> tuple[float, str, list[str]]:
    """Verify that critical safety fields are met. Downgrade status if not."""
    violations = []
    door_fire = _normalize_fire_class(str(door.get("brandschutz") or ""))
    prod_fire = _normalize_fire_class(product.key_fields.get("fire_class", ""))
    if door_fire > 0 and prod_fire < door_fire:
        violations.append(
            f"KRITISCH: Brandschutz nicht erfuellt "
            f"(braucht EI{door_fire * 30}, Produkt hat {product.key_fields.get('fire_class', 'ohne')})"
        )
        if status == "matched":
            status = "partial"
            score = min(score, 55)

    door_rc = _normalize_resistance(str(door.get("einbruchschutz") or ""))
    prod_rc = _normalize_resistance(product.key_fields.get("resistance", ""))
    if door_rc > 0 and prod_rc < door_rc:
        violations.append(
            f"KRITISCH: Einbruchschutz nicht erfuellt "
            f"(braucht RC{door_rc}, Produkt hat {product.key_fields.get('resistance', 'ohne')})"
        )
        if status == "matched":
            status = "partial"
            score = min(score, 55)

    return score, status, violations


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
    sig_map = {}  # signature -> (best_product, score, gaps, category, viable_products)
    sig_groups = {}  # signature -> [indices]

    for i, pos in enumerate(positions):
        _enrich_position(pos)
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
            sig_map[sig] = (None, 0, [f"Keine Produkte in Kategorie '{category}'"], category, [])
            continue

        # Score all products, collect all viable ones
        best_product = None
        best_score = -1
        best_gaps = []
        viable_products = []

        for product in cat_products:
            score, gaps = _score_product(door, product)
            if score >= MATCH_THRESHOLD:
                viable_products.append((product, score, gaps))
            if score > best_score:
                best_score = score
                best_product = product
                best_gaps = gaps

        # Check feedback corrections for this door
        try:
            req_text = _build_req_text(door)
            feedback = find_relevant_feedback(req_text, door, limit=3)
            for fb in feedback:
                if fb.get("type") == "correction":
                    correct_idx = (fb.get("correct_product") or {}).get("row_index")
                    if correct_idx is not None:
                        for prod in cat_products:
                            if prod.row_index == correct_idx:
                                best_product = prod
                                best_score = max(best_score, 85)
                                best_gaps = ["Aus Korrektur-Feedback uebernommen"]
                                viable_products.append((prod, best_score, best_gaps))
                                break
        except Exception as e:
            logger.debug(f"Feedback lookup failed: {e}")

        # Cross-category search if best score is below threshold
        if best_score < MATCH_THRESHOLD:
            for alt_cat in catalog.main_category_names:
                if alt_cat == category:
                    continue
                alt_products = catalog.get_main_by_category(alt_cat)
                for product in alt_products:
                    alt_score, alt_gaps = _score_product(door, product)
                    if alt_score > best_score:
                        best_score = alt_score
                        best_product = product
                        best_gaps = alt_gaps
                        category = alt_cat
                    if alt_score >= MATCH_THRESHOLD:
                        viable_products.append((product, alt_score, alt_gaps))

        # Sort viable products by score descending (best first)
        viable_products.sort(key=lambda x: x[1], reverse=True)
        sig_map[sig] = (best_product, best_score, best_gaps, category, viable_products)

    progress("Ergebnisse werden zusammengestellt...")

    # Build results
    for i, pos in enumerate(positions):
        sig = _door_signature(pos)
        best_product, score, gaps, category, viable_products = sig_map[sig]

        # Get product details for ALL viable products (deduplicated by name)
        matched_products = []
        if viable_products:
            seen_names = set()
            for prod, prod_score, prod_gaps in viable_products:
                detail = catalog.get_product_detail(prod.row_index)
                if detail:
                    name = detail.get("Türblatt / Verglasungsart / Rollkasten", "")
                    if not name:
                        name = prod.key_fields.get("door_type", "")
                    if name in seen_names:
                        continue
                    seen_names.add(name)
                    detail["_compact"] = prod.compact_text
                    detail["_row_index"] = prod.row_index
                    matched_products.append(detail)
        elif best_product is not None:
            # Fallback: best product scored below threshold
            detail = catalog.get_product_detail(best_product.row_index)
            if detail:
                detail["_compact"] = best_product.compact_text
                detail["_row_index"] = best_product.row_index
                matched_products = [detail]

        if score >= MATCH_THRESHOLD:
            status = "matched"
        elif score >= PARTIAL_THRESHOLD:
            status = "partial"
        else:
            status = "unmatched"

        # Post-match verification of critical fields
        if best_product and status == "matched":
            score, status, violations = _verify_critical_fields(
                pos, best_product, score, status
            )
            if violations:
                gaps = list(gaps) + violations

        # Build structured missing_info from gap_items
        missing_info = []
        for gap_text in gaps:
            mi = _parse_gap_to_missing_info(gap_text)
            if mi:
                missing_info.append(mi)

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
            "missing_info": missing_info,
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
                len(matched) / max(total, 1) * 100, 1
            ),
        },
    }


def _parse_gap_to_missing_info(gap_text: str) -> dict | None:
    """Parse a gap text string into a structured missing_info dict."""
    # Pattern: "Feld: braucht X, Produkt hat Y"
    m = re.match(r'(?:KRITISCH:\s*)?(\w[\w\s]*?)(?::\s*| nicht erfuellt).*?braucht\s+(.+?),\s*Produkt hat\s+(.+)', gap_text)
    if m:
        return {
            "feld": m.group(1).strip(),
            "benoetigt": m.group(2).strip(),
            "vorhanden": m.group(3).strip(),
        }
    # Pattern: "Feld: braucht X, Produkt ohne Angabe"
    m = re.match(r'(?:KRITISCH:\s*)?(\w[\w\s]*?):\s*braucht\s+(.+?),\s*Produkt (ohne.*)', gap_text)
    if m:
        return {
            "feld": m.group(1).strip(),
            "benoetigt": m.group(2).strip(),
            "vorhanden": m.group(3).strip(),
        }
    # Pattern: "Fluegel: braucht X, Produkt ist Y"
    m = re.match(r'(\w[\w\s]*?):\s*braucht\s+(.+?),\s*Produkt ist\s+(.+)', gap_text)
    if m:
        return {
            "feld": m.group(1).strip(),
            "benoetigt": m.group(2).strip(),
            "vorhanden": m.group(3).strip(),
        }
    # Pattern: "Masse: braucht XxYmm, Produkt max AxBmm"
    m = re.match(r'(\w[\w\s]*?):\s*braucht\s+(.+?),\s*Produkt max\s+(.+)', gap_text)
    if m:
        return {
            "feld": m.group(1).strip(),
            "benoetigt": m.group(2).strip(),
            "vorhanden": f"max {m.group(3).strip()}",
        }
    # Generic: just store the text
    if gap_text:
        return {
            "feld": gap_text.split(":")[0].strip() if ":" in gap_text else "Sonstiges",
            "benoetigt": gap_text,
            "vorhanden": "—",
        }
    return None


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
        str(door.get("zargentyp") or ""),
        str(door.get("besonderheiten") or ""),
        str(door.get("rauchschutz") or ""),
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
