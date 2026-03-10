"""
Domain knowledge for Swiss door product matching.

Ported from v1 services/fast_matcher.py -- battle-tested hierarchies
for fire classes, resistance classes, and category detection keywords
derived from real FTAG catalog data.
"""

import re
from typing import Optional


# Fire class hierarchy (higher fulfills lower)
# Keys are lowercase normalized forms
FIRE_CLASS_RANK: dict[str, int] = {
    "ohne": 0, "keine": 0, "": 0, "--": 0, "nicht definiert": 0,
    "ei30": 1, "t30": 1, "f30": 1,
    "ei60": 2, "t60": 2, "f60": 2,
    "ei90": 3, "t90": 3, "f90": 3,
    "ei120": 4, "t120": 4, "f120": 4,
}

# Resistance class hierarchy
RESISTANCE_RANK: dict[str, int] = {
    "": 0, "ohne": 0, "keine": 0, "--": 0, "nicht definiert": 0,
    "rc1": 1, "wk1": 1,
    "rc2": 2, "wk2": 2,
    "rc3": 3, "wk3": 3,
    "rc4": 4, "wk4": 4,
}

# Category detection keywords (proven with FTAG data)
# Maps canonical category name -> list of detection keywords
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "Rahmentuere": [
        "rahmen", "fluegel", "innentuer", "standardtuer",
    ],
    "Zargentuere": ["zargen"],
    "Futtertuere": ["futter"],
    "Schiebetuere": ["schiebe", "sliding"],
    "Brandschutztor": ["tor", "sektional", "schnelllauf", "rolltor"],
    "Brandschutzvorhang": ["vorhang", "rollkasten"],
    "Festverglasung": ["festverglas"],
    "Ganzglas Tuer": ["ganzglas", "glastuer"],
    "Pendeltuere": ["pendel"],
    "Vollwand": ["vollwand", "trennwand"],
    "Steigzonen/Elektrofronten": ["steigzone", "elektrofront", "revision"],
}


def normalize_fire_class(val: Optional[str]) -> int:
    """Normalize fire class string to rank number.

    Handles formats like 'EI30', 'ei 60', 'T90-C', 'F30', etc.
    Returns 0 for unknown or empty values.
    """
    if not val:
        return 0
    val = val.lower().strip().replace(" ", "").replace("-", "")
    # Extract EI/T/F + number pattern
    m = re.search(r"(ei|t|f)(\d+)", val)
    if m:
        key = m.group(1) + m.group(2)
        return FIRE_CLASS_RANK.get(key, 0)
    return FIRE_CLASS_RANK.get(val, 0)


def normalize_resistance(val: Optional[str]) -> int:
    """Normalize resistance class to rank number.

    Handles formats like 'RC2', 'wk3', 'RC 2', etc.
    Returns 0 for unknown or empty values.
    """
    if not val:
        return 0
    val = val.lower().strip().replace(" ", "").replace("-", "")
    m = re.search(r"(rc|wk)(\d+)", val)
    if m:
        key = m.group(1) + m.group(2)
        return RESISTANCE_RANK.get(key, 0)
    return RESISTANCE_RANK.get(val, 0)


def detect_category(text: str) -> Optional[str]:
    """Detect product category from text using CATEGORY_KEYWORDS.

    Args:
        text: Free-text description to check for category keywords.

    Returns:
        Canonical category name if detected, None otherwise.
    """
    if not text:
        return None
    text_lower = text.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                return category
    return None
