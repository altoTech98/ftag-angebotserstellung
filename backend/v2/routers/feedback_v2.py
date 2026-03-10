"""
V2 Feedback Router - API endpoint for saving matching corrections.

POST /api/v2/feedback saves a correction with position, original match,
corrected match, and reason. Used for few-shot learning in AI matching.
"""

import logging

from fastapi import APIRouter
from pydantic import BaseModel

from v2.matching.feedback_v2 import FeedbackEntry, get_feedback_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2", tags=["V2 Feedback"])


class FeedbackRequest(BaseModel):
    """Request body for saving a matching correction."""

    positions_nr: str
    requirement_summary: str
    original_produkt_id: str
    original_konfidenz: float
    corrected_produkt_id: str
    corrected_produkt_name: str
    correction_reason: str


@router.post("/feedback")
async def save_feedback(request: FeedbackRequest):
    """Save a matching correction for future few-shot learning.

    Creates a FeedbackEntry from the request and persists it
    in the V2 feedback store.

    Returns:
        JSON with status and feedback_id.
    """
    entry = FeedbackEntry(
        positions_nr=request.positions_nr,
        requirement_summary=request.requirement_summary,
        original_match={
            "produkt_id": request.original_produkt_id,
            "gesamt_konfidenz": request.original_konfidenz,
        },
        corrected_match={
            "produkt_id": request.corrected_produkt_id,
            "produkt_name": request.corrected_produkt_name,
        },
        correction_reason=request.correction_reason,
    )

    store = get_feedback_store()
    saved = store.save_correction(entry)

    logger.info(
        f"[V2 Feedback] Saved correction {saved.id} for position {saved.positions_nr}"
    )

    return {"status": "saved", "feedback_id": saved.id}
