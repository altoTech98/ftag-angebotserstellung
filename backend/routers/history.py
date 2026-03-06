"""
History Router – Browse and manage past analyses.
GET    /api/history         - list all analyses (summary)
GET    /api/history/{id}    - full analysis details
POST   /api/history/{id}/rematch - re-run matching on stored requirements
DELETE /api/history/{id}    - delete entry
"""

import logging
from fastapi import APIRouter, HTTPException

from config import settings
from services.history_store import (
    get_history_list,
    get_history_detail,
    delete_history_entry,
    save_analysis,
)
from services.fast_matcher import match_all
from services.product_matcher import match_requirements

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/history")
async def list_history():
    """Return summary list of all past analyses."""
    return {"analyses": get_history_list()}


@router.get("/history/{history_id}")
async def get_history(history_id: str):
    """Return full details of a past analysis."""
    entry = get_history_detail(history_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Analyse '{history_id}' nicht gefunden")
    return entry


@router.post("/history/{history_id}/rematch")
async def rematch_history(history_id: str):
    """
    Re-run product matching on a stored analysis using current feedback/synonyms/TF-IDF.
    Does NOT re-extract requirements from the document.
    """
    entry = get_history_detail(history_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Analyse '{history_id}' nicht gefunden")

    requirements = entry.get("requirements", {})
    if not requirements.get("positionen"):
        raise HTTPException(status_code=400, detail="Keine Positionen in der gespeicherten Analyse")

    try:
        positionen = requirements.get("positionen", [])
        match_result = match_all(positionen)
    except Exception as e:
        logger.warning(f"Fast rematch failed, falling back to keyword: {e}")
        try:
            match_result = match_requirements(requirements)
        except Exception as e2:
            raise HTTPException(status_code=500, detail=str(e2) if settings.DEBUG else "Rematch fehlgeschlagen")

    # Save as new history entry
    new_entry = save_analysis(
        file_id=entry.get("file_id", "rematch"),
        filename=f"Rematch: {entry.get('filename', '?')}",
        requirements=requirements,
        matching=match_result,
    )

    return {
        "status": "rematched",
        "new_history_id": new_entry["id"],
        "original_history_id": history_id,
        "requirements": requirements,
        "matching": match_result,
        "message": (
            f"Rematch abgeschlossen: {match_result['summary']['matched_count']} erfüllbar, "
            f"{match_result['summary']['unmatched_count']} nicht erfüllbar"
        ),
    }


@router.delete("/history/{history_id}")
async def delete_history(history_id: str):
    """Delete a history entry."""
    deleted = delete_history_entry(history_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Analyse '{history_id}' nicht gefunden")
    return {"status": "deleted", "id": history_id}
