"""
Smart Excel Parser – Structured extraction from Türlisten/Türmatrizen.

Instead of converting 200-column Excel to text, this parser:
1. Auto-detects the header row
2. Maps columns to known door fields via fuzzy matching
3. Extracts structured door dicts directly from cells
4. Normalizes values (dimensions, fire protection codes, etc.)

Handles varying column structures across customers (39–217 columns).
"""

import io
import os
import re
import logging
from difflib import SequenceMatcher
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Known field patterns for fuzzy column header matching
# ---------------------------------------------------------------------------
KNOWN_FIELD_PATTERNS = {
    "tuer_nr": [
        "tür-nr", "tür nr", "türnummer", "tuer-nr", "tuer nr", "tuernr",
        "türnr", "pos", "position", "pos.", "pos-nr", "pos nr", "element-nr",
        "element nr", "elementnr", "door no", "door number",
    ],
    "geschoss": [
        "geschoss", "stockwerk", "etage", "og", "ug", "eg", "floor", "level",
        "ebene", "stock",
    ],
    "breite": [
        "breite", "b [mm]", "b[mm]", "b (mm)", "lichte breite", "tb",
        "türbreite", "breite mm", "breite [mm]", "lichte b",
        "rohbaumass breite", "rbm breite", "width",
        "rm-b rohbaumass breite", "dm-b durchgang breite", "durchgang breite",
    ],
    "hoehe": [
        "höhe", "hoehe", "h [mm]", "h[mm]", "h (mm)", "lichte höhe", "th",
        "türhöhe", "höhe mm", "höhe [mm]", "lichte h", "lichte höhe",
        "rohbaumass höhe", "rbm höhe", "height",
        "rm-h rohbaumass höhe", "dm-h durchgang höhe", "durchgang höhe",
    ],
    "brandschutz": [
        "brandschutz", "feuerschutz", "bs", "feuerwiderstand",
        "brandschutzklasse", "brand", "fire", "ei30", "ei60", "ei90",
        "feuerwiderstandsklasse", "brandschutzanforderung",
        "brand-/rauchschutz", "rauchschutz",
    ],
    "schallschutz": [
        "schallschutz", "ss", "rw", "schalldämmung", "schall",
        "schallschutzklasse", "schalldämmwert", "rw [db]", "rw[db]",
        "schalldämmwert (db)",
    ],
    "einbruchschutz": [
        "einbruchschutz", "rc", "wk", "einbruch", "sicherheit",
        "widerstandsklasse", "einbruchsicherheit", "rc-klasse",
        "einbruch-widerstandsklasse",
    ],
    "tuertyp": [
        "türtyp", "tuertyp", "türart", "elementtyp",
        "tür typ", "door type", "konstruktion", "bauart",
        "türblatt",
    ],
    "beschlaege": [
        "beschläge", "beschlag", "drücker", "druecker", "schloss",
        "schliesser", "schliessung", "beschlaege", "bänder", "band",
        "türdrücker", "türschliesser", "türband",
    ],
    "oberflaechenbehandlung": [
        "oberfläche", "oberflaeche", "farbe", "ral", "beschichtung",
        "anstrich", "finish", "surface", "oberflächenbehandlung",
        "farbgebung", "ral-ton",
    ],
    "verglasung": [
        "verglasung", "verglast", "lichtausschnitt",
        "seitenteil", "glasausschnitt", "glasart",
        "durchsicht (glas",
    ],
    "menge": [
        "menge", "stk", "stück", "quantity", "qty",
    ],
    "besonderheiten": [
        "bemerkung", "besonderheit", "hinweis", "kommentar", "notiz",
        "anmerkung", "zusatz", "bemerkungen", "remarks", "notes",
    ],
    "raum": [
        "raum", "raumbezeichnung", "raumnummer", "raum-nr", "raum nr",
        "zimmer", "room", "raumname", "nutzung", "zugehöriger raum",
    ],
    "wandtyp": [
        "wandtyp", "wand", "wandkonstruktion", "wandaufbau", "mauerwerk",
        "wandstärke", "wanddicke",
    ],
}

# ---------------------------------------------------------------------------
# Normalization helpers
# ---------------------------------------------------------------------------
_BS_PATTERN = re.compile(r"(EI|EI2?|T|REI)\s*(\d+)", re.IGNORECASE)
_RC_PATTERN = re.compile(r"(RC|WK)\s*(\d+)", re.IGNORECASE)
_DIM_PATTERN = re.compile(r"(\d{3,4})")


def _fuzzy_ratio(a: str, b: str) -> float:
    """Simple fuzzy ratio using SequenceMatcher."""
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def _best_field_match(column_name: str) -> tuple[str | None, float]:
    """
    Find the best matching canonical field for a column header.

    Returns: (field_name, score) or (None, 0.0)
    """
    col_lower = column_name.lower().strip()
    if not col_lower or len(col_lower) < 2:
        return None, 0.0

    best_field = None
    best_score = 0.0

    for field, patterns in KNOWN_FIELD_PATTERNS.items():
        field_best = 0.0
        for pattern in patterns:
            # Exact match (highest priority)
            if pattern == col_lower:
                score = 0.98
            # Substring match: only for patterns >= 4 chars to avoid false positives
            # (e.g., "ss" in "glasmass" → false schallschutz match)
            elif len(pattern) >= 4 and pattern in col_lower:
                # Score higher for longer pattern matches (more specific)
                specificity = len(pattern) / len(col_lower)
                score = 0.80 + min(specificity * 0.15, 0.15)
            elif len(pattern) >= 4 and col_lower in pattern:
                score = 0.80
            else:
                # Fuzzy match (only for patterns >= 4 chars)
                if len(pattern) < 4:
                    continue
                ratio = _fuzzy_ratio(col_lower, pattern)
                score = ratio if ratio >= 0.75 else 0.0

            if score > field_best:
                field_best = score

        if field_best > best_score:
            best_score = field_best
            best_field = field

    return best_field, best_score


def _normalize_brandschutz(value) -> str | None:
    """Normalize fire protection: 'EI2 30' → 'EI30', 'T 30' → 'T30'."""
    if pd.isna(value) or not str(value).strip():
        return None
    s = str(value).strip()
    m = _BS_PATTERN.search(s)
    if m:
        prefix = m.group(1).upper()
        if prefix == "EI2":
            prefix = "EI"
        return f"{prefix}{m.group(2)}"
    # Check for common shorthand
    s_lower = s.lower()
    if s_lower in ("keine", "nein", "ohne", "-", "0", "n/a"):
        return None
    return s if len(s) > 1 else None


def _normalize_einbruchschutz(value) -> str | None:
    """Normalize burglar resistance: 'WK 2' → 'RC2', 'RC3' stays."""
    if pd.isna(value) or not str(value).strip():
        return None
    s = str(value).strip()
    m = _RC_PATTERN.search(s)
    if m:
        level = m.group(2)
        return f"RC{level}"
    s_lower = s.lower()
    if s_lower in ("keine", "nein", "ohne", "-", "0", "n/a"):
        return None
    return s if len(s) > 1 else None


def _extract_dimension_mm(value) -> int | None:
    """Extract numeric mm value: '900mm' → 900, '0.9m' → 900, '1.066' → 1066, '900' → 900."""
    if pd.isna(value):
        return None
    s = str(value).strip()
    if not s:
        return None

    # Try direct numeric conversion
    try:
        v_float = float(s)
        if 0.1 <= v_float < 15:
            # Likely meters (e.g. 1.066m → 1066mm, 0.9m → 900mm)
            return int(round(v_float * 1000))
        v = int(v_float)
        if 100 <= v <= 9999:
            return v
        return v if v > 0 else None
    except (ValueError, OverflowError):
        pass

    # Extract first number sequence
    m = _DIM_PATTERN.search(s)
    if m:
        v = int(m.group(1))
        if 100 <= v <= 9999:
            return v
    return None


def _clean_string_value(value) -> str | None:
    """Clean a string cell value, return None if empty."""
    if pd.isna(value):
        return None
    s = str(value).strip()
    if not s or s.lower() in ("-", "0", "n/a", "nan", "none"):
        return None
    return s


# ---------------------------------------------------------------------------
# Main functions
# ---------------------------------------------------------------------------

def parse_tuerliste_bytes(content: bytes) -> dict:
    """Parse an Excel Türliste from raw bytes. See parse_tuerliste for return format."""
    return _parse_tuerliste_from_excel(pd.ExcelFile(io.BytesIO(content)))


def parse_tuerliste(file_path: str) -> dict:
    """
    Parse an Excel Türliste into structured door positions.

    Returns:
        {
            "doors": [
                {
                    "tuer_nr": "T01.001",
                    "geschoss": "EG",
                    "breite": 900,
                    "hoehe": 2100,
                    "brandschutz": "EI30",
                    ...
                    "_raw_row": {<all original columns>},
                },
                ...
            ],
            "column_mapping": {"tuer_nr": "Tür-Nr.", "breite": "B [mm]", ...},
            "unmapped_columns": ["Foo", "Bar"],
            "total_rows": 659,
            "sheet_name": "Türliste",
            "header_row_index": int,
        }
    """
    return _parse_tuerliste_from_excel(pd.ExcelFile(file_path))


def _parse_tuerliste_from_excel(xl: pd.ExcelFile) -> dict:
    """Internal: parse Türliste from an already-opened ExcelFile."""

    # Find the right sheet
    sheet_name = _find_tuerliste_sheet(xl)
    if not sheet_name:
        sheet_name = xl.sheet_names[0]
        logger.warning(f"No door list sheet found, using first sheet: {sheet_name}")

    # Read raw data (no header)
    df_raw = pd.read_excel(xl, sheet_name=sheet_name, header=None, dtype=str)
    df_raw = df_raw.fillna("")

    # Find header row
    header_idx = _find_header_row(df_raw)
    if header_idx is None:
        header_idx = 0
        logger.warning("Could not auto-detect header row, using row 0")

    # Re-read with correct header
    df = pd.read_excel(xl, sheet_name=sheet_name, header=header_idx, dtype=str)
    df.columns = [str(c).strip() for c in df.columns]
    df = df.fillna("")

    # Drop completely empty rows
    df = df[df.apply(lambda row: any(str(v).strip() for v in row), axis=1)]

    # Map columns
    column_mapping = _map_columns(df)
    all_mapped_cols = set(column_mapping.values())
    unmapped = [c for c in df.columns if c not in all_mapped_cols and c.strip()]

    # Extract door positions
    doors = _extract_door_positions(df, column_mapping)

    return {
        "doors": doors,
        "column_mapping": column_mapping,
        "unmapped_columns": unmapped[:50],  # Limit for API response
        "total_rows": len(doors),
        "sheet_name": sheet_name,
        "header_row_index": header_idx,
    }


def _find_tuerliste_sheet(xl: pd.ExcelFile) -> str | None:
    """
    Find the sheet most likely to contain door data.
    Strategy: name pattern match → column analysis.
    """
    sheet_names = xl.sheet_names

    # Check sheet names for door list patterns
    door_name_patterns = re.compile(
        r"(t[üu]rliste|t[üu]rmatrix|t[üu]r[_\-\s]?liste|"
        r"t[üu]r[_\-\s]?matrix|door|t[üu]ren)",
        re.IGNORECASE,
    )
    for name in sheet_names:
        if door_name_patterns.search(name):
            return name

    # Fallback: check which sheet has the most door-related columns
    best_sheet = None
    best_count = 0

    for name in sheet_names:
        try:
            df = pd.read_excel(xl, sheet_name=name, header=None, nrows=15, dtype=str)
            for i in range(min(10, len(df))):
                row_values = df.iloc[i].dropna().astype(str).str.lower().tolist()
                row_text = " ".join(row_values)
                count = sum(
                    1 for kw in [
                        "tür-nr", "türnummer", "pos", "brandschutz",
                        "schallschutz", "breite", "höhe", "türtyp", "geschoss",
                    ]
                    if kw in row_text
                )
                if count > best_count:
                    best_count = count
                    best_sheet = name
        except Exception:
            continue

    if best_count >= 3:
        return best_sheet
    return None


def _find_header_row(df: pd.DataFrame) -> int | None:
    """
    Auto-detect the header row by scoring candidate rows.

    Prefers rows with more door-specific keywords over rows that merely
    have many string values. This correctly handles multi-row headers where
    group headers (Row 4) have enough strings but actual column headers (Row 6)
    have more domain-specific keywords.
    """
    _DOOR_KEYWORDS = [
        "tür", "pos", "brand", "schall", "breit", "höh", "geschoss",
        "einbruch", "wand", "raum", "zarge", "schloss", "beschlag",
        "verglasung", "glas", "durchsicht", "öffnung", "flügel",
        "rohbau", "durchgang", "zylinder", "türblatt",
    ]

    candidates = []  # (row_index, door_kw_count, non_empty_count)

    for i in range(min(20, len(df))):
        row = df.iloc[i]
        non_empty = row[row.astype(str).str.strip() != ""]
        if len(non_empty) < 5:
            continue

        string_count = sum(
            1 for v in non_empty
            if isinstance(v, str) and len(str(v).strip()) > 1
        )
        if string_count < 5:
            continue

        row_text = " ".join(str(v).lower() for v in non_empty)
        door_kw_count = sum(1 for kw in _DOOR_KEYWORDS if kw in row_text)

        if door_kw_count >= 2 or string_count >= 8:
            candidates.append((i, door_kw_count, len(non_empty)))

    if not candidates:
        return None

    # Prefer row with most door keywords, then most non-empty cells
    candidates.sort(key=lambda x: (x[1], x[2]), reverse=True)
    best = candidates[0]
    logger.info(
        f"Header row detected: row {best[0]} "
        f"(door_keywords={best[1]}, non_empty={best[2]}, "
        f"candidates checked: {[c[0] for c in candidates]})"
    )
    return best[0]


def _map_columns(df: pd.DataFrame) -> dict[str, str]:
    """
    Map DataFrame column names to canonical fields using fuzzy matching.

    Returns: {canonical_field: actual_column_name}
    """
    mapping = {}
    used_columns = set()

    # Two passes: exact matches first, then fuzzy
    for pass_num in range(2):
        threshold = 0.85 if pass_num == 0 else 0.75

        for col in df.columns:
            if col in used_columns:
                continue
            field, score = _best_field_match(col)
            if field and field not in mapping and score >= threshold:
                mapping[field] = col
                used_columns.add(col)

    return mapping


def _extract_door_positions(df: pd.DataFrame, column_mapping: dict) -> list[dict]:
    """
    Extract structured door dicts from DataFrame using column mapping.
    """
    doors = []
    tuer_nr_col = column_mapping.get("tuer_nr")

    for _, row in df.iterrows():
        # Skip rows without a door number (likely summary/empty rows)
        if tuer_nr_col:
            tuer_nr_val = _clean_string_value(row.get(tuer_nr_col))
            if not tuer_nr_val:
                continue
        else:
            tuer_nr_val = None

        # Skip header-repeat rows
        if tuer_nr_val and tuer_nr_val.lower() in (
            "tür-nr", "türnummer", "pos", "position", "nr", "element-nr",
        ):
            continue

        door = {
            "tuer_nr": tuer_nr_val,
            "geschoss": _clean_string_value(row.get(column_mapping.get("geschoss", ""), "")),
            "breite": _extract_dimension_mm(row.get(column_mapping.get("breite", ""), "")),
            "hoehe": _extract_dimension_mm(row.get(column_mapping.get("hoehe", ""), "")),
            "brandschutz": _normalize_brandschutz(row.get(column_mapping.get("brandschutz", ""), "")),
            "schallschutz": _clean_string_value(row.get(column_mapping.get("schallschutz", ""), "")),
            "einbruchschutz": _normalize_einbruchschutz(row.get(column_mapping.get("einbruchschutz", ""), "")),
            "tuertyp": _clean_string_value(row.get(column_mapping.get("tuertyp", ""), "")),
            "beschlaege": _clean_string_value(row.get(column_mapping.get("beschlaege", ""), "")),
            "oberflaechenbehandlung": _clean_string_value(row.get(column_mapping.get("oberflaechenbehandlung", ""), "")),
            "verglasung": _clean_string_value(row.get(column_mapping.get("verglasung", ""), "")),
            "menge": _parse_menge(row.get(column_mapping.get("menge", ""), "")),
            "besonderheiten": _clean_string_value(row.get(column_mapping.get("besonderheiten", ""), "")),
            "raum": _clean_string_value(row.get(column_mapping.get("raum", ""), "")),
            "wandtyp": _clean_string_value(row.get(column_mapping.get("wandtyp", ""), "")),
        }

        # Store raw row for reference
        door["_raw_row"] = {
            str(k): str(v) for k, v in row.items()
            if str(v).strip()
        }

        doors.append(door)

    return doors


def _parse_menge(value) -> int:
    """Parse quantity, default to 1."""
    if pd.isna(value) or not str(value).strip():
        return 1
    try:
        v = int(float(str(value).strip()))
        return v if v > 0 else 1
    except (ValueError, OverflowError):
        return 1


def merge_tuerlisten(parsed_lists: list[dict]) -> dict:
    """
    Merge multiple parsed Türliste results by tuer_nr.

    First list is the base, subsequent lists enrich with additional fields.
    Conflicts are tracked in _merge_conflicts.
    """
    if not parsed_lists:
        return {"doors": [], "column_mapping": {}, "unmapped_columns": [],
                "total_rows": 0, "sheet_name": "", "header_row_index": 0}

    if len(parsed_lists) == 1:
        return parsed_lists[0]

    base = parsed_lists[0]
    doors_by_nr = {}
    for door in base["doors"]:
        key = door.get("tuer_nr")
        if key:
            doors_by_nr[key] = door.copy()

    merged_mapping = dict(base["column_mapping"])
    merged_unmapped = list(base["unmapped_columns"])

    # Merge subsequent lists
    for extra in parsed_lists[1:]:
        merged_mapping.update({
            k: v for k, v in extra["column_mapping"].items()
            if k not in merged_mapping
        })
        merged_unmapped.extend(extra.get("unmapped_columns", []))

        for door in extra["doors"]:
            key = door.get("tuer_nr")
            if not key:
                continue

            if key in doors_by_nr:
                # Enrich: fill None fields from extra
                existing = doors_by_nr[key]
                conflicts = existing.get("_merge_conflicts", [])
                for field in [
                    "geschoss", "breite", "hoehe", "brandschutz", "schallschutz",
                    "einbruchschutz", "tuertyp", "beschlaege",
                    "oberflaechenbehandlung", "verglasung", "besonderheiten",
                    "raum", "wandtyp",
                ]:
                    existing_val = existing.get(field)
                    new_val = door.get(field)
                    if not existing_val and new_val:
                        existing[field] = new_val
                    elif existing_val and new_val and str(existing_val) != str(new_val):
                        conflicts.append(f"{field}: '{existing_val}' vs '{new_val}'")
                if conflicts:
                    existing["_merge_conflicts"] = conflicts
            else:
                # New door from extra list
                doors_by_nr[key] = door.copy()

    all_doors = list(doors_by_nr.values())

    return {
        "doors": all_doors,
        "column_mapping": merged_mapping,
        "unmapped_columns": list(set(merged_unmapped))[:50],
        "total_rows": len(all_doors),
        "sheet_name": base["sheet_name"],
        "header_row_index": base["header_row_index"],
    }
