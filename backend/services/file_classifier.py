"""
File Classifier Service – Classifies uploaded tender documents.

3-tier heuristic:
1. Extension-based (immediate: .dwg→plan, .crbx→sonstig, .jpg→foto)
2. Filename pattern matching (türliste→tuerliste, grundriss→plan, etc.)
3. Excel header content inspection (Tür-Nr, Brandschutz columns → tuerliste)

Categories:
- tuerliste:      Primary Excel with door data (CRITICAL)
- spezifikation:  PDF/Word with additional specs (USEFUL)
- plan:           Floor plans, drawings (SKIP)
- foto:           Images (SKIP)
- sonstig:        Unknown / unsupported (SKIP)
"""

import os
import re
import logging

import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Extension → category mapping (unambiguous types)
# ---------------------------------------------------------------------------
EXTENSION_MAP = {
    # Plans / CAD
    ".dwg": "plan",
    ".dxf": "plan",
    # Images
    ".jpg": "foto",
    ".jpeg": "foto",
    ".png": "foto",
    ".bmp": "foto",
    ".tif": "foto",
    ".tiff": "foto",
    # Construction / other
    ".crbx": "sonstig",
}

# ---------------------------------------------------------------------------
# Filename patterns → category
# ---------------------------------------------------------------------------
TUERLISTE_PATTERNS = re.compile(
    r"(t[üu]rliste|t[üu]rmatrix|t[üu]rlist|tuerliste|tuermatrix|"
    r"t[üu]r[_\-\s]?liste|t[üu]r[_\-\s]?matrix|"
    r"doorlist|door[_\-\s]?schedule)",
    re.IGNORECASE,
)

PLAN_PATTERNS = re.compile(
    r"(grundriss|situationsplan|lageplan|geschossplan|"
    r"schnitt[_\-\s]plan|brandschutzplan|fassadenplan|"
    r"installationsplan|"
    r"floor[_\-\s]?plan|layout)",
    re.IGNORECASE,
)

SPEC_PATTERNS = re.compile(
    r"(leistungsverzeichnis|[_\-\s]lv[_\-\s\.]|"
    r"t[üu]rbuch|t[üu]r[_\-\s]?typicals?|t[üu]rtypisch|"
    r"spezifikation|specification|"
    r"schnittstellendefinition|schnittstelle|"
    r"anforderung|bedingung|vertrag|werkvertrag|"
    r"baubeschreibung|pflichtenheft)",
    re.IGNORECASE,
)

FOTO_PATTERNS = re.compile(
    r"(foto|photo|bild|image|aufnahme)",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Excel header keywords that indicate a door list
# ---------------------------------------------------------------------------
DOOR_HEADER_KEYWORDS = {
    "tür-nr", "türnummer", "tür nr", "tuernr", "tuer-nr",
    "pos", "position",
    "brandschutz", "feuerschutz", "feuerwiderstand",
    "schallschutz", "schalldämmung",
    "einbruchschutz", "widerstandsklasse",
    "breite", "lichte breite", "türbreite",
    "höhe", "hoehe", "lichte höhe", "türhöhe",
    "türtyp", "tuertyp", "türart",
    "geschoss", "stockwerk", "etage",
    "beschläge", "beschlag", "drücker",
}

# Minimum number of door-related headers to classify as tuerliste
MIN_DOOR_HEADERS = 3


def classify_file(filename: str, file_path: str) -> dict:
    """
    Classify a single file.

    Returns:
        {
            "category": str,       # tuerliste|spezifikation|plan|foto|sonstig
            "confidence": float,   # 0.0–1.0
            "reason": str,         # Human-readable explanation
            "parseable": bool,     # Whether the system can extract useful data
        }
    """
    ext = os.path.splitext(filename)[1].lower()

    # Tier 1: Extension-based (instant, high confidence)
    if ext in EXTENSION_MAP:
        cat = EXTENSION_MAP[ext]
        return {
            "category": cat,
            "confidence": 0.95,
            "reason": f"Dateityp {ext} → {cat}",
            "parseable": False,
        }

    # Tier 2: Filename pattern matching
    name_lower = filename.lower()

    if TUERLISTE_PATTERNS.search(name_lower) and ext in (".xlsx", ".xls", ".xlsm"):
        return {
            "category": "tuerliste",
            "confidence": 0.90,
            "reason": f"Dateiname enthält Türlisten-Muster",
            "parseable": True,
        }

    if PLAN_PATTERNS.search(name_lower):
        return {
            "category": "plan",
            "confidence": 0.85,
            "reason": f"Dateiname enthält Plan-Muster",
            "parseable": ext == ".pdf",
        }

    if FOTO_PATTERNS.search(name_lower):
        return {
            "category": "foto",
            "confidence": 0.85,
            "reason": f"Dateiname enthält Foto-Muster",
            "parseable": False,
        }

    if SPEC_PATTERNS.search(name_lower):
        return {
            "category": "spezifikation",
            "confidence": 0.85,
            "reason": f"Dateiname enthält Spezifikation-Muster",
            "parseable": True,
        }

    # Tier 3: Excel header content inspection
    if ext in (".xlsx", ".xls", ".xlsm"):
        result = _classify_excel_by_content(file_path, filename)
        if result:
            return result
        # Default for Excel without clear door headers
        return {
            "category": "spezifikation",
            "confidence": 0.50,
            "reason": "Excel-Datei ohne erkannte Türlisten-Spalten",
            "parseable": True,
        }

    # Tier 3b: PDF default → spezifikation (unless plan pattern already matched)
    if ext == ".pdf":
        return {
            "category": "spezifikation",
            "confidence": 0.60,
            "reason": "PDF-Dokument (Standard: Spezifikation)",
            "parseable": True,
        }

    # Word documents → spezifikation
    if ext in (".docx", ".doc", ".docm"):
        return {
            "category": "spezifikation",
            "confidence": 0.70,
            "reason": "Word-Dokument → Spezifikation",
            "parseable": True,
        }

    # Text files → spezifikation
    if ext == ".txt":
        return {
            "category": "spezifikation",
            "confidence": 0.60,
            "reason": "Text-Datei → Spezifikation",
            "parseable": True,
        }

    # Unknown
    return {
        "category": "sonstig",
        "confidence": 0.50,
        "reason": f"Unbekannter Dateityp ({ext})",
        "parseable": False,
    }


def classify_files(files: list[dict]) -> list[dict]:
    """
    Batch-classify multiple files.

    Input:  [{"filename": str, "file_path": str, ...}, ...]
    Output: Same dicts enriched with classification fields.
    """
    results = []
    for f in files:
        classification = classify_file(f["filename"], f["file_path"])
        results.append({**f, **classification})
    return results


def _classify_excel_by_content(file_path: str, filename: str) -> dict | None:
    """
    Inspect Excel column headers to determine if it's a door list.
    Returns classification dict or None if inconclusive.
    """
    try:
        xl = pd.ExcelFile(file_path)
        for sheet_name in xl.sheet_names:
            try:
                df = pd.read_excel(xl, sheet_name=sheet_name, header=None, nrows=15, dtype=str)
            except Exception:
                continue

            # Check each row as potential header
            for i in range(min(10, len(df))):
                row_values = df.iloc[i].dropna().astype(str).str.lower().tolist()
                row_text = " ".join(row_values)

                matches = sum(
                    1 for kw in DOOR_HEADER_KEYWORDS
                    if kw in row_text
                )

                if matches >= MIN_DOOR_HEADERS:
                    return {
                        "category": "tuerliste",
                        "confidence": min(0.60 + matches * 0.05, 0.95),
                        "reason": f"Excel enthält {matches} Türlisten-Spalten (Sheet: {sheet_name})",
                        "parseable": True,
                    }

        return None
    except Exception as e:
        logger.warning(f"Could not inspect Excel headers for {filename}: {e}")
        return None
