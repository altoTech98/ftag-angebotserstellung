"""
V2 Analyze Router - Analysis trigger endpoint with full extraction pipeline.

Validates tender session, runs the 3-pass extraction pipeline,
and returns structured ExtractionResult with all door positions.
"""

import logging
import traceback

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from v2.extraction.pipeline import run_extraction_pipeline
from v2.parsers.base import ParseResult
from v2.routers.upload_v2 import _tenders

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2", tags=["V2 Analysis"])


class AnalyzeRequest(BaseModel):
    """Request body for analyze endpoint."""
    tender_id: str


@router.post("/analyze")
async def analyze_tender(request: AnalyzeRequest):
    """Trigger full 3-pass extraction pipeline on an uploaded tender.

    Validates tender exists and has files. Runs Pass 1 (structural),
    Pass 2 (semantic AI), and Pass 3 (validation) via the pipeline
    orchestrator. Returns structured extraction results.

    Args:
        request: JSON body with tender_id.

    Returns:
        JSON with tender_id, status, positionen, zusammenfassung,
        warnungen, and total_positionen.
    """
    tender_id = request.tender_id

    if tender_id not in _tenders:
        raise HTTPException(
            status_code=404,
            detail=f"Tender {tender_id} not found",
        )

    tender = _tenders[tender_id]
    files = tender["files"]

    if len(files) == 0:
        raise HTTPException(
            status_code=400,
            detail="Tender has no uploaded files",
        )

    # Extract ParseResult objects from tender files
    parse_results = [f for f in files if isinstance(f, ParseResult)]

    logger.info(
        f"[V2 Analyze] Tender {tender_id}: {len(parse_results)} files, "
        f"formats: {[f.format for f in parse_results]}"
    )

    # Update tender status to analyzing
    tender["status"] = "analyzing"

    try:
        result = await run_extraction_pipeline(parse_results, tender_id)

        # Update tender status to completed
        tender["status"] = "completed"

        response = {
            "tender_id": tender_id,
            "status": "completed",
            "positionen": [pos.model_dump() for pos in result.positionen],
            "zusammenfassung": result.dokument_zusammenfassung,
            "warnungen": result.warnungen,
            "total_positionen": len(result.positionen),
            "enrichment_report": (
                result.enrichment_report.model_dump()
                if result.enrichment_report
                else None
            ),
            "conflicts": [c.model_dump() for c in result.conflicts],
            "total_conflicts": len(result.conflicts),
        }

        return response

    except Exception as e:
        logger.error(
            f"[V2 Analyze] Pipeline failed for tender {tender_id}: {e}\n"
            f"{traceback.format_exc()}"
        )
        tender["status"] = "error"
        raise HTTPException(
            status_code=500,
            detail=f"Extraction pipeline failed: {str(e)}",
        )
