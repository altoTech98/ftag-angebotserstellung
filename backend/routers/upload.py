"""
Upload Router – Handles file upload and initial parsing.
POST /api/upload         – Single file upload (legacy)
POST /api/upload/folder  – Multi-file / folder upload with classification
"""

import os
import uuid
import logging
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse

from services.document_parser import parse_document
from services.file_classifier import classify_file
from services.project_store import create_project

logger = logging.getLogger(__name__)

router = APIRouter()

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "uploads")
ALLOWED_EXTENSIONS = {".pdf", ".xlsx", ".xls", ".docx", ".doc", ".txt"}
FOLDER_ALLOWED_EXTENSIONS = {
    ".pdf", ".xlsx", ".xls", ".xlsm", ".docx", ".doc", ".docm", ".txt",
    ".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff",
    ".dwg", ".dxf", ".crbx",
}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
MAX_TOTAL_SIZE = 500 * 1024 * 1024  # 500 MB for folder uploads


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    Upload an Ausschreibung (tender) document.
    Accepts: PDF, Excel, Word, TXT
    Returns: file_id and extracted text preview
    """
    # Validate file extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Dateityp '{ext}' nicht unterstützt. Erlaubt: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Save file
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_id = str(uuid.uuid4())
    safe_filename = f"{file_id}{ext}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Datei zu groß (max. 50 MB)")

    with open(file_path, "wb") as f:
        f.write(content)

    # Parse document to text
    try:
        text = parse_document(file_path)
    except Exception as e:
        os.remove(file_path)
        raise HTTPException(
            status_code=422,
            detail=f"Dokument konnte nicht gelesen werden: {str(e)}",
        )

    # Return file info + text preview
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
    Creates a project, saves files, classifies each one.
    """
    logger.info(f"Folder upload: {len(files)} files received")
    if not files:
        raise HTTPException(status_code=400, detail="Keine Dateien hochgeladen")

    project_id = str(uuid.uuid4())[:12]
    project_dir = os.path.join(UPLOAD_DIR, project_id)
    os.makedirs(project_dir, exist_ok=True)

    total_size = 0
    file_entries = []

    for uploaded_file in files:
        ext = os.path.splitext(uploaded_file.filename)[1].lower()

        # Skip unsupported extensions silently
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

        # Save file with UUID prefix to avoid name collisions
        file_id = str(uuid.uuid4())[:8]
        # Keep original filename for classification (strip path separators)
        safe_name = uploaded_file.filename.replace("/", "_").replace("\\", "_")
        save_name = f"{file_id}_{safe_name}"
        file_path = os.path.join(project_dir, save_name)

        with open(file_path, "wb") as f:
            f.write(content)

        # Classify the file
        try:
            classification = classify_file(safe_name, file_path)
        except Exception as e:
            logger.warning(f"Classification failed for {safe_name}: {e}")
            classification = {
                "category": "sonstig",
                "confidence": 0.0,
                "reason": f"Klassifikation fehlgeschlagen: {str(e)}",
                "parseable": False,
            }

        file_entries.append({
            "file_id": file_id,
            "filename": safe_name,
            "file_path": file_path,
            "size": file_size,
            **classification,
        })

    if not file_entries:
        raise HTTPException(
            status_code=400,
            detail="Keine unterstützten Dateien im Upload gefunden",
        )

    # Create project in store with our pre-generated ID
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
