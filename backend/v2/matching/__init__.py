"""
Phase 4: Product Matching.

Multi-dimensional matching of extracted requirements against product catalog.
TF-IDF pre-filtering + AI scoring per dimension.
"""

from v2.matching.tfidf_index import CatalogTfidfIndex
from v2.matching.ai_matcher import match_single_position, match_positions

__all__ = [
    "CatalogTfidfIndex",
    "match_single_position",
    "match_positions",
]
