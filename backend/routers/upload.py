"""
Upload Router – Handles file upload and initial parsing (in-memory, no disk writes).
POST /api/upload         – Single file upload
POST /api/upload/folder  – Multi-file / folder upload with classification
"""

import os
import uuid
import logging
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException

from services.document_parser import parse_document_bytes
from services.file_classifier import classify_file
from services.project_store import create_project
from services.memory_cache import text_cache, project_cache

logger = logging.getLogger(__name__)

router = APIRouter()

ALLOWED_EXTENSIONS = {".pdf", ".xlsx", ".xls", ".docx", ".doc", ".txt"}
FOLDER_ALLOWED_EXTENSIONS = {
    ".pdf", ".xlsx", ".xls", ".xlsm", ".docx", ".doc", ".docm", ".txt",
    ".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff",
    ".dwg", ".dxf", ".crbx",
}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB per file
MAX_TOTAL_SIZE = 500 * 1024 * 1024  # 500 MB for folder uploads


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    Upload an Ausschreibung (tender) document.
    Accepts: PDF, Excel, Word, TXT
    Parses in-memory, stores only extracted text in cache.
    """
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Dateityp '{ext}' nicht unterstützt. Erlaubt: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Datei zu groß (max. 50 MB)")

    file_id = str(uuid.uuid4())

    # Parse document in memory – no disk write
    try:
        text = parse_document_bytes(content, ext)
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=f"Dokument konnte nicht gelesen werden: {str(e)}",
        )

    # Store extracted text in memory cache
    text_cache.store(file_id, text, filename=file.filename, extension=ext)

    # Also store raw bytes for Excel files (for structured parsing in analyze)
    if ext in (".xlsx", ".xls", ".xlsm"):
        from services.memory_cache import project_cache
        project_cache.store(f"excel_{file_id}", content, filename=file.filename)

    return {
        "file_id": file_id,
        "filename": file.filename,
        "file_type": ext,
        "text_length": len(text),
        "text_preview": text[:500] + ("..." if len(text) > 500 else ""),
        "status": "uploaded",
        "message": f"Datei '{file.filename}' erfolgreich hochgeladen und gelesen ({len(text)} Zeichen)",
    }


@router.post("/upload/folder")
async def upload_folder(files: List[UploadFile] = File(...)):
    """
    Upload multiple files (folder upload or multi-select).
    Creates a project, classifies each file in-memory.
    Parseable file bytes are cached for later analysis.
    """
    logger.info(f"Folder upload: {len(files)} files received")
    if not files:
        raise HTTPException(status_code=400, detail="Keine Dateien hochgeladen")

    project_id = str(uuid.uuid4())[:12]
    total_size = 0
    file_entries = []
    file_bytes_map = {}  # file_id -> bytes (for parseable files only)

    for uploaded_file in files:
        ext = os.path.splitext(uploaded_file.filename)[1].lower()

        if ext not in FOLDER_ALLOWED_EXTENSIONS:
            logger.info(f"Skipping unsupported file: {uploaded_file.filename}")
            continue

        content = await uploaded_file.read()
        file_size = len(content)
        total_size += file_size

        if total_size > MAX_TOTAL_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"Gesamtgrösse überschreitet {MAX_TOTAL_SIZE // (1024*1024)} MB",
            )

        file_id = str(uuid.uuid4())[:8]
        safe_name = uploaded_file.filename.replace("/", "_").replace("\\", "_")

        # Classify file using bytes (no disk)
        try:
            classification = classify_file(safe_name, content=content)
        except Exception as e:
            logger.warning(f"Classification failed for {safe_name}: {e}")
            classification = {
                "category": "sonstig",
                "confidence": 0.0,
                "reason": f"Klassifikation fehlgeschlagen: {str(e)}",
                "parseable": False,
            }

        # Keep bytes for parseable files (needed during analysis)
        if classification["parseable"]:
            file_bytes_map[file_id] = content

        file_entries.append({
            "file_id": file_id,
            "filename": safe_name,
            "size": file_size,
            "extension": ext,
            **classification,
        })

    if not file_entries:
        raise HTTPException(
            status_code=400,
            detail="Keine unterstützten Dateien im Upload gefunden",
        )

    # Cache file bytes for analysis phase
    if file_bytes_map:
        project_cache.store(f"project_{project_id}", file_bytes_map)

    # Create project in store (metadata only, no file_path)
    project = create_project(file_entries, project_id=project_id)

    return {
        "project_id": project_id,
        "total_files": len(file_entries),
        "files": [
            {
                "file_id": f["file_id"],
                "filename": f["filename"],
                "category": f["category"],
                "confidence": f["confidence"],
                "reason": f["reason"],
                "parseable": f["parseable"],
                "size": f["size"],
            }
            for f in file_entries
        ],
        "summary": project["summary"],
        "status": "classified",
        "message": f"{len(file_entries)} Dateien hochgeladen und klassifiziert",
    }
