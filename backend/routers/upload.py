"""
Production-Grade Upload Router with Robust Error Handling.
POST /api/upload           – Single file upload
POST /api/upload/folder    – Multi-file upload
GET  /api/upload/health    – Upload service health check
"""

import os
import uuid
import logging
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel

from config import settings
from services.exceptions import (
    FrankTuerenError,
    FileUploadError,
    FileParsingError,
    ValidationError,
    log_exception,
)
from services.validators import Validator
from services.document_parser import parse_document_bytes
from services.file_classifier import classify_file
from services.memory_cache import text_cache, project_cache

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Upload"])


# ─────────────────────────────────────────────────────────────────────────────
# PYDANTIC MODELS
# ─────────────────────────────────────────────────────────────────────────────

class FileMetadata(BaseModel):
    """File metadata response."""
    file_id: str
    filename: str
    size: int
    extension: str
    category: str
    confidence: float
    parseable: bool
    reason: str = ""


class UploadResponse(BaseModel):
    """Single file upload response."""
    file_id: str
    filename: str
    file_type: str
    text_length: int
    text_preview: str
    status: str


class FolderUploadResponse(BaseModel):
    """Multi-file upload response."""
    project_id: str
    total_files: int
    files: List[FileMetadata]
    summary: dict


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _get_file_extension(filename: str) -> str:
    """Extract and validate file extension."""
    if not filename or '.' not in filename:
        raise ValidationError(
            "Dateiname muss eine Extension haben",
            details={"filename": filename},
        )
    
    _, ext = os.path.splitext(filename)
    ext = ext.lower()
    
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise ValidationError(
            f"Dateityp '{ext}' nicht unterstützt",
            details={"extension": ext},
        )
    
    return ext


def _sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage and display."""
    return Validator.sanitize_filename(filename)


def _validate_file_content(content: bytes, filename: str) -> int:
    """Validate file content and return size."""
    if not content:
        raise FileUploadError("Datei ist leer")
    
    size = len(content)
    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    
    if size > max_bytes:
        raise FileUploadError(
            f"Datei zu groß ({size / 1024 / 1024:.1f}MB > {settings.MAX_FILE_SIZE_MB}MB)",
            details={"size_mb": size / 1024 / 1024, "max_mb": settings.MAX_FILE_SIZE_MB},
        )
    
    return size


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/upload", response_model=UploadResponse)
async def upload_single_file(file: UploadFile = File(...)) -> dict:
    """
    Upload and parse a single document file.
    
    Supported formats: PDF, Excel, Word, Text, Images, CAD
    
    Returns:
        - file_id: UUID for referencing the file
        - text_length: Characters extracted
        - text_preview: First 500 characters
        - status: "uploaded"
    """
    file_id = str(uuid.uuid4())
    safe_filename = None
    
    try:
        # Validation
        Validator.validate_string(
            file.filename,
            "filename",
            min_length=1,
            max_length=255,
        )
        
        safe_filename = _sanitize_filename(file.filename)
        ext = _get_file_extension(file.filename)
        
        # Read file content
        content = await file.read()
        size = _validate_file_content(content, safe_filename)
        
        logger.info(f"Upload: {safe_filename} ({size} bytes) -> {file_id}")
        
        # Parse document
        try:
            text = parse_document_bytes(content, ext)
        except Exception as e:
            log_exception(e, f"Document parsing for {safe_filename}")
            raise FileParsingError(
                f"Dokument konnte nicht gelesen werden: {str(e)}",
                details={"filename": safe_filename, "extension": ext},
            )
        
        # Validate parsed text
        if not text or not text.strip():
            raise FileParsingError(
                "Dokument ist leer oder konnte nicht geparst werden",
                details={"filename": safe_filename},
            )
        
        # Cache parsed text
        text_cache.set(file_id, text, metadata={"filename": safe_filename})
        
        # For Excel: also cache raw bytes for structured parsing
        if ext in ('.xlsx', '.xls', '.xlsm'):
            project_cache.set(f"excel_{file_id}", content, ttl_seconds=1800)
        
        # Response
        text_preview = text[:500] + ("..." if len(text) > 500 else "")
        
        logger.info(f"✅ Upload successful: {file_id}")
        
        return {
            "file_id": file_id,
            "filename": safe_filename,
            "file_type": ext[1:].upper(),
            "text_length": len(text),
            "text_preview": text_preview,
            "status": "uploaded",
        }
    
    except FrankTuerenError as e:
        log_exception(e, f"Upload {file_id}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except HTTPException:
        raise
    except Exception as e:
        log_exception(e, f"Upload {file_id}")
        raise HTTPException(status_code=500, detail="Fehler beim Datei-Upload")


@router.post("/upload/folder", response_model=FolderUploadResponse)
async def upload_folder(files: List[UploadFile] = File(...)) -> dict:
    """
    Upload and classify multiple files (folder/batch upload).
    
    Creates a project_id for managing multiple related files.
    Classifies each file and determines if it's parseable.
    
    Returns:
        - project_id: Reference ID for this file batch
        - files: List of file metadata with classification
        - summary: Statistics (parseable count, images, errors, etc)
    """
    project_id = str(uuid.uuid4())[:12]
    
    try:
        # Validation
        if not files:
            raise ValidationError("Keine Dateien hochgeladen")
        
        if len(files) > settings.MAX_FILES_PER_UPLOAD:
            raise ValidationError(
                f"Zu viele Dateien ({len(files)} > {settings.MAX_FILES_PER_UPLOAD})",
                details={"count": len(files)},
            )
        
        logger.info(f"Folder upload: {len(files)} files -> {project_id}")
        
        # Process files
        file_entries = []
        stats = {
            "parseable": 0,
            "images": 0,
            "unsupported": 0,
            "errors": 0,
            "total_size": 0,
        }
        
        max_total = settings.MAX_FILE_SIZE_MB * 10 * 1024 * 1024
        
        for uploaded_file in files:
            try:
                # Validate
                Validator.validate_string(
                    uploaded_file.filename,
                    "filename",
                    min_length=1,
                    max_length=255,
                )
                
                safe_name = _sanitize_filename(uploaded_file.filename)
                ext = _get_file_extension(uploaded_file.filename)
                
                # Read and validate
                content = await uploaded_file.read()
                size = _validate_file_content(content, safe_name)
                
                stats["total_size"] += size
                if stats["total_size"] > max_total:
                    raise ValidationError(
                        "Gesamtgröße aller Dateien überschritten",
                        details={"total_mb": stats["total_size"] / 1024 / 1024},
                    )
                
                # Classify file
                file_id = str(uuid.uuid4())[:8]
                
                try:
                    classification = classify_file(safe_name, content=content)
                except Exception as e:
                    logger.warning(f"Classification failed for {safe_name}: {e}")
                    classification = {
                        "category": "unknown",
                        "confidence": 0.0,
                        "reason": "Klassifikation fehlgeschlagen",
                        "parseable": False,
                    }
                
                # Update stats
                if classification.get("parseable"):
                    stats["parseable"] += 1
                elif classification.get("category") == "image":
                    stats["images"] += 1
                else:
                    stats["unsupported"] += 1
                
                # Add entry
                file_entries.append(FileMetadata(
                    file_id=file_id,
                    filename=safe_name,
                    size=size,
                    extension=ext,
                    category=classification.get("category", "unknown"),
                    confidence=classification.get("confidence", 0.0),
                    parseable=classification.get("parseable", False),
                    reason=classification.get("reason", ""),
                ))
                
                logger.debug(f"File {file_id}: {safe_name} ({size} bytes)")
            
            except FrankTuerenError as e:
                stats["errors"] += 1
                logger.warning(f"File processing error: {e.message}")
                continue
            except Exception as e:
                stats["errors"] += 1
                logger.warning(f"Unexpected error processing {uploaded_file.filename}: {e}")
                continue
        
        if not file_entries:
            raise ValidationError("Keine unterstützten Dateien im Upload")
        
        # Cache project files
        project_cache.set(f"project_{project_id}", {
            "files": [f.dict() for f in file_entries],
            "stats": stats,
        }, ttl_seconds=1800)
        
        logger.info(f"✅ Project created: {project_id} | {len(file_entries)} files")
        
        return {
            "project_id": project_id,
            "total_files": len(file_entries),
            "files": file_entries,
            "summary": stats,
        }
    
    except FrankTuerenError as e:
        log_exception(e, f"Folder upload {project_id}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except HTTPException:
        raise
    except Exception as e:
        log_exception(e, f"Folder upload {project_id}")
        raise HTTPException(status_code=500, detail="Fehler beim Datei-Upload")


@router.get("/upload/health")
async def upload_health():
    """Health check for upload service."""
    return {
        "status": "ok",
        "max_file_size_mb": settings.MAX_FILE_SIZE_MB,
        "max_files_per_upload": settings.MAX_FILES_PER_UPLOAD,
        "cache_available": text_cache.size() < settings.CACHE_MAX_SIZE_MB * 1024 * 1024,
    }
