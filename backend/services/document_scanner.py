"""
Document Scanner – Scans supplementary documents for door-related data
and enriches the Tuerliste (door list) with found properties.

Uses fast regex-based extraction (no LLM calls).
Only fills EMPTY fields in doors – never overwrites existing data.
"""

import os
import re
import logging

from services.document_parser import parse_document_bytes, parse_pdf_specs_bytes

logger = logging.getLogger(__name__)

# Fields that can be enriched from scanned documents
ENRICHABLE_FIELDS = [
    "brandschutz", "schallschutz", "einbruchschutz",
    "verglasung", "oberflaechenbehandlung", "zubehoer",
    "besonderheiten", "breite", "hoehe",
]


def scan_and_enrich(
    doors: list[dict],
    spec_files: list[dict],
    cached_files: dict,
    on_progress=None,
) -> list[dict]:
    """
    Scan supplementary documents and enrich door positions with found data.

    Args:
        doors: List of door position dicts (from Tuerliste)
        spec_files: List of file info dicts with keys: file_id, filename, category, parseable
        cached_files: Dict mapping file_id -> raw file bytes
        on_progress: Optional callback for progress updates

    Returns:
        Enriched list of door dicts (same length, modified in place).
    """
    if not doors or not spec_files:
        return doors

    # Collect door numbers for matching
    door_nrs = [d.get("tuer_nr", d.get("position", "")) for d in doors]

    all_properties = []
    general_reqs_parts = []

    # Scan each spec document (limit to 5 to avoid excessive processing)
    scannable = [f for f in spec_files if f.get("parseable", True)][:5]

    for i, sf in enumerate(scannable):
        file_bytes = cached_files.get(sf["file_id"])
        if not file_bytes:
            continue

        filename = sf.get("filename", "unknown")
        if on_progress:
            on_progress(f"Dokument {i+1}/{len(scannable)} wird gescannt: {filename}")

        # Parse document fully (not truncated)
        try:
            ext = os.path.splitext(filename)[1].lower()
            if ext == ".pdf":
                text = parse_pdf_specs_bytes(file_bytes, max_chars=50000)
            else:
                text = parse_document_bytes(file_bytes, ext)
        except Exception as e:
            logger.warning(f"Failed to parse {filename} for scanning: {e}")
            continue

        if not text or len(text.strip()) < 20:
            continue

        # Scan with fast regex extraction (no LLM)
        try:
            scan_result = _regex_scan(text, filename)
        except Exception as e:
            logger.warning(f"Document scan failed for {filename}: {e}")
            continue

        if not scan_result.get("is_relevant"):
            logger.info(f"Document not door-relevant: {filename}")
            continue

        logger.info(f"Found {len(scan_result.get('door_properties', []))} door properties in {filename}")

        all_properties.extend(scan_result.get("door_properties", []))

        if scan_result.get("general_requirements"):
            general_reqs_parts.append(scan_result["general_requirements"])

    if not all_properties and not general_reqs_parts:
        logger.info("No door data found in supplementary documents")
        return doors

    # Merge scanned data into doors
    enriched_count = _merge_scanned_data(doors, all_properties, door_nrs)

    # Apply general requirements to doors with empty fields
    if general_reqs_parts:
        general_count = _apply_general_requirements(doors, general_reqs_parts)
        enriched_count += general_count

    logger.info(f"Document scanning complete: {enriched_count} fields enriched across {len(doors)} doors")
    return doors


def _regex_scan(text: str, filename: str = "") -> dict:
    """
    Fast regex-based document scan for door-related data.
    Replaces the slow Ollama LLM call with pure pattern matching.
    """
    result = {
        "is_relevant": False,
        "door_properties": [],
        "general_requirements": "",
    }

    if not text or not text.strip():
        return result

    text_lower = text.lower()

    # Check relevance
    door_keywords = [
        "tuer", "tür", "door", "ei30", "ei60", "t30", "t60",
        "brandschutz", "schallschutz", "rc2", "rc3", "wk2",
        "rauchschutz", "zargen", "fluegel", "flügel",
    ]
    relevance_count = sum(1 for kw in door_keywords if kw in text_lower)
    if relevance_count < 2:
        return result

    result["is_relevant"] = True

    # Extract fire classes
    fire_classes = set()
    for m in re.finditer(r'(EI|T|F)\s*(\d{2,3})', text, re.IGNORECASE):
        fire_classes.add(f"{m.group(1).upper()}{m.group(2)}")

    # Extract resistance classes
    resistance = set()
    for m in re.finditer(r'(RC|WK)\s*(\d)', text, re.IGNORECASE):
        resistance.add(f"{m.group(1).upper()}{m.group(2)}")

    # Extract sound ratings
    sound = set()
    for m in re.finditer(r'(?:Rw\s*=?\s*)?(\d{2,3})\s*dB', text, re.IGNORECASE):
        db_val = int(m.group(1))
        if 15 <= db_val <= 60:
            sound.add(f"Rw={m.group(1)}dB")

    # Extract RAL colors
    ral_colors = set()
    for m in re.finditer(r'RAL\s*(\d{4})', text, re.IGNORECASE):
        ral_colors.add(f"RAL {m.group(1)}")

    # Extract smoke protection
    smoke = set()
    for m in re.finditer(r'(S200|S[_\s]*200|Rauchschutz)', text, re.IGNORECASE):
        smoke.add("S200")

    # Extract dimensions (BxH)
    dimensions = []
    for m in re.finditer(r'(\d{3,4})\s*[xX×]\s*(\d{3,4})', text):
        dimensions.append((int(m.group(1)), int(m.group(2))))

    # Extract door numbers with context-aware property assignment
    door_nrs = {}
    for m in re.finditer(
        r'(?:Pos(?:ition)?\.?\s*|T(?:uer|ür)?\.?\s*)(\d+(?:[.\-/]\d+)*)',
        text, re.IGNORECASE,
    ):
        nr = m.group(0).strip()
        # Grab surrounding context (200 chars around match)
        start = max(0, m.start() - 100)
        end = min(len(text), m.end() + 200)
        context = text[start:end]
        door_nrs[nr] = context

    # Build per-door properties from context
    if door_nrs:
        for nr, context in list(door_nrs.items())[:50]:
            prop = {"tuer_nr": nr}
            fc = re.search(r'(EI|T|F)\s*(\d{2,3})', context, re.IGNORECASE)
            if fc:
                prop["brandschutz"] = f"{fc.group(1).upper()}{fc.group(2)}"
            rc = re.search(r'(RC|WK)\s*(\d)', context, re.IGNORECASE)
            if rc:
                prop["einbruchschutz"] = f"{rc.group(1).upper()}{rc.group(2)}"
            snd = re.search(r'(?:Rw\s*=?\s*)?(\d{2,3})\s*dB', context, re.IGNORECASE)
            if snd and 15 <= int(snd.group(1)) <= 60:
                prop["schallschutz"] = f"Rw={snd.group(1)}dB"
            ral = re.search(r'RAL\s*(\d{4})', context, re.IGNORECASE)
            if ral:
                prop["oberflaechenbehandlung"] = f"RAL {ral.group(1)}"
            dim = re.search(r'(\d{3,4})\s*[xX×]\s*(\d{3,4})', context)
            if dim:
                prop["breite"] = int(dim.group(1))
                prop["hoehe"] = int(dim.group(2))
            smk = re.search(r'(S200|Rauchschutz)', context, re.IGNORECASE)
            if smk:
                prop["besonderheiten"] = "Rauchschutz S200"
            result["door_properties"].append(prop)
    else:
        # No specific door numbers — create general properties
        if fire_classes or resistance or sound:
            prop = {}
            if fire_classes:
                prop["brandschutz"] = ", ".join(sorted(fire_classes))
            if resistance:
                prop["einbruchschutz"] = ", ".join(sorted(resistance))
            if sound:
                prop["schallschutz"] = ", ".join(sorted(sound))
            if ral_colors:
                prop["oberflaechenbehandlung"] = ", ".join(sorted(ral_colors))
            result["door_properties"].append(prop)

    # General requirements text
    general = []
    if ral_colors:
        general.append(f"Oberflaeche: {', '.join(sorted(ral_colors))}")
    if fire_classes:
        general.append(f"Brandschutz: {', '.join(sorted(fire_classes))}")
    if resistance:
        general.append(f"Einbruchschutz: {', '.join(sorted(resistance))}")
    if sound:
        general.append(f"Schallschutz: {', '.join(sorted(sound))}")
    if smoke:
        general.append("Rauchschutz: S200")
    result["general_requirements"] = "; ".join(general)

    logger.info(
        f"Regex scan ({filename}): relevant=True, "
        f"properties={len(result['door_properties'])}, general='{result['general_requirements']}'"
    )
    return result


def _merge_scanned_data(doors: list[dict], properties: list[dict], door_nrs: list[str]) -> int:
    """
    Merge scanned door properties into the door list.
    Only fills empty/null fields, never overwrites.

    Returns count of fields enriched.
    """
    enriched = 0

    for prop in properties:
        scanned_nr = prop.get("tuer_nr")

        if scanned_nr:
            # Try to match to a specific door
            match_idx = _match_door_number(scanned_nr, door_nrs)
            if match_idx is not None:
                enriched += _enrich_door(doors[match_idx], prop)
        else:
            # No door number - skip (general requirements handled separately)
            pass

    return enriched


def _apply_general_requirements(doors: list[dict], general_parts: list[str]) -> int:
    """
    Apply general requirements (that apply to all doors) to empty fields.
    E.g., "alle Tueren RAL 9010" -> set oberflaechenbehandlung where empty.

    Returns count of fields enriched.
    """
    enriched = 0
    general_text = " ".join(general_parts)

    # Parse general requirements
    general_props = {}

    # Fire class from general requirements
    fc = re.search(r'(?:alle|saemtliche|generell).*?(EI|T)\s*(\d{2,3})', general_text, re.IGNORECASE)
    if fc:
        general_props["brandschutz"] = f"{fc.group(1).upper()}{fc.group(2)}"

    # RAL color from general requirements
    ral = re.search(r'(?:alle|saemtliche|generell).*?RAL\s*(\d{4})', general_text, re.IGNORECASE)
    if not ral:
        ral = re.search(r'RAL\s*(\d{4})', general_text, re.IGNORECASE)
    if ral:
        general_props["oberflaechenbehandlung"] = f"RAL {ral.group(1)}"

    # Resistance from general requirements
    rc = re.search(r'(?:alle|saemtliche|generell).*?(RC|WK)\s*(\d)', general_text, re.IGNORECASE)
    if rc:
        general_props["einbruchschutz"] = f"{rc.group(1).upper()}{rc.group(2)}"

    # Sound from general requirements
    snd = re.search(r'(?:alle|saemtliche|generell).*?(\d{2,3})\s*dB', general_text, re.IGNORECASE)
    if snd:
        general_props["schallschutz"] = f"Rw={snd.group(1)}dB"

    if not general_props:
        return 0

    # Apply to doors where field is empty
    for door in doors:
        for field, value in general_props.items():
            if not door.get(field):
                door[field] = value
                enriched += 1

    return enriched


def _enrich_door(door: dict, prop: dict) -> int:
    """
    Enrich a single door dict with scanned properties.
    Only fills empty/null fields. Returns count of fields set.
    """
    enriched = 0
    for field in ENRICHABLE_FIELDS:
        if field not in prop:
            continue
        val = prop[field]
        if not val:
            continue
        # Only fill if door field is empty/null
        if not door.get(field):
            door[field] = val
            enriched += 1
    return enriched


def _match_door_number(scanned_nr: str, door_nrs: list[str]) -> int | None:
    """
    Fuzzy-match a scanned door number to the door list.
    Handles variations like "T1.01" vs "1.01" vs "Pos 1.01" vs "Position 1.01".

    Returns index into door_nrs or None.
    """
    if not scanned_nr:
        return None

    scanned_clean = _normalize_door_nr(scanned_nr)

    # Exact match first
    for i, nr in enumerate(door_nrs):
        if _normalize_door_nr(nr) == scanned_clean:
            return i

    # Partial match: scanned number ends with door number or vice versa
    for i, nr in enumerate(door_nrs):
        nr_clean = _normalize_door_nr(nr)
        if nr_clean and scanned_clean:
            if nr_clean.endswith(scanned_clean) or scanned_clean.endswith(nr_clean):
                return i

    # Numeric-only match
    scanned_digits = re.sub(r'[^\d.]', '', scanned_clean)
    if scanned_digits:
        for i, nr in enumerate(door_nrs):
            nr_digits = re.sub(r'[^\d.]', '', _normalize_door_nr(nr))
            if nr_digits == scanned_digits:
                return i

    return None


def _normalize_door_nr(nr: str) -> str:
    """Normalize a door number for comparison."""
    if not nr:
        return ""
    # Remove common prefixes
    nr = re.sub(r'^(?:Pos(?:ition)?\.?\s*|T(?:uer|ür)?\.?\s*)', '', str(nr).strip(), flags=re.IGNORECASE)
    # Remove whitespace
    nr = nr.strip().lower()
    return nr
