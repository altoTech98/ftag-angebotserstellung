"""
V2 Analyze Router - Analysis trigger endpoint with file sorting.

Validates tender session, sorts files by format priority (xlsx > pdf > docx),
and returns a stub extraction result. The real pipeline will be connected in Plan 03.
"""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from v2.parsers.base import ParseResult
from v2.routers.upload_v2 import _tenders

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2", tags=["V2 Analysis"])

# Format priority for sorting: lower number = higher priority
_FORMAT_PRIORITY = {
    "xlsx": 0,
    "xls": 0,
    "pdf": 1,
    "docx": 2,
    "txt": 3,
    "unknown": 9,
}


class AnalyzeRequest(BaseModel):
    """Request body for analyze endpoint."""
    tender_id: str


def _sort_parse_results(files: list[ParseResult]) -> list[ParseResult]:
    """Sort parsed files by format priority: xlsx > pdf > docx.

    Args:
        files: List of ParseResult objects from uploaded files.

    Returns:
        Sorted list with XLSX first, then PDF, then DOCX.
    """
    return sorted(files, key=lambda r: _FORMAT_PRIORITY.get(r.format, 9))


@router.post("/analyze")
async def analyze_tender(request: AnalyzeRequest):
    """Trigger analysis on an uploaded tender.

    Validates tender exists and has files. Sorts files by format priority.
    Currently returns a stub response; the real extraction pipeline
    will be wired in Plan 03.

    Args:
        request: JSON body with tender_id.

    Returns:
        JSON with tender_id, status, positionen (empty stub), warnungen,
        and sorted_files metadata.
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

    # Sort files by format priority (xlsx > pdf > docx)
    sorted_files = _sort_parse_results(files)

    logger.info(
        f"[V2 Analyze] Tender {tender_id}: {len(sorted_files)} files, "
        f"order: {[f.format for f in sorted_files]}"
    )

    # Update tender status
    tender["status"] = "analyzed"

    # Stub response - real pipeline in Plan 03
    return {
        "tender_id": tender_id,
        "status": "completed",
        "positionen": [],
        "warnungen": ["Pipeline not yet connected"],
        "sorted_files": [
            {
                "filename": r.source_file,
                "format": r.format,
                "page_count": r.page_count,
            }
            for r in sorted_files
        ],
    }
