"""
Catalog Index – Preprocessed, category-partitioned FTAG product profiles
optimized for AI matching with Claude.

Loads the FTAG product catalog (884 products, 318 columns), builds compact
text profiles (~25-30 tokens each) for efficient Claude API usage, and
partitions products into main products vs. accessories (ZZ).
"""

import os
import re
import logging
from functools import lru_cache
from dataclasses import dataclass, field

import pandas as pd

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
PRODUCT_FILE = os.path.join(DATA_DIR, "produktuebersicht.xlsx")

# Header row in the FTAG catalog (0-indexed). Row 6 contains the actual
# column names (Produktegruppen, Brandschutzklasse, etc.)
CATALOG_HEADER_ROW = 6

# Key column indices for building compact profiles
# Main product columns
COL_CATEGORY = 0        # Produktegruppen
COL_COST_CENTER = 1     # Kostenträger
COL_LEAVES = 2          # Anzahl Flügel
COL_DOOR_TYPE = 3       # Türblatt / Verglasungsart / Rollkasten
COL_DOOR_VARIANT = 4    # Türblattausführung
COL_FIRE_CLASS = 5      # Brandschutzklasse
COL_VKF_NR = 6          # VKF.Nr
COL_LIGHT_OPENING = 8   # Lichtmass max. B x H in mm
COL_MAX_AREA = 9        # Türfläche max. in m2
COL_GLASS_CUTOUT = 15   # Glasausschnitt
COL_SOUND_DB = 17       # Türrohling (dB)
COL_RESISTANCE = 18     # Widerstandsklasse
COL_LEAD_EQUIV = 19     # Bleigleichwert (2mm)
COL_SMOKE_CLASS = 20    # VKF.Nr / Klasse S200

# ZZ Schloss columns
COL_LOCK_TYPE = 91      # Schlossart
COL_LOCK_ARTICLE = 92   # Schloss-Artikel
COL_LOCK_LEAVES = 93    # für 1-flüglig / 2-flüglig
COL_LOCK_NO_PANIC = 94  # ohne Panikfunktion
COL_LOCK_DORNMASS = 105 # Dornmass
COL_LOCK_ABSTAND = 106  # Abstand

# ZZ Glas columns
COL_GLASS_TYPE = 260    # Glasart
COL_GLASS_ARTICLE = 261 # Glas-Artikel
COL_GLASS_THICKNESS = 262  # Glas-Dicke in mm
COL_GLASS_SOUND = 263   # Schallschutz (dB)

# ZZ Schliessblech columns
COL_STRIKE_TYPE = 141   # Schliessblechart
COL_STRIKE_ARTICLE = 142  # Schliessblech-Artikel
COL_STRIKE_RESISTANCE = 147  # Widerstandsklasse


@dataclass
class ProductProfile:
    """Compact representation of a single FTAG product."""
    row_index: int                  # Row in the DataFrame (for detail lookup)
    category: str                   # e.g., "Rahmentüre", "ZZ (Schloss)"
    compact_text: str               # ~25-30 token summary for Claude
    key_fields: dict = field(default_factory=dict)  # Structured key fields


@dataclass
class CatalogIndex:
    """Pre-processed product catalog, partitioned by category."""
    df: pd.DataFrame                                   # Full DataFrame for detail lookup
    main_products: list[ProductProfile] = field(default_factory=list)
    accessories: dict[str, list[ProductProfile]] = field(default_factory=dict)
    by_category: dict[str, list[ProductProfile]] = field(default_factory=dict)
    all_profiles: list[ProductProfile] = field(default_factory=list)
    category_names: list[str] = field(default_factory=list)
    main_category_names: list[str] = field(default_factory=list)

    def get_main_by_category(self, category: str) -> list[ProductProfile]:
        """Get main products for a specific category."""
        return self.by_category.get(category, [])

    def get_accessories_by_type(self, zz_type: str) -> list[ProductProfile]:
        """Get accessories by ZZ type (e.g., 'ZZ (Schloss)')."""
        return self.accessories.get(zz_type, [])

    def get_product_detail(self, row_index: int) -> dict:
        """Get full product details for a specific row."""
        if row_index < 0 or row_index >= len(self.df):
            return {}
        row = self.df.iloc[row_index]
        result = {}
        for col in self.df.columns[:25]:
            val = row.get(col)
            if pd.notna(val) and str(val).strip() not in ("", "-", "nan"):
                result[str(col)] = str(val).strip()
        return result

    def get_product_extended(self, row_index: int) -> dict:
        """Get extended product details including compatible accessories.

        Returns dict with basic fields plus:
        - tuerschliesser: list of compatible door closers
        - baender: list of compatible hinges
        - schloesser: list of compatible locks
        - bodenabschluss: list of compatible bottom seals
        """
        if row_index < 0 or row_index >= len(self.df):
            return {}
        row = self.df.iloc[row_index]
        ncols = len(self.df.columns)

        def _val(idx):
            if idx >= ncols:
                return ""
            v = row.iloc[idx]
            if pd.isna(v):
                return ""
            s = str(v).strip()
            return "" if s in ("-", "nan", "NaN", ".") else s

        def _ja_cols(start, end):
            """Collect column names where value is 'ja'."""
            result = []
            for i in range(start, min(end, ncols)):
                v = row.iloc[i]
                if pd.notna(v) and str(v).strip().lower() == "ja":
                    result.append(str(self.df.columns[i]).strip())
            return result

        # Zargen compatibility
        zargen_types = []
        for idx, label in [(53, "MBW"), (54, "LBW"), (55, "Steckzargen"), (56, "OS-Zarge")]:
            if idx < ncols:
                v = row.iloc[idx]
                if pd.notna(v) and str(v).strip().lower() == "ja":
                    zargen_types.append(label)

        # Oberfläche: split into Umfassung (frame) and Türblatt (leaf)
        giessharz = _val(22)  # Giessharzbeschichtung Orsopal
        senosan = _val(23)    # Oberflächenfolie Senosan
        umf_material = _val(16)  # Umfassung Materialisierung

        # Türblatt surface: KH (Kunstharz) or Folie
        oberfl_tuerblatt = ""
        if giessharz.lower() == "ja":
            oberfl_tuerblatt = "KH"
        elif senosan.lower() == "ja":
            oberfl_tuerblatt = "Folie"

        # Umfassung surface: from material column (e.g. "grundiert"), or same as Türblatt
        oberfl_umfassung = umf_material if umf_material else oberfl_tuerblatt

        ext = {
            "kostentraeger": _val(COL_COST_CENTER),
            "tuerblatt": _val(COL_DOOR_TYPE),
            "tuerblattausfuehrung": _val(COL_DOOR_VARIANT),
            "anzahl_fluegel": _val(COL_LEAVES),
            "brandschutzklasse": _val(COL_FIRE_CLASS),
            "lichtmass_max": _val(COL_LIGHT_OPENING),
            "umfassung_material": umf_material,
            "oberflaeche_umfassung": oberfl_umfassung,
            "oberflaeche_tuerblatt": oberfl_tuerblatt,
            "schallschutz_db": _val(COL_SOUND_DB),
            "widerstandsklasse": _val(COL_RESISTANCE),
            "glasausschnitt": _val(COL_GLASS_CUTOUT),
            "zargen_types": zargen_types,
            "tuerschliesser": _ja_cols(76, 90),
            "baender": _ja_cols(210, 239),
            "schloesser": _ja_cols(120, 140),
            "bodenabschluss": _ja_cols(253, 259),
        }
        return ext


def _safe_str(val, max_len: int = 80) -> str:
    """Convert a cell value to a clean string, or empty string."""
    if pd.isna(val):
        return ""
    s = str(val).strip()
    if s in ("-", "nan", "NaN", ".", ""):
        return ""
    return s[:max_len]


def _build_main_product_profile(row, row_idx: int, col_names: list[str]) -> ProductProfile:
    """Build a compact profile for a main product (Rahmentüre, Zargentüre, etc.)."""
    category = _safe_str(row.iloc[COL_CATEGORY])
    door_type = _safe_str(row.iloc[COL_DOOR_TYPE])
    door_variant = _safe_str(row.iloc[COL_DOOR_VARIANT])
    leaves = _safe_str(row.iloc[COL_LEAVES])
    fire_class = _safe_str(row.iloc[COL_FIRE_CLASS])
    light_opening = _safe_str(row.iloc[COL_LIGHT_OPENING])
    sound_db = _safe_str(row.iloc[COL_SOUND_DB])
    resistance = _safe_str(row.iloc[COL_RESISTANCE])
    glass_cutout = _safe_str(row.iloc[COL_GLASS_CUTOUT])
    lead_equiv = _safe_str(row.iloc[COL_LEAD_EQUIV])
    smoke_class = _safe_str(row.iloc[COL_SMOKE_CLASS])
    max_area = _safe_str(row.iloc[COL_MAX_AREA])

    # Build compact text: [Row N] Category | DoorType | Leaves | FireClass | ...
    parts = [f"[{row_idx}]", category]
    if door_type:
        parts.append(door_type)
    if door_variant:
        parts.append(door_variant)
    if leaves:
        parts.append(leaves)
    if fire_class:
        parts.append(fire_class)
    if resistance:
        parts.append(resistance)
    if sound_db:
        parts.append(f"Rw={sound_db}dB")
    if light_opening:
        parts.append(f"max {light_opening}")
    if glass_cutout and glass_cutout.lower() == "ja":
        parts.append("Glasausschnitt")
    if lead_equiv:
        parts.append(f"Blei={lead_equiv}")

    compact_text = " | ".join(parts)

    key_fields = {
        "category": category,
        "door_type": door_type,
        "door_variant": door_variant,
        "leaves": leaves,
        "fire_class": fire_class,
        "light_opening": light_opening,
        "sound_db": sound_db,
        "resistance": resistance,
        "glass_cutout": glass_cutout,
        "lead_equiv": lead_equiv,
        "smoke_class": smoke_class,
        "max_area": max_area,
    }
    # Remove empty values
    key_fields = {k: v for k, v in key_fields.items() if v}

    return ProductProfile(
        row_index=row_idx,
        category=category,
        compact_text=compact_text,
        key_fields=key_fields,
    )


def _build_lock_profile(row, row_idx: int) -> ProductProfile:
    """Build a compact profile for a ZZ (Schloss) product."""
    lock_type = _safe_str(row.iloc[COL_LOCK_TYPE])
    lock_article = _safe_str(row.iloc[COL_LOCK_ARTICLE])
    lock_leaves = _safe_str(row.iloc[COL_LOCK_LEAVES])
    dornmass = _safe_str(row.iloc[COL_LOCK_DORNMASS])
    abstand = _safe_str(row.iloc[COL_LOCK_ABSTAND])

    # Collect panic functions
    panic_funcs = []
    for col_idx in range(94, 102):
        if col_idx < len(row):
            val = _safe_str(row.iloc[col_idx])
            if val.lower() == "ja":
                panic_funcs.append(str(row.index[col_idx])[:30] if hasattr(row, 'index') else f"Panik_{col_idx}")

    parts = [f"[{row_idx}]", "Schloss"]
    if lock_type:
        parts.append(lock_type)
    if lock_article:
        parts.append(lock_article[:60])
    if lock_leaves:
        parts.append(lock_leaves)
    if dornmass:
        parts.append(f"DM={dornmass}")
    if panic_funcs:
        parts.append(f"Panik: {', '.join(panic_funcs[:3])}")

    compact_text = " | ".join(parts)

    key_fields = {
        "category": "ZZ (Schloss)",
        "lock_type": lock_type,
        "lock_article": lock_article,
        "lock_leaves": lock_leaves,
        "dornmass": dornmass,
        "abstand": abstand,
        "panic_functions": panic_funcs,
    }
    key_fields = {k: v for k, v in key_fields.items() if v}

    return ProductProfile(
        row_index=row_idx,
        category="ZZ (Schloss)",
        compact_text=compact_text,
        key_fields=key_fields,
    )


def _build_glass_profile(row, row_idx: int) -> ProductProfile:
    """Build a compact profile for a ZZ (Glas) product."""
    glass_type = _safe_str(row.iloc[COL_GLASS_TYPE])
    glass_article = _safe_str(row.iloc[COL_GLASS_ARTICLE])
    glass_thickness = _safe_str(row.iloc[COL_GLASS_THICKNESS])
    glass_sound = _safe_str(row.iloc[COL_GLASS_SOUND])

    parts = [f"[{row_idx}]", "Glas"]
    if glass_type:
        parts.append(glass_type)
    if glass_article:
        parts.append(glass_article[:60])
    if glass_thickness:
        parts.append(f"{glass_thickness}mm")
    if glass_sound:
        parts.append(f"Rw={glass_sound}")

    compact_text = " | ".join(parts)

    key_fields = {
        "category": "ZZ (Glas)",
        "glass_type": glass_type,
        "glass_article": glass_article,
        "glass_thickness": glass_thickness,
        "glass_sound": glass_sound,
    }
    key_fields = {k: v for k, v in key_fields.items() if v}

    return ProductProfile(
        row_index=row_idx,
        category="ZZ (Glas)",
        compact_text=compact_text,
        key_fields=key_fields,
    )


def _build_strike_plate_profile(row, row_idx: int) -> ProductProfile:
    """Build a compact profile for a ZZ (Schliessblech) product."""
    strike_type = _safe_str(row.iloc[COL_STRIKE_TYPE])
    strike_article = _safe_str(row.iloc[COL_STRIKE_ARTICLE])
    strike_resistance = _safe_str(row.iloc[COL_STRIKE_RESISTANCE])

    parts = [f"[{row_idx}]", "Schliessblech"]
    if strike_type:
        parts.append(strike_type)
    if strike_article:
        parts.append(strike_article[:60])
    if strike_resistance:
        parts.append(strike_resistance)

    compact_text = " | ".join(parts)

    key_fields = {
        "category": "ZZ (Schliessblech)",
        "strike_type": strike_type,
        "strike_article": strike_article,
        "strike_resistance": strike_resistance,
    }
    key_fields = {k: v for k, v in key_fields.items() if v}

    return ProductProfile(
        row_index=row_idx,
        category="ZZ (Schliessblech)",
        compact_text=compact_text,
        key_fields=key_fields,
    )


def _load_catalog_df() -> pd.DataFrame:
    """Load the FTAG catalog with the correct header row."""
    if not os.path.exists(PRODUCT_FILE):
        raise FileNotFoundError(
            f"Product catalog not found at: {PRODUCT_FILE}\n"
            "Please place 'produktuebersicht.xlsx' in the data/ directory."
        )

    df = pd.read_excel(PRODUCT_FILE, sheet_name=0, header=CATALOG_HEADER_ROW)
    df.columns = [str(c).strip() for c in df.columns]
    df = df.dropna(how="all").reset_index(drop=True)

    # Remove the "Produktegruppen" row that's actually a leftover header
    if len(df) > 0:
        first_col = df.columns[0]
        df = df[df[first_col].astype(str) != "Produktegruppen"].reset_index(drop=True)

    logger.info(f"Loaded FTAG catalog: {len(df)} products, {len(df.columns)} columns")
    return df


@lru_cache(maxsize=1)
def get_catalog_index() -> CatalogIndex:
    """
    Build and cache the catalog index.
    Call this at startup to preload.
    """
    df = _load_catalog_df()
    col_names = list(df.columns)

    all_profiles = []
    main_products = []
    accessories = {"ZZ (Schloss)": [], "ZZ (Glas)": [], "ZZ (Schliessblech)": []}
    by_category = {}

    for row_idx, row in df.iterrows():
        category = _safe_str(row.iloc[COL_CATEGORY])
        if not category:
            continue

        # Build profile based on category
        if "Schloss" in category:
            profile = _build_lock_profile(row, row_idx)
            accessories.setdefault("ZZ (Schloss)", []).append(profile)
        elif "Glas" in category and "ZZ" in category:
            profile = _build_glass_profile(row, row_idx)
            accessories.setdefault("ZZ (Glas)", []).append(profile)
        elif "Schliessblech" in category:
            profile = _build_strike_plate_profile(row, row_idx)
            accessories.setdefault("ZZ (Schliessblech)", []).append(profile)
        else:
            profile = _build_main_product_profile(row, row_idx, col_names)
            main_products.append(profile)

        all_profiles.append(profile)
        by_category.setdefault(category, []).append(profile)

    # Build category name lists
    category_names = sorted(by_category.keys())
    main_category_names = [c for c in category_names if "ZZ" not in c]

    index = CatalogIndex(
        df=df,
        main_products=main_products,
        accessories=accessories,
        by_category=by_category,
        all_profiles=all_profiles,
        category_names=category_names,
        main_category_names=main_category_names,
    )

    logger.info(
        f"Catalog index built: {len(main_products)} main products, "
        f"{sum(len(v) for v in accessories.values())} accessories, "
        f"{len(category_names)} categories"
    )
    for cat, products in sorted(by_category.items(), key=lambda x: -len(x[1])):
        logger.info(f"  {cat}: {len(products)} products")

    return index


def format_products_for_claude(profiles: list[ProductProfile]) -> str:
    """Format a list of product profiles as compact text for Claude prompts."""
    return "\n".join(p.compact_text for p in profiles)


def invalidate_catalog_cache():
    """Clear the catalog index cache (call after catalog file changes)."""
    get_catalog_index.cache_clear()


def reload_catalog():
    """Force reload of the entire catalog index (used for recovery)."""
    logger.info("Reloading catalog index...")
    invalidate_catalog_cache()
    index = get_catalog_index()
    logger.info(f"Catalog reloaded: {len(index.main_products)} main products")
    return index
