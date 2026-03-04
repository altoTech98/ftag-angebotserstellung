"""
═══════════════════════════════════════════════════════════════════════════════
Upload Router – Production-Grade File Upload & Parsing
In-Memory Processing, Automatic Classification, Multi-File Support
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import uuid
import logging
from typing import List, Tuple
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from pydantic import BaseModel

from config import settings
from services.document_parser import parse_document_bytes, DocumentParser
from services.file_classifier import classify_file
from services.project_store import create_project
from services.memory_cache import text_cache, project_cache
from services.error_handler import (
    ValidationError, FileError, ErrorCode, 
    validate_file_extension, validate_file_size
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ─────────────────────────────────────────────────────────────────────────────
# PYDANTIC MODELS
# ─────────────────────────────────────────────────────────────────────────────

class UploadResponse(BaseModel):
    """Single File Upload Response"""
    file_id: str
    filename: str
    file_type: str
    text_length: int
    text_preview: str
    status: str
    message: str


class FileMetadata(BaseModel):
    """Datei-Metadaten für Folder Upload"""
    file_id: str
    filename: str
    size: int
    extension: str
    category: str
    confidence: float
    parseable: bool
    reason: str = ""


class FolderUploadResponse(BaseModel):
    """Folder/Multi-File Upload Response"""
    project_id: str
    total_files: int
    files: List[FileMetadata]
    summary: dict
    status: str
    message: str


# ─────────────────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def _validate_and_normalize_filename(filename: str) -> Tuple[str, str]:
    """
    Validiert und normalisiert Dateinamen.
    
    Args:
        filename: Original-Dateiname
        
    Returns:
        (safe_filename, extension)
        
    Raises:
        ValidationError: Wenn Dateiname ungültig
    """
    if not filename:
        raise ValidationError("Dateiname ist erforderlich", field="filename")
    
    if len(filename) > 255:
        raise ValidationError(
            "Dateiname zu lang (max. 255 Zeichen)",
            field="filename"
        )
    
    # Extension extrahieren
    name, ext = os.path.splitext(filename)
    ext = ext.lower()
    
    # Sanitize: Pfad-Separatoren entfernen
    safe_name = name.replace("/", "_").replace("\\", "_")[:240]
    
    if not safe_name:
        raise ValidationError(
            "Ungültiger Dateiname",
            field="filename"
        )
    
    return f"{safe_name}{ext}", ext


def _handle_upload_error(file_id: str, error: Exception):
    """Loggt Upload-Fehler strukturiert"""
    if isinstance(error, ValidationError):
        logger.warning(f"Upload {file_id} Validierungsfehler: {error.message}")
    elif isinstance(error, FileError):
        logger.warning(f"Upload {file_id} Datei-Fehler: {error.message}")
    else:
        logger.error(f"Upload {file_id} Fehler: {str(error)}", exc_info=True)


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/upload", response_model=UploadResponse, tags=["Upload"])
async def upload_document(file: UploadFile = File(...)) -> dict:
    """
    Lädt eine einzelne Ausschreibungs-Datei hoch und parst sie.
    
    Unterstützt: PDF, Excel (.xlsx), Word (.docx), TXT
    
    Returns:
        - file_id: UUID zum Referenzieren der Datei
        - text_length: Anzahl extrahierter Zeichen
        - text_preview: Erste 500 Zeichen
        - status: "uploaded"
        
    Processing:
        1. Dateivalidierung
        2. In-Memory Parsing (keine Disk-Writes)
        3. Text-Extraktion & Caching
        4. Für Excel: Strukturierter Parse-Path
        
    Raises:
        HTTPException: Bei Validierungs- oder Parse-Fehlern
    """
    file_id = str(uuid.uuid4())
    
    try:
        # ─── VALIDIERUNG ───
        safe_filename, ext = _validate_and_normalize_filename(file.filename)
        
        # Datei-Typ prüfen
        if not DocumentParser.is_supported(file.filename):
            supported = ", ".join(DocumentParser.SUPPORTED_FORMATS.keys())
            raise ValidationError(
                f"Dateityp '{ext}' nicht unterstützt",
                field="file_type",
                details={"supported": supported}
            )
        
        # Inhalt lesen
        content = await file.read()
        
        # Größe validieren
        validate_file_size(len(content), settings.MAX_FILE_SIZE_MB)
        
        # ─── PARSING ───
        logger.info(f"Upload: {safe_filename} ({len(content)} bytes) → {file_id}")
        
        try:
            text = parse_document_bytes(content, ext)
        except FileError:
            raise
        except Exception as e:
            logger.exception(f"Parse-Fehler für {safe_filename}")
            raise FileError(
                ErrorCode.FILE_PARSE_ERROR,
                f"Dokument konnte nicht gelesen werden",
                filename=safe_filename
            )
        
        # ─── CACHING ───
        text_cache.set(file_id, text, metadata={"filename": safe_filename, "ext": ext})
        
        # Für Excel: Raw-Bytes auch cachen für strukturierten Parse
        if ext in (".xlsx", ".xls", ".xlsm"):
            project_cache.set(f"excel_{file_id}", content)
            logger.debug(f"Excel-Bytes gecacht für {file_id}")
        
        # ─── RESPONSE ───
        text_preview = text[:500] + ("..." if len(text) > 500 else "")
        
        logger.info(f"✅ Upload erfolgreich: {file_id}")
        
        return {
            "file_id": file_id,
            "filename": safe_filename,
            "file_type": ext,
            "text_length": len(text),
            "text_preview": text_preview,
            "status": "uploaded",
            "message": f"✅ '{safe_filename}' hochgeladen ({len(text)} Zeichen)"
        }
    
    except ValidationError as e:
        e.log(context=f"upload/{file_id}")
        raise HTTPException(
            status_code=422,
            detail=e.message
        )
    except FileError as e:
        e.log(context=f"upload/{file_id}")
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Upload-Fehler: {file_id}")
        raise HTTPException(
            status_code=500,
            detail="Fehler beim Hochladen der Datei"
        )


@router.post("/upload/folder", response_model=FolderUploadResponse, tags=["Upload"])
async def upload_folder(files: List[UploadFile] = File(...)) -> dict:
    """
    Lädt mehrere Dateien (Ordner oder Multi-Select) als Projekt hoch.
    
    Processing:
        1. Dateivalidierung & Normalisierung
        2. In-Memory Klassifikation
        3. Projekt-Erstellung (alle Dateien gruppieren)
        4. Bytes-Caching für spätere Analyse
    
    Returns:
        - project_id: UUID für das Multi-File Projekt
        - files: Array mit klassifizierten Dateien
        - summary: Statistiken
        
    Note:
        - Nicht unterstützte Dateien werden übersprungen
        - Maximale Gesamtgröße: siehe settings.MAX_FILE_SIZE_MB * 10
        
    Raises:
        HTTPException: Bei kritischen Fehlern
    """
    project_id = str(uuid.uuid4())[:12]
    
    try:
        logger.info(f"Folder-Upload: {len(files)} Dateien, Projekt: {project_id}")
        
        if not files:
            raise ValidationError("Keine Dateien hochgeladen", field="files")
        
        if len(files) > settings.MAX_FILES_PER_UPLOAD:
            raise ValidationError(
                f"Zu viele Dateien ({len(files)} > {settings.MAX_FILES_PER_UPLOAD})",
                field="files"
            )
        
        # ─── VERARBEITUNG ───
        total_size = 0
        max_total_size = settings.MAX_FILE_SIZE_MB * 10 * 1024 * 1024
        
        file_entries = []
        file_bytes_map = {}
        
        stats = {
            "parseable": 0,
            "images": 0,
            "unsupported": 0,
            "errors": 0,
            "total_size": 0
        }
        
        for uploaded_file in files:
            try:
                # Validierung
                safe_name, ext = _validate_and_normalize_filename(uploaded_file.filename)
                
                if ext not in settings.ALLOWED_EXTENSIONS:
                    stats["unsupported"] += 1
                    logger.debug(f"Datei übersprungen: {safe_name} ({ext})")
                    continue
                
                # Inhalt lesen
                content = await uploaded_file.read()
                if not content:
                    logger.warning(f"Leere Datei: {safe_name}")
                    stats["errors"] += 1
                    continue
                
                # Größe prüfen
                file_size = len(content)
                total_size += file_size
                stats["total_size"] = total_size
                
                if total_size > max_total_size:
                    raise ValidationError(
                        f"Gesamtgröße überschritten",
                        field="total_size",
                        details={"max_mb": max_total_size / (1024 * 1024)}
                    )
                
                # ─── KLASSIFIKATION ───
                file_id = str(uuid.uuid4())[:8]
                
                try:
                    classification = classify_file(safe_name, content=content)
                except Exception as e:
                    logger.warning(f"Klassifikation fehlgeschlagen für {safe_name}: {e}")
                    classification = {
                        "category": "sonstig",
                        "confidence": 0.0,
                        "reason": "Klassifikation fehlgeschlagen",
                        "parseable": False,
                    }
                
                # Statistiken aktualisieren
                if classification.get("parseable"):
                    file_bytes_map[file_id] = content
                    stats["parseable"] += 1
                elif classification.get("category") == "bild":
                    stats["images"] += 1
                
                # Eintrag hinzufügen
                file_entries.append({
                    "file_id": file_id,
                    "filename": safe_name,
                    "size": file_size,
                    "extension": ext,
                    **classification
                })
                
                logger.debug(
                    f"Datei {file_id}: {safe_name} "
                    f"({file_size} bytes, {classification.get('category')})"
                )
            
            except ValidationError as e:
                stats["errors"] += 1
                logger.warning(f"Validierungsfehler in {uploaded_file.filename}: {e.message}")
                continue
            except Exception as e:
                stats["errors"] += 1
                logger.warning(f"Fehler beim Verarbeiten von {uploaded_file.filename}: {e}")
                continue
        
        if not file_entries:
            raise ValidationError(
                "Keine unterstützten Dateien im Upload",
                field="files"
            )
        
        # ─── CACHING ───
        if file_bytes_map:
            project_cache.set(f"project_{project_id}", file_bytes_map)
            logger.debug(f"Projekt-Bytes gecacht: {project_id}")
        
        # ─── PROJEKT ERSTELLEN ───
        project = create_project(file_entries, project_id=project_id)
        
        logger.info(
            f"✅ Projekt erstellt: {project_id} | "
            f"{len(file_entries)} Dateien, "
            f"{stats['parseable']} analysierbar, "
            f"{stats['images']} Bilder"
        )
        
        return {
            "project_id": project_id,
            "total_files": len(file_entries),
            "files": [
                FileMetadata(
                    file_id=f["file_id"],
                    filename=f["filename"],
                    size=f["size"],
                    extension=f["extension"],
                    category=f["category"],
                    confidence=f["confidence"],
                    parseable=f["parseable"],
                    reason=f.get("reason", "")
                )
                for f in file_entries
            ],
            "summary": {
                **project.get("summary", {}),
                **stats
            },
            "status": "classified",
            "message": (
                f"✅ {len(file_entries)} Dateien klassifiziert "
                f"({stats['parseable']} analysierbar, {stats['images']} Bilder)"
            )
        }
    
    except ValidationError as e:
        e.log(context=f"upload/folder/{project_id}")
        raise HTTPException(status_code=422, detail=e.message)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Folder-Upload Fehler: {project_id}")
        raise HTTPException(status_code=500, detail="Fehler beim Hochladen der Dateien")
