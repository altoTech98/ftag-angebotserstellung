"""
V2 Upload Router - Multi-file upload with tender_id session management.

Accepts multiple files per upload, groups them under a tender_id,
and parses each file immediately using Phase 1 parsers.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, File, HTTPException, UploadFile

from v2.parsers.base import ParseResult
from v2.parsers.router import parse_document

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2", tags=["V2 Upload"])

# In-memory tender storage.
# Maps tender_id -> {"files": [ParseResult, ...], "status": str, "created_at": datetime}
_tenders: dict[str, dict] = {}


@router.post("/upload")
async def upload_files(
    files: list[UploadFile] = File(...),
    tender_id: Optional[str] = None,
):
    """Upload one or more files, grouped under a tender session.

    Args:
        files: One or more files to upload.
        tender_id: Optional existing tender_id to append files to.
            If not provided, a new tender session is created.

    Returns:
        JSON with tender_id, per-file metadata, and total file count.
    """
    # Validate or create tender_id
    if tender_id is not None:
        if tender_id not in _tenders:
            raise HTTPException(
                status_code=404,
                detail=f"Tender {tender_id} not found",
            )
    else:
        tender_id = str(uuid.uuid4())
        _tenders[tender_id] = {
            "files": [],
            "status": "uploading",
            "created_at": datetime.now(timezone.utc),
        }

    # Parse each uploaded file immediately
    new_file_metadata = []
    for upload_file in files:
        content = await upload_file.read()
        filename = upload_file.filename or "unknown"

        logger.info(f"[V2 Upload] Parsing {filename} ({len(content)} bytes) for tender {tender_id}")
        result: ParseResult = parse_document(content, filename)

        # Store result in tender
        _tenders[tender_id]["files"].append(result)

        new_file_metadata.append({
            "filename": filename,
            "format": result.format,
            "page_count": result.page_count,
            "warnings": result.warnings,
        })

    total_files = len(_tenders[tender_id]["files"])
    logger.info(f"[V2 Upload] Tender {tender_id}: {total_files} files total")

    return {
        "tender_id": tender_id,
        "files": new_file_metadata,
        "total_files": total_files,
    }


@router.post("/upload/single")
async def upload_single_file(file: UploadFile = File(...)):
    """Upload a single file as a new tender session.

    Args:
        file: The file to upload.

    Returns:
        JSON with tender_id, filename, format, and total_files=1.
    """
    tender_id = str(uuid.uuid4())
    _tenders[tender_id] = {
        "files": [],
        "status": "uploading",
        "created_at": datetime.now(timezone.utc),
    }

    content = await file.read()
    filename = file.filename or "unknown"

    logger.info(f"[V2 Upload] Parsing single file {filename} ({len(content)} bytes) for tender {tender_id}")
    result: ParseResult = parse_document(content, filename)

    _tenders[tender_id]["files"].append(result)

    return {
        "tender_id": tender_id,
        "filename": filename,
        "format": result.format,
        "total_files": 1,
    }


@router.get("/tender/{tender_id}")
async def get_tender_status(tender_id: str):
    """Get tender session status and file list.

    Args:
        tender_id: The tender session ID.

    Returns:
        JSON with tender_id, status, file list, and timestamps.
    """
    if tender_id not in _tenders:
        raise HTTPException(
            status_code=404,
            detail=f"Tender {tender_id} not found",
        )

    tender = _tenders[tender_id]
    files_info = [
        {
            "filename": r.source_file,
            "format": r.format,
            "page_count": r.page_count,
            "warnings": r.warnings,
        }
        for r in tender["files"]
    ]

    return {
        "tender_id": tender_id,
        "status": tender["status"],
        "files": files_info,
        "total_files": len(tender["files"]),
        "created_at": tender["created_at"].isoformat(),
    }
