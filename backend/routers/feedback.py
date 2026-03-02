"""
Feedback Router – Save/retrieve user corrections for product matching.
POST /api/feedback
GET  /api/feedback/stats
GET  /api/products/search
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

import pandas as pd

from services.feedback_store import save_feedback_entry, get_feedback_stats
from services.product_matcher import load_product_catalog

router = APIRouter()


class FeedbackRequest(BaseModel):
    requirement_text: str
    requirement_fields: dict
    wrong_product: dict
    correct_product: dict
    position_id: str
    match_status_was: str
    user_note: Optional[str] = ""


@router.post("/feedback")
async def submit_feedback(request: FeedbackRequest):
    """Save a user correction for product matching."""
    entry = save_feedback_entry(request.model_dump())
    return {
        "status": "saved",
        "feedback_id": entry["id"],
        "message": "Korrektur gespeichert – wird bei zukünftigen Matches berücksichtigt.",
    }


@router.get("/feedback/stats")
async def feedback_stats():
    """Return feedback statistics."""
    return get_feedback_stats()


@router.get("/products/search")
async def search_products(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(20, ge=1, le=50),
):
    """
    Enhanced product search for the correction modal.
    Searches all columns, returns results with row index.
    """
    try:
        df = load_product_catalog()
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))

    df_str = df.astype(str)
    search_lower = q.lower()

    # Score each row by how many columns contain the search term
    scores = df_str.apply(
        lambda col: col.str.contains(search_lower, case=False, na=False)
    ).sum(axis=1)

    # Get top results with positive score
    top_indices = scores.nlargest(limit)
    top_indices = top_indices[top_indices > 0]

    results = []
    for idx in top_indices.index:
        row = df.iloc[idx]
        product = {"_row_index": int(idx)}
        for col in df.columns[:12]:
            val = row.get(col)
            if pd.notna(val) and str(val).strip() not in ("nan", "NaN", ""):
                product[str(col)] = str(val).strip()
        # Build summary string for display
        summary_parts = [
            str(row.iloc[c])
            for c in range(min(4, len(df.columns)))
            if pd.notna(row.iloc[c]) and str(row.iloc[c]).strip() not in ("nan", "")
        ]
        product["_summary"] = " | ".join(summary_parts)
        results.append(product)

    return {
        "query": q,
        "total_results": len(results),
        "products": results,
    }
