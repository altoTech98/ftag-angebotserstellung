"""
Product Matcher – Loads the FTAG product list and matches extracted requirements.
"""

import os
import re
import pandas as pd
from functools import lru_cache
from typing import Optional

# Path to the product Excel file
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
PRODUCT_FILE = os.path.join(DATA_DIR, "produktuebersicht.xlsx")


@lru_cache(maxsize=1)
def load_product_catalog() -> pd.DataFrame:
    """
    Load and cache the FTAG product catalog from Excel.
    Returns a cleaned DataFrame.
    """
    if not os.path.exists(PRODUCT_FILE):
        raise FileNotFoundError(
            f"Product catalog not found at: {PRODUCT_FILE}\n"
            "Please place 'produktuebersicht.xlsx' in the data/ directory."
        )

    # Read Excel - try to find the right sheet
    xl = pd.ExcelFile(PRODUCT_FILE)
    sheet_names = xl.sheet_names

    # Try to read first sheet or find relevant sheet
    df = pd.read_excel(PRODUCT_FILE, sheet_name=0, header=None)

    # Find the header row (look for rows with substantial content)
    header_row = _find_header_row(df)

    if header_row is not None:
        df = pd.read_excel(PRODUCT_FILE, sheet_name=0, header=header_row)
    else:
        df = pd.read_excel(PRODUCT_FILE, sheet_name=0)

    # Clean column names
    df.columns = [str(col).strip() for col in df.columns]

    # Drop completely empty rows/columns
    df = df.dropna(how="all").reset_index(drop=True)

    return df


def _find_header_row(df: pd.DataFrame) -> Optional[int]:
    """Find the row index that looks like a header."""
    for i, row in df.iterrows():
        non_null = row.dropna()
        if len(non_null) > 5:
            # Check if values look like headers (strings, not numbers)
            string_count = sum(1 for v in non_null if isinstance(v, str) and len(v) > 1)
            if string_count > 5:
                return i
    return None


def get_products_summary() -> list[dict]:
    """
    Return a summary list of all products for the frontend.
    Returns first 200 rows to avoid overwhelming the API.
    """
    df = load_product_catalog()

    products = []
    for _, row in df.head(200).iterrows():
        product = {}
        for col in df.columns[:20]:  # First 20 columns
            val = row.get(col)
            if pd.notna(val) and str(val).strip():
                product[str(col)] = str(val).strip()
        if product:
            products.append(product)

    return products


def match_requirements(requirements: dict) -> dict:
    """
    Match extracted requirements against the product catalog.

    Returns:
        {
            "matched": [...],      # Positions with matching products
            "unmatched": [...],    # Positions without matching products
            "partial": [...],      # Positions with partial matches
            "summary": {...}
        }
    """
    df = load_product_catalog()
    positions = requirements.get("positionen", [])

    matched = []
    unmatched = []
    partial = []

    for pos in positions:
        match_result = _match_single_position(pos, df)
        match_result["original_position"] = pos

        if match_result["status"] == "matched":
            matched.append(match_result)
        elif match_result["status"] == "partial":
            partial.append(match_result)
        else:
            unmatched.append(match_result)

    return {
        "matched": matched,
        "partial": partial,
        "unmatched": unmatched,
        "summary": {
            "total_positions": len(positions),
            "matched_count": len(matched),
            "partial_count": len(partial),
            "unmatched_count": len(unmatched),
            "match_rate": round(
                (len(matched) + len(partial) * 0.5) / max(len(positions), 1) * 100, 1
            ),
        },
    }


def _match_single_position(position: dict, df: pd.DataFrame) -> dict:
    """
    Match a single position requirement against the product catalog.
    Uses fuzzy matching based on door type, fire protection class, etc.
    """
    tuertyp = (position.get("tuertyp") or "").lower()
    brandschutz = (position.get("brandschutz") or "").upper()
    einbruchschutz = (position.get("einbruchschutz") or "").upper()
    schallschutz = position.get("schallschutz")
    breite = position.get("breite")
    hoehe = position.get("hoehe")

    # Convert dataframe to string for searching
    df_str = df.astype(str)

    matching_rows = []
    score = 0
    max_score = 0

    # Score based on door type
    if tuertyp:
        max_score += 3
        type_keywords = _get_type_keywords(tuertyp)
        for col in df_str.columns:
            col_matches = df_str[col].str.contains(
                "|".join(type_keywords), case=False, na=False
            )
            if col_matches.any():
                score += 3
                matching_rows.extend(df[col_matches].index.tolist())
                break

    # Score based on fire protection
    if brandschutz and brandschutz != "NONE":
        max_score += 3
        # Look for fire class in any column
        fire_match = df_str.apply(
            lambda col: col.str.contains(brandschutz, case=False, na=False)
        ).any(axis=1)
        if fire_match.any():
            score += 3
            matching_rows.extend(df[fire_match].index.tolist())

    # Score based on burglar resistance
    if einbruchschutz and einbruchschutz != "NONE":
        max_score += 2
        # RC and WK are equivalent
        rc_class = einbruchschutz.replace("WK", "RC")
        wk_class = einbruchschutz.replace("RC", "WK")
        burglary_pattern = f"{rc_class}|{wk_class}"
        burglary_match = df_str.apply(
            lambda col: col.str.contains(burglary_pattern, case=False, na=False)
        ).any(axis=1)
        if burglary_match.any():
            score += 2
            matching_rows.extend(df[burglary_match].index.tolist())

    # Determine match status
    unique_matches = list(set(matching_rows))

    if max_score == 0:
        # No specific requirements – assume basic product exists
        status = "matched"
        confidence = 0.7
        products = _get_generic_product(tuertyp)
    elif score >= max_score * 0.7:
        status = "matched"
        confidence = score / max(max_score, 1)
        products = _extract_matching_products(df, unique_matches[:3])
    elif score > 0:
        status = "partial"
        confidence = score / max(max_score, 1)
        products = _extract_matching_products(df, unique_matches[:3])
    else:
        status = "unmatched"
        confidence = 0.0
        products = []

    return {
        "status": status,
        "confidence": round(confidence, 2),
        "position": position.get("position", "?"),
        "beschreibung": position.get("beschreibung", ""),
        "menge": position.get("menge", 1),
        "einheit": position.get("einheit", "Stk"),
        "matched_products": products,
        "reason": _get_match_reason(status, tuertyp, brandschutz, einbruchschutz),
    }


def _get_type_keywords(tuertyp: str) -> list[str]:
    """Map door type string to search keywords."""
    keywords = []
    if "stahl" in tuertyp:
        keywords.extend(["Stahl", "ST"])
    if "holz" in tuertyp:
        keywords.extend(["Holz", "HO"])
    if "alu" in tuertyp or "aluminium" in tuertyp:
        keywords.extend(["Alu", "Aluminium"])
    if "brand" in tuertyp or "feuer" in tuertyp:
        keywords.extend(["T30", "T60", "T90", "EI30", "EI60", "EI90", "Brand"])
    if "sicherheit" in tuertyp:
        keywords.extend(["RC", "WK", "Sicherheit"])
    if not keywords:
        keywords = [tuertyp[:4]] if len(tuertyp) >= 4 else [tuertyp]
    return keywords


def _extract_matching_products(df: pd.DataFrame, row_indices: list) -> list[dict]:
    """Extract product info from matching rows."""
    products = []
    seen = set()

    for idx in row_indices:
        if idx >= len(df):
            continue
        row = df.iloc[idx]
        # Get first few columns as product identifier
        product_key = str(row.iloc[0]) if len(row) > 0 else str(idx)
        if product_key in seen or product_key in ("nan", "NaN", ""):
            continue
        seen.add(product_key)

        product = {}
        for col in df.columns[:10]:
            val = row.get(col)
            if pd.notna(val) and str(val).strip() not in ("nan", "NaN", ""):
                product[str(col)] = str(val).strip()

        if product:
            products.append(product)

    return products[:3]  # Max 3 matching products


def _get_generic_product(tuertyp: str) -> list[dict]:
    """Return a generic product placeholder when specific match not found."""
    return [
        {
            "bezeichnung": f"Standard {tuertyp.title() if tuertyp else 'Tür'}",
            "hinweis": "Standardprodukt aus FTAG-Sortiment – genaue Spezifikation bei Auftragserteilung",
        }
    ]


def _get_match_reason(status: str, tuertyp: str, brandschutz: str, einbruchschutz: str) -> str:
    """Generate human-readable match reason."""
    if status == "matched":
        return "Produkt im FTAG-Sortiment verfügbar"
    elif status == "partial":
        return "Teilweise erfüllbar – Rückfrage zu spezifischen Anforderungen empfohlen"
    else:
        specs = []
        if brandschutz:
            specs.append(f"Brandschutzklasse {brandschutz}")
        if einbruchschutz:
            specs.append(f"Einbruchschutz {einbruchschutz}")
        if tuertyp:
            specs.append(f"Türtyp {tuertyp}")
        spec_str = ", ".join(specs) if specs else "Spezifikation"
        return f"Kein exaktes Produkt für {spec_str} gefunden – Sonderanfertigung prüfen"
