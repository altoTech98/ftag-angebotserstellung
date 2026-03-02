"""
Product Matcher – Loads the FTAG product list and matches extracted requirements.
Supports both simple keyword matching (fallback) and AI-powered matching with feedback learning.
"""

import os
import re
import logging
import numpy as np
import pandas as pd
from functools import lru_cache
from typing import Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from services.feedback_store import find_relevant_feedback

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# SYNONYM DICTIONARY (domain-specific)
# ─────────────────────────────────────────────

# Maps alternative terms → canonical search terms for pre-filtering
SYNONYMS = {
    # Türtyp
    "metalltür": ["Stahltür", "Stahl"],
    "metalltüre": ["Stahltür", "Stahl"],
    "stahltüre": ["Stahltür", "Stahl"],
    "holztüre": ["Holztür", "Holz"],
    "alutüre": ["Alutür", "Alu", "Aluminium"],
    "feuerschutztür": ["Brandschutztür", "Brand", "T30", "T60", "T90"],
    "feuerschutztüre": ["Brandschutztür", "Brand", "T30", "T60", "T90"],
    "brandschutztüre": ["Brandschutztür", "Brand", "T30", "T60", "T90"],
    "sicherheitstür": ["RC", "WK", "Sicherheit"],
    "sicherheitstüre": ["RC", "WK", "Sicherheit"],
    "fluchttür": ["Paniktür", "Flucht", "Panik"],
    "fluchttüre": ["Paniktür", "Flucht", "Panik"],
    "rauchschutztür": ["Rauchschutz", "RS"],
    "rauchschutztüre": ["Rauchschutz", "RS"],
    "schallschutztür": ["Schallschutz", "dB"],
    "schallschutztüre": ["Schallschutz", "dB"],
    "innentür": ["Innentür", "innen"],
    "innentüre": ["Innentür", "innen"],
    "aussentür": ["Aussentür", "aussen", "Haustür"],
    "aussentüre": ["Aussentür", "aussen", "Haustür"],
    # Brandschutz-Äquivalenzen
    "t30": ["T30", "EI30", "EI230"],
    "t60": ["T60", "EI60", "EI260"],
    "t90": ["T90", "EI90", "EI290"],
    "t120": ["T120", "EI120"],
    "ei30": ["EI30", "T30", "EI230"],
    "ei60": ["EI60", "T60", "EI260"],
    "ei90": ["EI90", "T90", "EI290"],
    "ei120": ["EI120", "T120"],
    "feuerschutz": ["Brand", "Brandschutz", "T30", "T60", "T90"],
    # Einbruchschutz-Äquivalenzen
    "wk2": ["WK2", "RC2"],
    "wk3": ["WK3", "RC3"],
    "wk4": ["WK4", "RC4"],
    "rc2": ["RC2", "WK2"],
    "rc3": ["RC3", "WK3"],
    "rc4": ["RC4", "WK4"],
    "einbruchsicher": ["RC2", "RC3", "WK2", "WK3", "Sicherheit"],
    "einbruchhemmend": ["RC2", "RC3", "WK2", "WK3"],
    # Bauart
    "einflügelig": ["1-flg", "einflügelig", "1-flügelig"],
    "zweiflügelig": ["2-flg", "zweiflügelig", "2-flügelig"],
    "1-flügelig": ["1-flg", "einflügelig"],
    "2-flügelig": ["2-flg", "zweiflügelig"],
    # Oberfläche
    "pulverbeschichtet": ["pulverbeschichtet", "beschichtet", "Pulver"],
    "verzinkt": ["verzinkt", "Zink", "feuerverzinkt"],
    "ral": ["RAL", "Farbe", "lackiert"],
    # Zubehör
    "türdrücker": ["Drücker", "Beschlag"],
    "türschliesser": ["Schliesser", "Türschliesser"],
    "panikstange": ["Panik", "Paniktür", "Panikbeschlag"],
    "obentürschliesser": ["OTS", "Obentürschliesser", "Schliesser"],
}


def expand_synonyms(text: str) -> list[str]:
    """
    Expand text with synonym keywords.
    Returns additional search terms based on domain knowledge.
    """
    if not text:
        return []

    extra_terms = []
    text_lower = text.lower()

    for term, expansions in SYNONYMS.items():
        if term in text_lower:
            extra_terms.extend(expansions)

    return list(set(extra_terms))


# Path to the product Excel file
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
PRODUCT_FILE = os.path.join(DATA_DIR, "produktuebersicht.xlsx")

# TF-IDF cache (lazy-initialized on first use)
_tfidf_vectorizer = None
_tfidf_matrix = None


@lru_cache(maxsize=1)
def load_product_catalog() -> pd.DataFrame:
    """
    Load and cache the FTAG product catalog from Excel.
    Returns a cleaned DataFrame.
    """
    if not os.path.exists(PRODUCT_FILE):
        raise FileNotFoundError(
            f"Product catalog not found at: {PRODUCT_FILE}\n"
            "Please place 'produktuebersicht.xlsx' in the data/ directory."
        )

    # Read Excel - try to find the right sheet
    xl = pd.ExcelFile(PRODUCT_FILE)
    sheet_names = xl.sheet_names

    # Try to read first sheet or find relevant sheet
    df = pd.read_excel(PRODUCT_FILE, sheet_name=0, header=None)

    # Find the header row (look for rows with substantial content)
    header_row = _find_header_row(df)

    if header_row is not None:
        df = pd.read_excel(PRODUCT_FILE, sheet_name=0, header=header_row)
    else:
        df = pd.read_excel(PRODUCT_FILE, sheet_name=0)

    # Clean column names
    df.columns = [str(col).strip() for col in df.columns]

    # Drop completely empty rows/columns
    df = df.dropna(how="all").reset_index(drop=True)

    return df


def _find_header_row(df: pd.DataFrame) -> Optional[int]:
    """Find the row index that looks like a header."""
    for i, row in df.iterrows():
        non_null = row.dropna()
        if len(non_null) > 5:
            # Check if values look like headers (strings, not numbers)
            string_count = sum(1 for v in non_null if isinstance(v, str) and len(v) > 1)
            if string_count > 5:
                return i
    return None


# ─────────────────────────────────────────────
# TF-IDF SEMANTIC SEARCH
# ─────────────────────────────────────────────

def _build_product_text(row, columns) -> str:
    """Combine all product columns into a single text for TF-IDF vectorization."""
    parts = []
    for col in columns:
        val = row.get(col)
        if pd.notna(val) and str(val).strip() not in ("nan", "NaN", ""):
            parts.append(str(val).strip().lower())
    return " ".join(parts)


def _get_tfidf_matrix():
    """
    Build and cache the TF-IDF matrix for all products.
    Called once on first use, then cached for the process lifetime.
    """
    global _tfidf_vectorizer, _tfidf_matrix

    if _tfidf_matrix is not None:
        return _tfidf_vectorizer, _tfidf_matrix

    df = load_product_catalog()

    product_texts = []
    for _, row in df.iterrows():
        product_texts.append(_build_product_text(row, df.columns))

    _tfidf_vectorizer = TfidfVectorizer(
        analyzer="word",
        lowercase=True,
        token_pattern=r"(?u)\b\w[\w\-/]+\b",
        max_features=5000,
        sublinear_tf=True,
        ngram_range=(1, 2),
    )

    _tfidf_matrix = _tfidf_vectorizer.fit_transform(product_texts)
    logger.info(f"TF-IDF matrix built: {_tfidf_matrix.shape[0]} products, {_tfidf_matrix.shape[1]} features")
    return _tfidf_vectorizer, _tfidf_matrix


def tfidf_score_candidates(requirement_text: str, top_n: int = 100) -> list[tuple[int, float]]:
    """
    Score all products against a requirement using TF-IDF cosine similarity.
    Returns list of (row_index, score) tuples, sorted by score descending.
    """
    vectorizer, matrix = _get_tfidf_matrix()
    req_vector = vectorizer.transform([requirement_text.lower()])
    scores = cosine_similarity(req_vector, matrix).flatten()
    top_indices = np.argsort(scores)[::-1][:top_n]
    return [(int(idx), float(scores[idx])) for idx in top_indices if scores[idx] > 0.0]


def invalidate_tfidf_cache():
    """Clear TF-IDF cache (call after product catalog changes)."""
    global _tfidf_vectorizer, _tfidf_matrix
    _tfidf_vectorizer = None
    _tfidf_matrix = None


def get_products_summary() -> list[dict]:
    """
    Return a summary list of all products for the frontend.
    Returns first 200 rows to avoid overwhelming the API.
    """
    df = load_product_catalog()

    products = []
    for _, row in df.head(200).iterrows():
        product = {}
        for col in df.columns[:20]:  # First 20 columns
            val = row.get(col)
            if pd.notna(val) and str(val).strip():
                product[str(col)] = str(val).strip()
        if product:
            products.append(product)

    return products


# ─────────────────────────────────────────────
# AI-POWERED MATCHING (Stage 1 + 2)
# ─────────────────────────────────────────────

def match_requirements_ai(requirements: dict) -> dict:
    """
    AI-enhanced matching: pre-filter + Claude batch matching + feedback loop.
    All positions are matched in a SINGLE Claude API call (batch).
    Falls back to keyword matching on error.
    """
    from services.claude_client import ai_match_products_batch

    df = load_product_catalog()
    positions = requirements.get("positionen", [])

    if not positions:
        return {
            "matched": [], "partial": [], "unmatched": [],
            "summary": {"total_positions": 0, "matched_count": 0,
                        "partial_count": 0, "unmatched_count": 0, "match_rate": 0},
        }

    # Stage 1: Pre-filter candidates for ALL positions
    positions_data = []
    for pos in positions:
        candidates = prefilter_candidates(pos, df, limit=25)
        req_text = _build_requirement_text(pos)
        positions_data.append({
            "req_text": req_text,
            "req_fields": pos,
            "candidates_text": format_candidates_for_claude(df, candidates) if candidates else "",
            "candidate_indices": candidates,
        })

    # Collect feedback once (shared across all positions)
    all_text = " ".join(pd["req_text"] for pd in positions_data)
    feedback_examples = find_relevant_feedback(all_text, {}, limit=8)

    # Stage 2: Batch AI matching (single Claude call)
    try:
        # Only send positions that have candidates to Claude
        batch_indices = [i for i, pd in enumerate(positions_data) if pd["candidate_indices"]]
        batch_data = [positions_data[i] for i in batch_indices]

        if batch_data:
            ai_results = ai_match_products_batch(batch_data, feedback_examples)
        else:
            ai_results = []

        # Map AI results back to positions
        ai_result_map = {}
        for j, bi in enumerate(batch_indices):
            if j < len(ai_results):
                ai_result_map[bi] = ai_results[j]

    except Exception as e:
        logger.warning(f"Batch AI matching failed: {e}")
        ai_result_map = {}

    # Build results
    matched = []
    unmatched = []
    partial = []

    for i, pos in enumerate(positions):
        if i in ai_result_map:
            ai_result = ai_result_map[i]
            match_result = _build_result_from_ai(pos, df, ai_result, positions_data[i]["candidate_indices"])
        elif not positions_data[i]["candidate_indices"]:
            match_result = {
                "status": "unmatched",
                "confidence": 0.0,
                "position": pos.get("position", "?"),
                "beschreibung": pos.get("beschreibung", ""),
                "menge": pos.get("menge", 1),
                "einheit": pos.get("einheit", "Stk"),
                "matched_products": [],
                "reason": "Keine passenden Kandidaten im Katalog gefunden",
                "match_criteria": [],
            }
        else:
            # Fallback to keyword matching
            match_result = _match_single_position(pos, df)

        match_result["original_position"] = pos

        if match_result["status"] == "matched":
            matched.append(match_result)
        elif match_result["status"] == "partial":
            partial.append(match_result)
        else:
            unmatched.append(match_result)

    logger.info(
        f"Batch matching done: {len(matched)} matched, {len(partial)} partial, "
        f"{len(unmatched)} unmatched ({len(batch_indices)} positions in 1 API call)"
    )

    return {
        "matched": matched,
        "partial": partial,
        "unmatched": unmatched,
        "summary": {
            "total_positions": len(positions),
            "matched_count": len(matched),
            "partial_count": len(partial),
            "unmatched_count": len(unmatched),
            "match_rate": round(
                (len(matched) + len(partial) * 0.5) / max(len(positions), 1) * 100, 1
            ),
        },
    }


def _build_result_from_ai(position: dict, df: pd.DataFrame, ai_result: dict, candidate_indices: list) -> dict:
    """Build a match result dict from an AI batch result with confidence threshold enforcement."""
    products = []
    if ai_result.get("best_match_index") is not None:
        products = _extract_matching_products(df, [ai_result["best_match_index"]])
    for alt_idx in ai_result.get("alternative_indices", []):
        alt_products = _extract_matching_products(df, [alt_idx])
        products.extend(alt_products)
    products = products[:3]

    confidence = round(ai_result.get("confidence", 0.0), 2)
    original_status = ai_result.get("status", "unmatched")
    status = original_status
    review_needed = False

    # Confidence threshold enforcement
    if confidence < 0.4 and status in ("matched", "partial"):
        status = "unmatched"
        review_needed = True
    elif confidence < 0.6 and status == "matched":
        status = "partial"
        review_needed = True

    return {
        "status": status,
        "confidence": confidence,
        "position": position.get("position", "?"),
        "beschreibung": position.get("beschreibung", ""),
        "menge": position.get("menge", 1),
        "einheit": position.get("einheit", "Stk"),
        "matched_products": products,
        "reason": ai_result.get("reason", ""),
        "match_criteria": ai_result.get("match_criteria", []),
        "review_needed": review_needed,
        "original_status": original_status if review_needed else None,
    }


def _match_single_position_ai(position: dict, df: pd.DataFrame) -> dict:
    """
    Match a single position using the two-stage AI pipeline:
    Stage 1: Pre-filter to ~25 candidates
    Stage 2: Claude AI semantic matching with feedback learning
    """
    from services.claude_client import ai_match_products

    # Stage 1: Pre-filter
    candidates = prefilter_candidates(position, df, limit=25)

    if not candidates:
        return {
            "status": "unmatched",
            "confidence": 0.0,
            "position": position.get("position", "?"),
            "beschreibung": position.get("beschreibung", ""),
            "menge": position.get("menge", 1),
            "einheit": position.get("einheit", "Stk"),
            "matched_products": [],
            "reason": "Keine passenden Kandidaten im Katalog gefunden",
        }

    # Build requirement text
    req_text = _build_requirement_text(position)

    # Find relevant past corrections
    feedback_examples = find_relevant_feedback(req_text, position, limit=5)

    # Format candidates for Claude
    candidates_text = format_candidates_for_claude(df, candidates)

    # Stage 2: Claude AI matching
    ai_result = ai_match_products(
        requirement_text=req_text,
        requirement_fields=position,
        candidates_text=candidates_text,
        candidate_indices=candidates,
        feedback_examples=feedback_examples,
    )

    # Build result from AI response
    products = []
    if ai_result["best_match_index"] is not None:
        products = _extract_matching_products(df, [ai_result["best_match_index"]])
    for alt_idx in ai_result.get("alternative_indices", []):
        alt_products = _extract_matching_products(df, [alt_idx])
        products.extend(alt_products)
    products = products[:3]

    return {
        "status": ai_result["status"],
        "confidence": round(ai_result["confidence"], 2),
        "position": position.get("position", "?"),
        "beschreibung": position.get("beschreibung", ""),
        "menge": position.get("menge", 1),
        "einheit": position.get("einheit", "Stk"),
        "matched_products": products,
        "reason": ai_result.get("reason", ""),
    }


def prefilter_candidates(position: dict, df: pd.DataFrame, limit: int = 25) -> list[int]:
    """
    Stage 1: Narrow ~891 products to ~25 candidates using keyword/text search.
    Returns list of DataFrame row indices, sorted by relevance score.
    """
    tuertyp = (position.get("tuertyp") or "").lower()
    brandschutz = (position.get("brandschutz") or "").upper()
    einbruchschutz = (position.get("einbruchschutz") or "").upper()
    beschreibung = (position.get("beschreibung") or "").lower()

    df_str = df.astype(str)
    scores = pd.Series(0.0, index=df.index)

    # Expand all fields with synonyms
    all_text = f"{tuertyp} {brandschutz} {einbruchschutz} {beschreibung}"
    synonym_terms = expand_synonyms(all_text)

    # Door type keywords (weight 3)
    if tuertyp:
        type_keywords = _get_type_keywords(tuertyp)
        # Add synonym expansions for door type
        type_keywords.extend(expand_synonyms(tuertyp))
        type_keywords = list(set(type_keywords))
        for col in df_str.columns:
            mask = df_str[col].str.contains(
                "|".join(re.escape(k) for k in type_keywords), case=False, na=False
            )
            scores[mask] += 3

    # Fire protection (weight 3) – with synonym expansion
    if brandschutz and brandschutz != "NONE":
        fire_terms = [brandschutz] + expand_synonyms(brandschutz)
        fire_pattern = "|".join(re.escape(t) for t in set(fire_terms))
        fire_mask = df_str.apply(
            lambda col: col.str.contains(fire_pattern, case=False, na=False)
        ).any(axis=1)
        scores[fire_mask] += 3

    # Burglar resistance (weight 2) – with synonym expansion
    if einbruchschutz and einbruchschutz != "NONE":
        burg_terms = [einbruchschutz] + expand_synonyms(einbruchschutz)
        rc_class = einbruchschutz.replace("WK", "RC")
        wk_class = einbruchschutz.replace("RC", "WK")
        burg_terms.extend([rc_class, wk_class])
        burg_pattern = "|".join(re.escape(t) for t in set(burg_terms))
        burg_mask = df_str.apply(
            lambda col: col.str.contains(burg_pattern, case=False, na=False)
        ).any(axis=1)
        scores[burg_mask] += 2

    # Free-text from description + synonyms (weight 1 per keyword hit)
    desc_search_words = []
    if beschreibung:
        desc_search_words = [w for w in beschreibung.split() if len(w) > 3][:5]
    desc_search_words.extend(synonym_terms[:5])
    for word in desc_search_words:
        if len(word) < 2:
            continue
        word_mask = df_str.apply(
            lambda col: col.str.contains(re.escape(word), case=False, na=False)
        ).any(axis=1)
        scores[word_mask] += 1

    # TF-IDF semantic scoring
    req_text = _build_requirement_text(position)
    tfidf_results = tfidf_score_candidates(req_text, top_n=100)

    tfidf_scores = pd.Series(0.0, index=df.index)
    for idx, score in tfidf_results:
        if idx in tfidf_scores.index:
            tfidf_scores[idx] = score

    # Normalize both to [0, 1] for fair combination
    kw_max = scores.max()
    keyword_norm = scores / kw_max if kw_max > 0 else scores

    tf_max = tfidf_scores.max()
    tfidf_norm = tfidf_scores / tf_max if tf_max > 0 else tfidf_scores

    # Combine: 60% keyword (domain-specific) + 40% TF-IDF (semantic)
    combined = keyword_norm * 0.6 + tfidf_norm * 0.4

    # Take top candidates sorted by combined score
    top_indices = combined.nlargest(limit).index.tolist()
    positive = [i for i in top_indices if combined[i] > 0]
    if len(positive) >= 5:
        return positive[:limit]
    return top_indices[:limit]


def format_candidates_for_claude(df: pd.DataFrame, candidate_indices: list[int]) -> str:
    """Format candidate products as a numbered text block for Claude."""
    lines = []
    for rank, idx in enumerate(candidate_indices, 1):
        if idx >= len(df):
            continue
        row = df.iloc[idx]
        parts = []
        for col in df.columns[:12]:
            val = row.get(col)
            if pd.notna(val) and str(val).strip() not in ("nan", "NaN", ""):
                parts.append(f"{col}: {str(val).strip()}")
        if parts:
            lines.append(f"[{rank}] (Index {idx}) {' | '.join(parts)}")
    return "\n".join(lines)


def _build_requirement_text(position: dict) -> str:
    """Build a human-readable requirement description from structured fields."""
    parts = []
    if position.get("beschreibung"):
        parts.append(position["beschreibung"])
    if position.get("tuertyp"):
        parts.append(f"Typ: {position['tuertyp']}")
    if position.get("brandschutz"):
        parts.append(f"Brandschutz: {position['brandschutz']}")
    if position.get("einbruchschutz"):
        parts.append(f"Einbruchschutz: {position['einbruchschutz']}")
    if position.get("schallschutz"):
        parts.append(f"Schallschutz: {position['schallschutz']}")
    if position.get("breite") and position.get("hoehe"):
        parts.append(f"Masse: {position['breite']}x{position['hoehe']}mm")
    if position.get("oberflaechenbehandlung"):
        parts.append(f"Oberfläche: {position['oberflaechenbehandlung']}")
    if position.get("zubehoer"):
        parts.append(f"Zubehör: {position['zubehoer']}")
    return " | ".join(parts) if parts else "Tür (keine Details)"


# ─────────────────────────────────────────────
# LEGACY KEYWORD MATCHING (Fallback)
# ─────────────────────────────────────────────

def match_requirements(requirements: dict) -> dict:
    """
    Match extracted requirements against the product catalog.
    Legacy keyword-based matching, used as fallback if AI matching fails.
    """
    df = load_product_catalog()
    positions = requirements.get("positionen", [])

    matched = []
    unmatched = []
    partial = []

    for pos in positions:
        match_result = _match_single_position(pos, df)
        match_result["original_position"] = pos

        if match_result["status"] == "matched":
            matched.append(match_result)
        elif match_result["status"] == "partial":
            partial.append(match_result)
        else:
            unmatched.append(match_result)

    return {
        "matched": matched,
        "partial": partial,
        "unmatched": unmatched,
        "summary": {
            "total_positions": len(positions),
            "matched_count": len(matched),
            "partial_count": len(partial),
            "unmatched_count": len(unmatched),
            "match_rate": round(
                (len(matched) + len(partial) * 0.5) / max(len(positions), 1) * 100, 1
            ),
        },
    }


def _match_single_position(position: dict, df: pd.DataFrame) -> dict:
    """
    Match a single position requirement against the product catalog.
    Uses fuzzy matching based on door type, fire protection class, etc.
    """
    tuertyp = (position.get("tuertyp") or "").lower()
    brandschutz = (position.get("brandschutz") or "").upper()
    einbruchschutz = (position.get("einbruchschutz") or "").upper()
    schallschutz = position.get("schallschutz")
    breite = position.get("breite")
    hoehe = position.get("hoehe")

    # Convert dataframe to string for searching
    df_str = df.astype(str)

    matching_rows = []
    score = 0
    max_score = 0

    # Score based on door type
    if tuertyp:
        max_score += 3
        type_keywords = _get_type_keywords(tuertyp)
        for col in df_str.columns:
            col_matches = df_str[col].str.contains(
                "|".join(type_keywords), case=False, na=False
            )
            if col_matches.any():
                score += 3
                matching_rows.extend(df[col_matches].index.tolist())
                break

    # Score based on fire protection
    if brandschutz and brandschutz != "NONE":
        max_score += 3
        # Look for fire class in any column
        fire_match = df_str.apply(
            lambda col: col.str.contains(brandschutz, case=False, na=False)
        ).any(axis=1)
        if fire_match.any():
            score += 3
            matching_rows.extend(df[fire_match].index.tolist())

    # Score based on burglar resistance
    if einbruchschutz and einbruchschutz != "NONE":
        max_score += 2
        # RC and WK are equivalent
        rc_class = einbruchschutz.replace("WK", "RC")
        wk_class = einbruchschutz.replace("RC", "WK")
        burglary_pattern = f"{rc_class}|{wk_class}"
        burglary_match = df_str.apply(
            lambda col: col.str.contains(burglary_pattern, case=False, na=False)
        ).any(axis=1)
        if burglary_match.any():
            score += 2
            matching_rows.extend(df[burglary_match].index.tolist())

    # Determine match status
    unique_matches = list(set(matching_rows))

    if max_score == 0:
        # No specific requirements – assume basic product exists
        status = "matched"
        confidence = 0.7
        products = _get_generic_product(tuertyp)
    elif score >= max_score * 0.7:
        status = "matched"
        confidence = score / max(max_score, 1)
        products = _extract_matching_products(df, unique_matches[:3])
    elif score > 0:
        status = "partial"
        confidence = score / max(max_score, 1)
        products = _extract_matching_products(df, unique_matches[:3])
    else:
        status = "unmatched"
        confidence = 0.0
        products = []

    return {
        "status": status,
        "confidence": round(confidence, 2),
        "position": position.get("position", "?"),
        "beschreibung": position.get("beschreibung", ""),
        "menge": position.get("menge", 1),
        "einheit": position.get("einheit", "Stk"),
        "matched_products": products,
        "reason": _get_match_reason(status, tuertyp, brandschutz, einbruchschutz),
        "match_criteria": [],
    }


def _get_type_keywords(tuertyp: str) -> list[str]:
    """Map door type string to search keywords."""
    keywords = []
    if "stahl" in tuertyp:
        keywords.extend(["Stahl", "ST"])
    if "holz" in tuertyp:
        keywords.extend(["Holz", "HO"])
    if "alu" in tuertyp or "aluminium" in tuertyp:
        keywords.extend(["Alu", "Aluminium"])
    if "brand" in tuertyp or "feuer" in tuertyp:
        keywords.extend(["T30", "T60", "T90", "EI30", "EI60", "EI90", "Brand"])
    if "sicherheit" in tuertyp:
        keywords.extend(["RC", "WK", "Sicherheit"])
    if not keywords:
        keywords = [tuertyp[:4]] if len(tuertyp) >= 4 else [tuertyp]
    return keywords


def _extract_matching_products(df: pd.DataFrame, row_indices: list) -> list[dict]:
    """Extract product info from matching rows."""
    products = []
    seen = set()

    for idx in row_indices:
        if idx >= len(df):
            continue
        row = df.iloc[idx]
        # Get first few columns as product identifier
        product_key = str(row.iloc[0]) if len(row) > 0 else str(idx)
        if product_key in seen or product_key in ("nan", "NaN", ""):
            continue
        seen.add(product_key)

        product = {}
        for col in df.columns[:10]:
            val = row.get(col)
            if pd.notna(val) and str(val).strip() not in ("nan", "NaN", ""):
                product[str(col)] = str(val).strip()

        if product:
            products.append(product)

    return products[:3]  # Max 3 matching products


def _get_generic_product(tuertyp: str) -> list[dict]:
    """Return a generic product placeholder when specific match not found."""
    return [
        {
            "bezeichnung": f"Standard {tuertyp.title() if tuertyp else 'Tür'}",
            "hinweis": "Standardprodukt aus FTAG-Sortiment – genaue Spezifikation bei Auftragserteilung",
        }
    ]


def _get_match_reason(status: str, tuertyp: str, brandschutz: str, einbruchschutz: str) -> str:
    """Generate human-readable match reason."""
    if status == "matched":
        return "Produkt im FTAG-Sortiment verfügbar"
    elif status == "partial":
        return "Teilweise erfüllbar – Rückfrage zu spezifischen Anforderungen empfohlen"
    else:
        specs = []
        if brandschutz:
            specs.append(f"Brandschutzklasse {brandschutz}")
        if einbruchschutz:
            specs.append(f"Einbruchschutz {einbruchschutz}")
        if tuertyp:
            specs.append(f"Türtyp {tuertyp}")
        spec_str = ", ".join(specs) if specs else "Spezifikation"
        return f"Kein exaktes Produkt für {spec_str} gefunden – Sonderanfertigung prüfen"
