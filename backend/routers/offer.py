"""
Offer Router – Offer generation and download endpoints (in-memory, no disk writes).
POST /api/offer/generate       – Start offer generation (background job)
GET  /api/offer/status/{job_id} – Poll job status
GET  /api/offer/{id}/download
GET  /api/report/{id}/download
"""

import uuid
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from services.claude_client import generate_offer_text, generate_gap_report_text
from services.offer_generator import (
    generate_offer_excel, generate_gap_report_excel,
    generate_offer_word, generate_gap_report_word,
)
from services.memory_cache import offer_cache
from services.job_store import create_job, get_job, update_job, run_in_background

logger = logging.getLogger(__name__)

router = APIRouter()


class GenerateOfferRequest(BaseModel):
    requirements: dict
    matching: dict


@router.post("/offer/generate")
async def generate_offer(request: GenerateOfferRequest):
    """Start offer generation as background job. Returns job_id immediately."""
    job = create_job()
    run_in_background(
        job, _run_offer_generation,
        request.requirements, request.matching,
    )
    return {"job_id": job.id, "status": "started"}


@router.get("/offer/status/{job_id}")
async def get_offer_status(job_id: str):
    """Poll the status of an offer generation job."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job nicht gefunden")
    return job.to_dict()


def _run_offer_generation(requirements: dict, matching: dict) -> dict:
    """Run offer + gap report generation in background thread."""
    matched = matching.get("matched", [])
    partial = matching.get("partial", [])
    unmatched = matching.get("unmatched", [])

    offer_id = str(uuid.uuid4())[:8]
    report_id = str(uuid.uuid4())[:8]

    project_info = {
        "projekt": requirements.get("projekt", "Ausschreibung"),
        "auftraggeber": requirements.get("auftraggeber", ""),
        "hinweise": requirements.get("hinweise", ""),
    }

    results = {
        "offer_id": None,
        "report_id": None,
        "has_offer": False,
        "has_gap_report": False,
        "summary": matching.get("summary", {}),
    }

    # Generate offer if there are matched/partial positions
    offer_positions = matched + partial
    if offer_positions:
        offer_text = generate_offer_text(requirements, offer_positions, project_info)

        xlsx_bytes = generate_offer_excel(offer_text, offer_positions, requirements, offer_id)
        docx_bytes = generate_offer_word(offer_text, offer_positions, requirements, offer_id)

        offer_cache.store(f"offer_{offer_id}_xlsx", xlsx_bytes, ttl_seconds=1800)
        offer_cache.store(f"offer_{offer_id}_docx", docx_bytes, ttl_seconds=1800)

        results["offer_id"] = offer_id
        results["has_offer"] = True
        results["offer_positions_count"] = len(offer_positions)

    # Generate gap report if there are unmatched/partial positions
    gap_positions = unmatched + partial
    if gap_positions:
        gap_text = generate_gap_report_text(requirements, unmatched, project_info)

        xlsx_bytes = generate_gap_report_excel(gap_text, unmatched, partial, requirements, report_id)
        docx_bytes = generate_gap_report_word(gap_text, unmatched, partial, requirements, report_id)

        offer_cache.store(f"report_{report_id}_xlsx", xlsx_bytes, ttl_seconds=1800)
        offer_cache.store(f"report_{report_id}_docx", docx_bytes, ttl_seconds=1800)

        results["report_id"] = report_id
        results["has_gap_report"] = True
        results["gap_positions_count"] = len(gap_positions)

    # Build status message
    msgs = []
    if results["has_offer"]:
        msgs.append(f"Angebot erstellt ({results.get('offer_positions_count', 0)} Positionen)")
    if results["has_gap_report"]:
        msgs.append(f"Gap-Report erstellt ({results.get('gap_positions_count', 0)} Positionen)")
    if not msgs:
        msgs.append("Keine Positionen zum Verarbeiten")

    results["message"] = " · ".join(msgs)
    return results


@router.get("/offer/{offer_id}/download")
async def download_offer(offer_id: str, format: str = "xlsx"):
    """Download offer as Excel (format=xlsx) or Word (format=docx) from memory cache."""
    key = f"offer_{offer_id}_{format}"
    data = offer_cache.get(key)
    if data is None:
        raise HTTPException(
            status_code=410,
            detail="Angebot nicht gefunden oder abgelaufen. Bitte erneut generieren.",
        )

    if format == "docx":
        media = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        fname = f"FTAG_Angebot_{offer_id}.docx"
    else:
        media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        fname = f"FTAG_Angebot_{offer_id}.xlsx"

    return Response(
        content=data,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


@router.get("/report/{report_id}/download")
async def download_gap_report(report_id: str, format: str = "xlsx"):
    """Download gap report as Excel (format=xlsx) or Word (format=docx) from memory cache."""
    key = f"report_{report_id}_{format}"
    data = offer_cache.get(key)
    if data is None:
        raise HTTPException(
            status_code=410,
            detail="Gap-Report nicht gefunden oder abgelaufen. Bitte erneut generieren.",
        )

    if format == "docx":
        media = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        fname = f"FTAG_Gap_Report_{report_id}.docx"
    else:
        media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        fname = f"FTAG_Gap_Report_{report_id}.xlsx"

    return Response(
        content=data,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )
