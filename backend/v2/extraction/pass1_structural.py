"""
Pass 1: Structural extraction using regex/heuristics (no AI).

Extracts door positions from ParseResult text using known field patterns.
Works on XLSX text (pipe-delimited canonical fields) and PDF/DOCX markdown tables.
Every extracted field gets FieldSource provenance tracking.
"""

import logging
import re
from typing import Optional

from v2.parsers.base import ParseResult
from v2.parsers.xlsx_parser import KNOWN_FIELD_PATTERNS, _MIN_DOOR_FIELDS
from v2.schemas.common import (
    BrandschutzKlasse,
    FieldSource,
    MaterialTyp,
    SchallschutzKlasse,
)
from v2.schemas.extraction import ExtractedDoorPosition

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Position number patterns
# ---------------------------------------------------------------------------
POSITION_NR_PATTERNS = [
    re.compile(r"T\d{1,3}\.\d{1,3}"),       # T1.01, T2.03
    re.compile(r"Pos\.?\s*\d{1,3}\.\d{1,3}"),  # Pos. 1.01, Pos 2.03
    re.compile(r"\b\d{1,3}\.\d{1,3}\b"),      # 1.01, 2.03
]

# Fire protection mapping
BRANDSCHUTZ_MAP: dict[str, BrandschutzKlasse] = {
    "EI30": BrandschutzKlasse.EI30,
    "EI60": BrandschutzKlasse.EI60,
    "EI90": BrandschutzKlasse.EI90,
    "EI120": BrandschutzKlasse.EI120,
    "E30": BrandschutzKlasse.E30,
    "E60": BrandschutzKlasse.E60,
    "E90": BrandschutzKlasse.E90,
    "T30": BrandschutzKlasse.T30,
    "T60": BrandschutzKlasse.T60,
    "T90": BrandschutzKlasse.T90,
}

# Sound protection mapping
SCHALLSCHUTZ_MAP: dict[str, SchallschutzKlasse] = {
    "27": SchallschutzKlasse.RW_27,
    "29": SchallschutzKlasse.RW_29,
    "32": SchallschutzKlasse.RW_32,
    "35": SchallschutzKlasse.RW_35,
    "37": SchallschutzKlasse.RW_37,
    "41": SchallschutzKlasse.RW_41,
    "42": SchallschutzKlasse.RW_42,
    "43": SchallschutzKlasse.RW_43,
    "44": SchallschutzKlasse.RW_44,
    "45": SchallschutzKlasse.RW_45,
    "46": SchallschutzKlasse.RW_46,
    "47": SchallschutzKlasse.RW_47,
    "53": SchallschutzKlasse.RW_53,
}

# Material mapping
MATERIAL_MAP: dict[str, MaterialTyp] = {
    "holz": MaterialTyp.HOLZ,
    "stahl": MaterialTyp.STAHL,
    "aluminium": MaterialTyp.ALUMINIUM,
    "alu": MaterialTyp.ALUMINIUM,
    "glas": MaterialTyp.GLAS,
    "kunststoff": MaterialTyp.KUNSTSTOFF,
    "eiche": MaterialTyp.EICHE,
    "buche": MaterialTyp.BUCHE,
    "fichte": MaterialTyp.FICHTE,
    "laerche": MaterialTyp.LAERCHE,
    "lärche": MaterialTyp.LAERCHE,
}

# Regex for fire protection values in text
_BRANDSCHUTZ_RE = re.compile(
    r"\b(EI(?:30|60|90|120)|E(?:30|60|90)|T(?:30|60|90))\b", re.IGNORECASE
)

# Regex for sound protection values
_SCHALLSCHUTZ_RE = re.compile(
    r"(?:Rw\s*)?(\d{2})\s*(?:dB)?", re.IGNORECASE
)

# Regex for dimension values (3-4 digit numbers likely mm)
_DIMENSION_RE = re.compile(r"\b(\d{3,4})\b")


# ---------------------------------------------------------------------------
# XLSX text extraction
# ---------------------------------------------------------------------------

def _parse_pipe_line(line: str) -> dict[str, str]:
    """Parse a pipe-delimited line into field:value dict.

    Lines from XLSX parser look like: 'tuer_nr: 1.01 | breite: 1000 | ...'
    """
    fields = {}
    parts = line.split("|")
    for part in parts:
        part = part.strip()
        if ":" in part:
            key, _, val = part.partition(":")
            fields[key.strip().lower()] = val.strip()
    return fields


def _extract_position_nr(text: str) -> Optional[str]:
    """Extract position number from text using known patterns."""
    for pattern in POSITION_NR_PATTERNS:
        match = pattern.search(text)
        if match:
            val = match.group(0)
            # Normalize: strip 'Pos.' prefix
            val = re.sub(r"^Pos\.?\s*", "", val)
            return val
    return None


def _extract_brandschutz(text: str) -> Optional[BrandschutzKlasse]:
    """Extract fire protection class from text."""
    match = _BRANDSCHUTZ_RE.search(text)
    if match:
        val = match.group(1).upper()
        return BRANDSCHUTZ_MAP.get(val)
    return None


def _extract_schallschutz(text: str) -> Optional[SchallschutzKlasse]:
    """Extract sound protection class from text."""
    match = _SCHALLSCHUTZ_RE.search(text)
    if match:
        db_val = match.group(1)
        return SCHALLSCHUTZ_MAP.get(db_val)
    return None


def _extract_schallschutz_db(text: str) -> Optional[int]:
    """Extract dB value for sound protection."""
    match = _SCHALLSCHUTZ_RE.search(text)
    if match:
        db_val = match.group(1)
        if db_val in SCHALLSCHUTZ_MAP:
            return int(db_val)
    return None


def _extract_material(text: str) -> Optional[MaterialTyp]:
    """Extract material type from text."""
    text_lower = text.lower().strip()
    for key, mat in MATERIAL_MAP.items():
        if key in text_lower:
            return mat
    return None


def _make_source(source_file: str) -> FieldSource:
    """Create a FieldSource with standard konfidenz for Pass 1."""
    return FieldSource(dokument=source_file, konfidenz=0.8)


def _extract_from_xlsx_text(
    parse_result: ParseResult,
) -> list[ExtractedDoorPosition]:
    """Extract positions from XLSX-formatted pipe-delimited text."""
    positions = []
    source_file = parse_result.source_file

    # Check if metadata says this has enough door columns
    detected = parse_result.metadata.get("detected_columns", {})
    has_door_sheet = False
    for sheet_name, col_mapping in detected.items():
        if len(col_mapping) >= _MIN_DOOR_FIELDS:
            has_door_sheet = True
            break

    if not has_door_sheet:
        return []

    for line in parse_result.text.splitlines():
        line = line.strip()
        if not line or line.startswith("==="):
            continue

        fields = _parse_pipe_line(line)
        if not fields:
            continue

        # Extract position number
        pos_nr = None
        for key in ("tuer_nr", "pos", "position", "pos.", "element-nr"):
            if key in fields:
                pos_nr = _extract_position_nr(fields[key])
                if pos_nr:
                    break

        if not pos_nr:
            # Try extracting from the whole line
            pos_nr = _extract_position_nr(line)

        if not pos_nr:
            continue

        quellen = {}
        source = _make_source(source_file)

        # Extract dimensions
        breite = None
        hoehe = None
        for key in ("breite", "breite_mm", "b [mm]", "b(mm)", "lichte breite"):
            if key in fields:
                dim_match = _DIMENSION_RE.search(fields[key])
                if dim_match:
                    breite = int(dim_match.group(1))
                    quellen["breite_mm"] = source
                break

        for key in ("hoehe", "hoehe_mm", "h [mm]", "h(mm)", "lichte hoehe", "höhe"):
            if key in fields:
                dim_match = _DIMENSION_RE.search(fields[key])
                if dim_match:
                    hoehe = int(dim_match.group(1))
                    quellen["hoehe_mm"] = source
                break

        # Extract fire protection
        brandschutz = None
        for key in ("brandschutz", "feuerschutz", "bs", "brand"):
            if key in fields:
                brandschutz = _extract_brandschutz(fields[key])
                if brandschutz:
                    quellen["brandschutz_klasse"] = source
                break

        # Extract sound protection
        schallschutz = None
        schallschutz_db = None
        for key in ("schallschutz", "ss", "rw", "schall"):
            if key in fields:
                schallschutz = _extract_schallschutz(fields[key])
                schallschutz_db = _extract_schallschutz_db(fields[key])
                if schallschutz:
                    quellen["schallschutz_klasse"] = source
                if schallschutz_db:
                    quellen["schallschutz_db"] = source
                break

        # Extract material
        material = None
        for key in ("tuertyp", "material", "konstruktion", "bauart"):
            if key in fields:
                material = _extract_material(fields[key])
                if material:
                    quellen["material_blatt"] = source
                break

        quellen["positions_nr"] = source

        positions.append(
            ExtractedDoorPosition(
                positions_nr=pos_nr,
                breite_mm=breite,
                hoehe_mm=hoehe,
                brandschutz_klasse=brandschutz,
                schallschutz_klasse=schallschutz,
                schallschutz_db=schallschutz_db,
                material_blatt=material,
                quellen=quellen,
            )
        )

    return positions


# ---------------------------------------------------------------------------
# PDF/DOCX markdown table extraction
# ---------------------------------------------------------------------------

def _parse_markdown_table(table_text: str) -> list[dict[str, str]]:
    """Parse a markdown table into a list of row dicts."""
    lines = [l.strip() for l in table_text.strip().splitlines() if l.strip()]
    if len(lines) < 3:  # Need header, separator, at least one row
        return []

    # Parse header
    header_line = lines[0]
    headers = [h.strip() for h in header_line.strip("|").split("|")]

    # Skip separator line
    rows = []
    for line in lines[2:]:
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) == len(headers):
            row = {}
            for h, c in zip(headers, cells):
                row[h.lower().strip()] = c.strip()
            rows.append(row)

    return rows


def _count_door_fields_in_headers(headers: list[str]) -> int:
    """Count how many headers match known door field patterns."""
    from v2.parsers.xlsx_parser import _best_field_match

    count = 0
    for header in headers:
        field, score = _best_field_match(header)
        if field and score >= 0.65:
            count += 1
    return count


def _extract_from_tables(
    parse_result: ParseResult,
) -> list[ExtractedDoorPosition]:
    """Extract positions from markdown tables in ParseResult.tables."""
    positions = []
    source_file = parse_result.source_file

    for table_text in parse_result.tables:
        rows = _parse_markdown_table(table_text)
        if not rows:
            continue

        # Check if this table has enough door-related headers
        headers = list(rows[0].keys())
        if _count_door_fields_in_headers(headers) < _MIN_DOOR_FIELDS:
            continue

        for row in rows:
            # Try to find position number
            pos_nr = None
            for key in row:
                pos_nr = _extract_position_nr(row[key])
                if pos_nr:
                    break

            if not pos_nr:
                continue

            quellen = {}
            source = _make_source(source_file)
            quellen["positions_nr"] = source

            # Extract dimensions from row values
            breite = None
            hoehe = None
            brandschutz = None
            schallschutz = None
            material = None

            for key, val in row.items():
                if not val:
                    continue
                key_lower = key.lower()

                # Dimensions
                if any(kw in key_lower for kw in ("breit", "width", "b ")):
                    dim_match = _DIMENSION_RE.search(val)
                    if dim_match:
                        breite = int(dim_match.group(1))
                        quellen["breite_mm"] = source

                elif any(kw in key_lower for kw in ("höh", "hoeh", "height", "h ")):
                    dim_match = _DIMENSION_RE.search(val)
                    if dim_match:
                        hoehe = int(dim_match.group(1))
                        quellen["hoehe_mm"] = source

                # Fire protection
                elif any(kw in key_lower for kw in ("brand", "feuer", "fire")):
                    brandschutz = _extract_brandschutz(val)
                    if brandschutz:
                        quellen["brandschutz_klasse"] = source

                # Sound protection
                elif any(kw in key_lower for kw in ("schall", "sound")):
                    schallschutz = _extract_schallschutz(val)
                    if schallschutz:
                        quellen["schallschutz_klasse"] = source

                # Material
                elif any(kw in key_lower for kw in ("material", "typ", "type")):
                    material = _extract_material(val)
                    if material:
                        quellen["material_blatt"] = source

            positions.append(
                ExtractedDoorPosition(
                    positions_nr=pos_nr,
                    breite_mm=breite,
                    hoehe_mm=hoehe,
                    brandschutz_klasse=brandschutz,
                    schallschutz_klasse=schallschutz,
                    material_blatt=material,
                    quellen=quellen,
                )
            )

    return positions


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_structural(parse_result: ParseResult) -> list[ExtractedDoorPosition]:
    """Extract door positions from ParseResult using regex/heuristics.

    Pass 1 in the multi-pass extraction pipeline. Runs without AI (fast, free).

    For XLSX: Parses pipe-delimited text lines with canonical field names.
    For PDF/DOCX: Parses markdown tables from parse_result.tables.

    Args:
        parse_result: Parsed document output from a v2 parser.

    Returns:
        List of ExtractedDoorPosition with field-level provenance.
    """
    if not parse_result.text and not parse_result.tables:
        return []

    if parse_result.format == "xlsx":
        return _extract_from_xlsx_text(parse_result)

    # For PDF/DOCX: extract from tables list
    if parse_result.tables:
        return _extract_from_tables(parse_result)

    return []
