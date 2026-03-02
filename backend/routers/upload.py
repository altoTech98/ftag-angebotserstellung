"""
Upload Router – Handles file upload and initial parsing.
POST /api/upload
"""

import os
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse

from services.document_parser import parse_document

router = APIRouter()

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "uploads")
ALLOWED_EXTENSIONS = {".pdf", ".xlsx", ".xls", ".docx", ".doc", ".txt"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


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
