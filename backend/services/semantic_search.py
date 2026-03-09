"""
Semantic Search Service – TF-IDF + Cosine Similarity for product matching.

Builds a TF-IDF index over product compact texts + expanded descriptions.
Finds semantically similar products for a given requirement text.
No external API needed – runs entirely locally.

Usage:
    from services.semantic_search import get_semantic_index
    index = get_semantic_index()
    candidates = index.search("Brandschutztür EI30 RC2 900x2100", top_k=30)
"""

import logging
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)


# Domain-specific synonyms for Swiss/German door terminology
SYNONYMS = {
    # Fire protection
    "brandschutz": ["feuerschutz", "feuerwiderstand", "brandschutztür", "feuerschutztür"],
    "ei30": ["t30", "f30", "el30", "brandschutz30"],
    "ei60": ["t60", "f60", "el60", "brandschutz60"],
    "ei90": ["t90", "f90", "el90", "brandschutz90"],
    # Break-in resistance
    "einbruchschutz": ["einbruchhemmend", "widerstandsklasse", "sicherheitstür"],
    "rc2": ["wk2", "einbruchschutz2"],
    "rc3": ["wk3", "einbruchschutz3"],
    # Sound insulation
    "schallschutz": ["schalldämmung", "schallschutztür", "schallschutzklasse"],
    # Door types
    "rahmentüre": ["rahmentür", "stahltüre", "stahltür", "stahlrahmentür"],
    "zargentüre": ["zargentür", "holzzargentür"],
    "holztüre": ["holztür", "innentür", "innentüre"],
    "glastüre": ["glastür", "ganzglastür"],
    "schiebetüre": ["schiebetür", "schiebeelement"],
    # Components
    "glasausschnitt": ["lichtausschnitt", "sichtfenster", "glaseinsatz"],
    "rauchschutz": ["rauchdicht", "rauchschutztür", "s200"],
    "fluegel": ["flügel", "türflügel", "drehflügel"],
    "zarge": ["türzarge", "stahlzarge", "holzzarge", "umfassungszarge"],
    # Materials
    "stahl": ["metall", "stahlblech"],
    "holz": ["massivholz", "holzwerkstoff"],
    "aluminium": ["alu", "aluminiumtür"],
}


@dataclass
class SearchResult:
    """A single search result with score and product profile."""
    row_index: int
    score: float
    category: str
    compact_text: str


class SemanticIndex:
    """TF-IDF based semantic search index over product catalog."""

    def __init__(self, profiles: list, synonym_map: dict = None):
        """
        Build the TF-IDF index from product profiles.

        Args:
            profiles: List of ProductProfile objects from catalog_index.
            synonym_map: Optional synonym expansion dict.
        """
        self._profiles = profiles
        self._synonym_map = synonym_map or SYNONYMS
        self._row_to_idx = {}  # row_index → list index

        # Build expanded corpus: each product gets enriched text
        corpus = []
        for i, p in enumerate(profiles):
            self._row_to_idx[p.row_index] = i
            expanded = self._expand_text(p.compact_text, p.key_fields)
            corpus.append(expanded)

        # Fit TF-IDF with German-aware tokenization
        self._vectorizer = TfidfVectorizer(
            analyzer="word",
            token_pattern=r"(?u)\b[a-zA-ZäöüÄÖÜß0-9]{2,}\b",
            lowercase=True,
            max_features=5000,
            ngram_range=(1, 2),  # Unigrams + bigrams
            sublinear_tf=True,
        )
        self._tfidf_matrix = self._vectorizer.fit_transform(corpus)

        logger.info(
            f"[SEMANTIC] Index built: {len(profiles)} products, "
            f"{len(self._vectorizer.vocabulary_)} features"
        )

    def _expand_text(self, compact_text: str, key_fields: dict) -> str:
        """Expand a product's compact text with synonyms and key field values."""
        parts = [compact_text]

        # Add key field values as extra terms
        for key, val in key_fields.items():
            if val:
                parts.append(str(val))

        text = " ".join(parts).lower()

        # Add synonyms for known terms
        extra = []
        for term, synonyms in self._synonym_map.items():
            if term in text:
                extra.extend(synonyms)

        if extra:
            text += " " + " ".join(extra)

        return text

    def _expand_query(self, query: str, fields: dict = None) -> str:
        """Expand a search query with synonyms and structured fields."""
        parts = [query]

        if fields:
            for key in ("tuertyp", "brandschutz", "schallschutz", "einbruchschutz",
                         "verglasung", "zargentyp", "besonderheiten", "rauchschutz"):
                val = fields.get(key)
                if val:
                    parts.append(str(val))

        text = " ".join(parts).lower()

        # Expand with synonyms
        extra = []
        for term, synonyms in self._synonym_map.items():
            if term in text:
                extra.extend(synonyms)

        if extra:
            text += " " + " ".join(extra)

        return text

    def search(
        self,
        query: str,
        fields: dict = None,
        top_k: int = 30,
        category_filter: str = None,
        min_score: float = 0.05,
    ) -> list[SearchResult]:
        """
        Find semantically similar products for a requirement.

        Args:
            query: Free-text requirement description.
            fields: Structured fields dict (brandschutz, schallschutz, etc.).
            top_k: Maximum number of results.
            category_filter: Optional category name to restrict search.
            min_score: Minimum cosine similarity score.

        Returns:
            List of SearchResult sorted by score descending.
        """
        expanded_query = self._expand_query(query, fields)
        query_vec = self._vectorizer.transform([expanded_query])
        scores = cosine_similarity(query_vec, self._tfidf_matrix).flatten()

        # Build results
        results = []
        for idx, score in enumerate(scores):
            if score < min_score:
                continue
            p = self._profiles[idx]
            if category_filter and p.category != category_filter:
                continue
            results.append(SearchResult(
                row_index=p.row_index,
                score=float(score),
                category=p.category,
                compact_text=p.compact_text,
            ))

        # Sort by score descending, take top_k
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    def search_multi_category(
        self,
        query: str,
        fields: dict = None,
        top_k_per_category: int = 10,
        top_k_total: int = 30,
        min_score: float = 0.05,
    ) -> list[SearchResult]:
        """
        Search across all categories, returning top results per category.
        Ensures diversity in results across product types.
        """
        expanded_query = self._expand_query(query, fields)
        query_vec = self._vectorizer.transform([expanded_query])
        scores = cosine_similarity(query_vec, self._tfidf_matrix).flatten()

        # Group by category
        by_category: dict[str, list[SearchResult]] = {}
        for idx, score in enumerate(scores):
            if score < min_score:
                continue
            p = self._profiles[idx]
            if p.category not in by_category:
                by_category[p.category] = []
            by_category[p.category].append(SearchResult(
                row_index=p.row_index,
                score=float(score),
                category=p.category,
                compact_text=p.compact_text,
            ))

        # Take top_k per category, then merge
        all_results = []
        for cat, cat_results in by_category.items():
            cat_results.sort(key=lambda r: r.score, reverse=True)
            all_results.extend(cat_results[:top_k_per_category])

        # Final sort and limit
        all_results.sort(key=lambda r: r.score, reverse=True)
        return all_results[:top_k_total]


@lru_cache(maxsize=1)
def get_semantic_index() -> SemanticIndex:
    """Get or build the semantic search index (cached singleton)."""
    from services.catalog_index import get_catalog_index
    catalog = get_catalog_index()
    return SemanticIndex(catalog.main_products)


def invalidate_semantic_cache():
    """Clear the semantic index cache (call after catalog reload)."""
    get_semantic_index.cache_clear()
