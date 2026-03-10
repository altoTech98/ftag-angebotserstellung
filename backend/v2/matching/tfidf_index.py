"""
Weighted TF-IDF index over FTAG product catalog.

Builds a TF-IDF vectorizer with field-weighted text representations
for each product. Key matching fields (Brandschutzklasse, Schallschutz,
etc.) are boosted by repeating them in the text. Category detection
provides a 1.3x score boost for products matching the detected category.

Usage:
    index = CatalogTfidfIndex(catalog_df=df)
    results = index.search(position, top_k=50)
    # results: list of (row_idx, score) tuples
"""

import logging
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from v2.matching.domain_knowledge import detect_category
from v2.schemas.extraction import ExtractedDoorPosition

logger = logging.getLogger(__name__)

# Field weights: repeat field value N times in text representation
# to boost its TF-IDF importance
FIELD_WEIGHTS: dict[str, int] = {
    "brandschutzklasse": 4,
    "widerstandsklasse": 3,
    "schallschutz": 3,
    "tuerrohling": 3,
    "lichtmass": 2,
    "material": 2,
    "kategorie": 2,
    "produktegruppen": 2,
    "umfassung": 2,
}

# Fields to extract from catalog for sending to Claude as candidate info
MATCHING_FIELDS = [
    "Produktegruppen",
    "Brandschutzklasse",
    "VKF.Nr",
    "Lichtmass max. B x H in mm",
    "Tuerflaece max. in m2",
    "Anzahl Fluegel",
    "Tuerblatt / Verglasungsart / Rollkasten",
    "Tuerblattausfuehrung",
    "Glasausschnitt",
    "Tuerrohling (dB)",
    "Widerstandsklasse",
    "Bleigleichwert (2mm)",
    "VKF.Nr / Klasse S200",
    "Umfassung Materialisierung",
    "Giessharzbeschichtung Orsopal",
    "Oberflaechenfolie Senosan",
]

# Minimum similarity score threshold
MIN_SCORE_THRESHOLD = 0.01

# Category boost factor
CATEGORY_BOOST = 1.3


def _safe_str(val, max_len: int = 120) -> str:
    """Convert a cell value to a clean string."""
    if pd.isna(val):
        return ""
    s = str(val).strip()
    if s in ("-", "nan", "NaN", ".", ""):
        return ""
    return s[:max_len]


class CatalogTfidfIndex:
    """Weighted TF-IDF index over FTAG product catalog.

    Args:
        catalog_df: DataFrame with product catalog data.
            If None, loads from default catalog path.
    """

    def __init__(
        self,
        catalog_df: Optional[pd.DataFrame] = None,
        catalog_path: Optional[str] = None,
    ):
        if catalog_df is not None:
            self._df = catalog_df
        else:
            self._df = self._load_catalog(catalog_path)

        self._col_names = list(self._df.columns)
        self._product_texts: list[str] = []
        self._product_categories: list[str] = []

        # Build weighted text for each product
        for row_idx in range(len(self._df)):
            row = self._df.iloc[row_idx]
            text = self._build_weighted_text(row)
            self._product_texts.append(text)
            # Store category for boost
            cat = _safe_str(row.iloc[0]) if len(row) > 0 else ""
            self._product_categories.append(cat)

        # Build TF-IDF vectorizer with German-aware tokenization
        self._vectorizer = TfidfVectorizer(
            analyzer="word",
            token_pattern=r"(?u)\b[a-zA-ZaeoeueAeOeUess0-9]{2,}\b",
            max_features=5000,
            ngram_range=(1, 2),
            sublinear_tf=True,
        )
        self._tfidf_matrix = self._vectorizer.fit_transform(self._product_texts)

        logger.info(
            f"[TFIDF] Index built: {self._tfidf_matrix.shape[0]} products, "
            f"{len(self._vectorizer.vocabulary_)} features"
        )

    @staticmethod
    def _load_catalog(catalog_path: Optional[str] = None) -> pd.DataFrame:
        """Load catalog from default or specified path."""
        import os

        if catalog_path is None:
            data_dir = os.path.join(
                os.path.dirname(__file__), "..", "..", "data"
            )
            catalog_path = os.path.join(data_dir, "produktuebersicht.xlsx")

        from services.catalog_index import CATALOG_HEADER_ROW

        df = pd.read_excel(catalog_path, sheet_name=0, header=CATALOG_HEADER_ROW)
        df.columns = [str(c).strip() for c in df.columns]
        df = df.dropna(how="all").reset_index(drop=True)
        # Remove leftover header rows
        if len(df) > 0:
            first_col = df.columns[0]
            df = df[df[first_col].astype(str) != "Produktegruppen"].reset_index(
                drop=True
            )
        return df

    def _build_weighted_text(self, row: pd.Series) -> str:
        """Build weighted text for a catalog product row.

        Key fields are repeated N times based on FIELD_WEIGHTS to boost
        their TF-IDF importance.
        """
        parts: list[str] = []
        for col_idx, col_name in enumerate(self._col_names):
            if col_idx >= len(row):
                break
            val = _safe_str(row.iloc[col_idx])
            if not val:
                continue
            normalized_col = col_name.lower().replace(" ", "")
            weight = 1
            for key, w in FIELD_WEIGHTS.items():
                if key in normalized_col:
                    weight = w
                    break
            parts.extend([f"{col_name}:{val}"] * weight)
        return " ".join(parts) if parts else "Produkt"

    def _build_query_from_position(self, pos: ExtractedDoorPosition) -> str:
        """Build TF-IDF query text from an extracted door position.

        Uses all available fields with same weighting as product text.
        Falls back to "Tuer" for empty positions.
        """
        parts: list[str] = []
        if pos.brandschutz_klasse:
            parts.extend([f"Brandschutzklasse:{pos.brandschutz_klasse.value}"] * 4)
        if pos.brandschutz_freitext:
            parts.append(pos.brandschutz_freitext)
        if pos.schallschutz_db:
            parts.extend([f"Tuerrohling:{pos.schallschutz_db}dB"] * 3)
        if pos.schallschutz_klasse:
            parts.append(f"Schallschutz:{pos.schallschutz_klasse.value}")
        if pos.breite_mm and pos.hoehe_mm:
            parts.extend([f"Lichtmass:{pos.breite_mm}x{pos.hoehe_mm}mm"] * 2)
        if pos.material_blatt:
            parts.extend([f"Material:{pos.material_blatt.value}"] * 2)
        if pos.einbruchschutz_klasse:
            parts.extend([f"Widerstandsklasse:{pos.einbruchschutz_klasse}"] * 3)
        if pos.oeffnungsart:
            parts.append(f"Oeffnungsart:{pos.oeffnungsart.value}")
        if pos.anzahl_fluegel:
            parts.append(f"Fluegel:{pos.anzahl_fluegel}")
        if pos.glasausschnitt:
            parts.append("Glasausschnitt:ja")
        if pos.positions_bezeichnung:
            parts.append(pos.positions_bezeichnung)
        if pos.tuerblatt_ausfuehrung:
            parts.append(pos.tuerblatt_ausfuehrung)
        if pos.bemerkungen:
            parts.append(pos.bemerkungen)
        if parts:
            return " ".join(parts)
        # Broad fallback for sparse positions: use common product terms
        return "Tuer Rahmentuere Brandschutz Schallschutz Produkt Standard"

    def search(
        self,
        position: ExtractedDoorPosition,
        top_k: int = 50,
    ) -> list[tuple[int, float]]:
        """Search for matching products using TF-IDF cosine similarity.

        Args:
            position: Extracted door position to match.
            top_k: Maximum number of candidates to return.

        Returns:
            List of (row_index, score) tuples sorted by score descending.
            Only results above MIN_SCORE_THRESHOLD are included.
        """
        query_text = self._build_query_from_position(position)
        query_vec = self._vectorizer.transform([query_text])
        scores = cosine_similarity(query_vec, self._tfidf_matrix).flatten()

        # Apply category boost
        detected_cat = None
        # Build detection text from position
        det_parts = []
        if position.positions_bezeichnung:
            det_parts.append(position.positions_bezeichnung)
        if position.oeffnungsart:
            det_parts.append(position.oeffnungsart.value)
        if position.tuerblatt_ausfuehrung:
            det_parts.append(position.tuerblatt_ausfuehrung)
        if position.bemerkungen:
            det_parts.append(position.bemerkungen)
        det_text = " ".join(det_parts)
        if det_text:
            detected_cat = detect_category(det_text)

        if detected_cat:
            for idx in range(len(scores)):
                prod_cat = self._product_categories[idx].lower()
                det_cat_lower = detected_cat.lower()
                # Fuzzy match: check if category names overlap
                if det_cat_lower in prod_cat or prod_cat in det_cat_lower:
                    scores[idx] *= CATEGORY_BOOST

        # Sort and filter
        top_indices = scores.argsort()[::-1][:top_k]
        results = [
            (int(idx), float(scores[idx]))
            for idx in top_indices
            if scores[idx] > MIN_SCORE_THRESHOLD
        ]
        return results

    def extract_candidate_fields(self, row_idx: int) -> dict:
        """Extract matching-relevant fields for a catalog product.

        Args:
            row_idx: Row index in the catalog DataFrame.

        Returns:
            Dictionary with matching-relevant field values.
        """
        if row_idx < 0 or row_idx >= len(self._df):
            return {"row_index": row_idx}

        row = self._df.iloc[row_idx]
        fields: dict = {"row_index": row_idx}

        for col in MATCHING_FIELDS:
            if col in self._df.columns:
                val = row.get(col)
                if pd.notna(val) and str(val).strip() not in ("", "-", "nan"):
                    fields[col] = str(val).strip()

        # Add Kostentraeger as product ID
        if "Kostentraeger" in self._df.columns:
            kt = row.get("Kostentraeger")
            if pd.notna(kt):
                fields["Kostentraeger"] = str(kt).strip()

        return fields
