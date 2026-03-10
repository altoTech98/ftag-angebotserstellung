"""
Phase 4+5: Product Matching and Adversarial Validation.

Multi-dimensional matching of extracted requirements against product catalog.
TF-IDF pre-filtering + AI scoring per dimension.
Adversarial validation via FOR/AGAINST debate with chain-of-thought reasoning.
"""

from v2.matching.tfidf_index import CatalogTfidfIndex
from v2.matching.ai_matcher import match_single_position, match_positions
from v2.matching.adversarial import (
    validate_single_position,
    validate_positions,
    ADVERSARIAL_MAX_CONCURRENT,
)

__all__ = [
    "CatalogTfidfIndex",
    "match_single_position",
    "match_positions",
    "validate_single_position",
    "validate_positions",
    "ADVERSARIAL_MAX_CONCURRENT",
]
