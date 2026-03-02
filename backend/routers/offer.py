"""
Offer Router – Offer generation and download endpoints.
POST /api/offer/generate
GET  /api/offer/{id}/download
GET  /api/report/{id}/download
"""

import os
import uuid
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from services.claude_client import generate_offer_text, generate_gap_report_text
from services.offer_generator import (
    generate_offer_excel, generate_gap_report_excel,
    generate_offer_word, generate_gap_report_word,
)

router = APIRouter()

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "outputs")


class GenerateOfferRequest(BaseModel):
    requirements: dict
    matching: dict


@router.post("/offer/generate")
async def generate_offer(request: GenerateOfferRequest):
    """
    Generate an offer and/or gap report based on analysis results.
    Returns offer_id and report_id for downloading.
    """
    requirements = request.requirements
    matching = request.matching

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
        try:
            offer_text = generate_offer_text(requirements, offer_positions, project_info)
        except ValueError as e:
            raise HTTPException(status_code=503, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Angebotserstellung fehlgeschlagen: {str(e)}",
            )

        generate_offer_excel(offer_text, offer_positions, requirements, offer_id)
        generate_offer_word(offer_text, offer_positions, requirements, offer_id)
        results["offer_id"] = offer_id
        results["has_offer"] = True
        results["offer_positions_count"] = len(offer_positions)

    # Generate gap report if there are unmatched/partial positions
    gap_positions = unmatched + partial
    if gap_positions:
        try:
            gap_text = generate_gap_report_text(requirements, unmatched, project_info)
        except ValueError as e:
            raise HTTPException(status_code=503, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Gap-Report Erstellung fehlgeschlagen: {str(e)}",
            )

        generate_gap_report_excel(gap_text, unmatched, partial, requirements, report_id)
        generate_gap_report_word(gap_text, unmatched, partial, requirements, report_id)
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
    """Download offer as Excel (format=xlsx) or Word (format=docx)."""
    if format == "docx":
        file_path = os.path.join(OUTPUT_DIR, f"angebot_{offer_id}.docx")
        media = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        fname = f"FTAG_Angebot_{offer_id}.docx"
    else:
        file_path = os.path.join(OUTPUT_DIR, f"angebot_{offer_id}.xlsx")
        media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        fname = f"FTAG_Angebot_{offer_id}.xlsx"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Angebot '{offer_id}' nicht gefunden")
    return FileResponse(file_path, media_type=media, filename=fname)


@router.get("/report/{report_id}/download")
async def download_gap_report(report_id: str, format: str = "xlsx"):
    """Download gap report as Excel (format=xlsx) or Word (format=docx)."""
    if format == "docx":
        file_path = os.path.join(OUTPUT_DIR, f"gap_report_{report_id}.docx")
        media = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        fname = f"FTAG_Gap_Report_{report_id}.docx"
    else:
        file_path = os.path.join(OUTPUT_DIR, f"gap_report_{report_id}.xlsx")
        media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        fname = f"FTAG_Gap_Report_{report_id}.xlsx"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Gap-Report '{report_id}' nicht gefunden")
    return FileResponse(file_path, media_type=media, filename=fname)
