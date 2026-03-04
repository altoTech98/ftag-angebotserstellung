"""
Input Validators – Type-safe, comprehensive validation for all endpoints.
Handles file uploads, document analysis, offer requests, etc.
"""

import re
import logging
from typing import Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class ValidationError(ValueError):
    """Raised when validation fails."""
    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")


# ─────────────────────────────────────────────────────────────────────────────
# File Validators
# ─────────────────────────────────────────────────────────────────────────────

def validate_file_extension(filename: str, allowed_extensions: set[str]) -> bool:
    """Check if file has allowed extension (case-insensitive)."""
    if not filename:
        raise ValidationError("filename", "Dateiname nicht vorhanden")
    
    ext = Path(filename).suffix.lower().lstrip(".")
    if not ext:
        raise ValidationError("filename", "Dateiendung nicht erkannt")
    
    if ext not in allowed_extensions:
        raise ValidationError(
            "filename",
            f"Dateityp '.{ext}' nicht unterstützt. Erlaubt: {', '.join(sorted(allowed_extensions))}"
        )
    
    return True


def validate_file_size(size_bytes: int, max_bytes: int) -> bool:
    """Check if file size is within limits."""
    if size_bytes <= 0:
        raise ValidationError("size", "Dateisize ungültig")
    
    if size_bytes > max_bytes:
        max_mb = max_bytes / (1024 * 1024)
        size_mb = size_bytes / (1024 * 1024)
        raise ValidationError(
            "size",
            f"Datei zu groß ({size_mb:.1f}MB, max {max_mb:.1f}MB)"
        )
    
    return True


def validate_filename(filename: str) -> bool:
    """Check filename for security issues (no path traversal, etc)."""
    if not filename or len(filename) > 255:
        raise ValidationError("filename", "Dateiname ungültig oder zu lang")
    
    # Block path traversal attempts
    if ".." in filename or "/" in filename or "\\" in filename:
        raise ValidationError("filename", "Ungültiger Dateiname (Path-Traversal erkannt)")
    
    # Block null bytes and control characters
    if any(ord(c) < 32 for c in filename):
        raise ValidationError("filename", "Ungültige Zeichen im Dateinamen")
    
    return True


# ─────────────────────────────────────────────────────────────────────────────
# String Validators
# ─────────────────────────────────────────────────────────────────────────────

def validate_text_length(text: str, min_length: int = 10, max_length: int = 1000000, field: str = "text") -> bool:
    """Validate text length."""
    if not isinstance(text, str):
        raise ValidationError(field, "Text muss ein String sein")
    
    if len(text) < min_length:
        raise ValidationError(field, f"Text zu kurz (mindestens {min_length} Zeichen)")
    
    if len(text) > max_length:
        raise ValidationError(field, f"Text zu lang (maximal {max_length} Zeichen)")
    
    return True


def validate_email(email: str) -> bool:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not email or not re.match(pattern, email):
        raise ValidationError("email", "Ungültiges E-Mail-Format")
    
    return True


def validate_url(url: str) -> bool:
    """Validate URL format."""
    pattern = r'^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(:[0-9]+)?(/.*)?$'
    
    if not url or not re.match(pattern, url):
        raise ValidationError("url", "Ungültiges URL-Format")
    
    return True


def validate_phone(phone: str) -> bool:
    """Validate phone number (Swiss format preferred but flexible)."""
    # Remove common separators
    cleaned = re.sub(r'[\s\-\(\)\+\.]', '', phone)
    
    if not cleaned or len(cleaned) < 7:
        raise ValidationError("phone", "Ungültige Telefonnummer")
    
    if not cleaned.isdigit() and not cleaned.startswith('+'):
        raise ValidationError("phone", "Telefonnummer darf nur Ziffern enthalten")
    
    return True


# ─────────────────────────────────────────────────────────────────────────────
# Number Validators
# ─────────────────────────────────────────────────────────────────────────────

def validate_integer(value: Any, min_val: Optional[int] = None, max_val: Optional[int] = None, field: str = "value") -> int:
    """Validate and convert to integer."""
    try:
        val = int(value)
    except (ValueError, TypeError):
        raise ValidationError(field, f"Wert muss eine Ganzzahl sein, erhalten: {value}")
    
    if min_val is not None and val < min_val:
        raise ValidationError(field, f"Wert muss >= {min_val} sein")
    
    if max_val is not None and val > max_val:
        raise ValidationError(field, f"Wert muss <= {max_val} sein")
    
    return val


def validate_float(value: Any, min_val: Optional[float] = None, max_val: Optional[float] = None, field: str = "value") -> float:
    """Validate and convert to float."""
    try:
        val = float(value)
    except (ValueError, TypeError):
        raise ValidationError(field, f"Wert muss eine Dezimalzahl sein, erhalten: {value}")
    
    if min_val is not None and val < min_val:
        raise ValidationError(field, f"Wert muss >= {min_val} sein")
    
    if max_val is not None and val > max_val:
        raise ValidationError(field, f"Wert muss <= {max_val} sein")
    
    return val


# ─────────────────────────────────────────────────────────────────────────────
# Business Logic Validators
# ─────────────────────────────────────────────────────────────────────────────

def validate_door_dimensions(width_mm: int, height_mm: int) -> bool:
    """Validate door dimensions."""
    # Realistic door dimensions (in mm)
    MIN_WIDTH, MAX_WIDTH = 600, 3000
    MIN_HEIGHT, MAX_HEIGHT = 1800, 3500
    
    width = validate_integer(width_mm, field="breite_mm")
    height = validate_integer(height_mm, field="hoehe_mm")
    
    if not (MIN_WIDTH <= width <= MAX_WIDTH):
        raise ValidationError("breite_mm", f"Breite muss zwischen {MIN_WIDTH} und {MAX_WIDTH}mm liegen")
    
    if not (MIN_HEIGHT <= height <= MAX_HEIGHT):
        raise ValidationError("hoehe_mm", f"Höhe muss zwischen {MIN_HEIGHT} und {MAX_HEIGHT}mm liegen")
    
    return True


def validate_fire_class(fire_class: str) -> bool:
    """Validate fire class format (EI30, T30, etc)."""
    if not fire_class or not isinstance(fire_class, str):
        return True  # Optional field
    
    pattern = r'^(EI|T|F)(\d+)?$'
    if not re.match(pattern, fire_class.upper()):
        raise ValidationError("fire_class", f"Ungültiges Brandschutzformat: {fire_class}")
    
    return True


def validate_sound_class(db_value: str) -> bool:
    """Validate sound class (dB value)."""
    if not db_value or not isinstance(db_value, str):
        return True  # Optional field
    
    # Extract number from strings like "32 dB", "Rw=35", etc.
    match = re.search(r'(\d+)', str(db_value))
    if not match:
        raise ValidationError("sound_class", f"Ungültiges Schallschutzformat: {db_value}")
    
    db = int(match.group(1))
    if not (20 <= db <= 80):
        raise ValidationError("sound_class", "dB-Wert muss zwischen 20 und 80 liegen")
    
    return True


def validate_quantity(quantity: int) -> bool:
    """Validate door quantity."""
    qty = validate_integer(quantity, min_val=1, max_val=1000, field="menge")
    return qty > 0


# ─────────────────────────────────────────────────────────────────────────────
# API Request Validators
# ─────────────────────────────────────────────────────────────────────────────

def validate_analyze_request(file_id: str) -> bool:
    """Validate analyze API request."""
    if not file_id or not isinstance(file_id, str):
        raise ValidationError("file_id", "file_id erforderlich")
    
    if len(file_id) > 255:
        raise ValidationError("file_id", "file_id zu lang")
    
    return True


def validate_offer_request(
    analysis_id: Optional[str] = None,
    project_id: Optional[str] = None,
) -> bool:
    """Validate offer generation request."""
    if not analysis_id and not project_id:
        raise ValidationError("request", "analysis_id oder project_id erforderlich")
    
    if analysis_id and len(analysis_id) > 255:
        raise ValidationError("analysis_id", "analysis_id zu lang")
    
    if project_id and len(project_id) > 255:
        raise ValidationError("project_id", "project_id zu lang")
    
    return True


def validate_feedback_request(
    rating: int,
    comment: Optional[str] = None,
) -> bool:
    """Validate feedback submission."""
    rating = validate_integer(rating, min_val=1, max_val=5, field="rating")
    
    if comment:
        validate_text_length(comment, min_length=5, max_length=5000, field="comment")
    
    return True


# ─────────────────────────────────────────────────────────────────────────────
# Batch Validators
# ─────────────────────────────────────────────────────────────────────────────

def validate_file_batch(
    filenames: list[str],
    file_sizes: list[int],
    allowed_extensions: set[str],
    max_file_size: int,
    max_files: int,
) -> bool:
    """Validate batch of files."""
    if len(filenames) != len(file_sizes):
        raise ValidationError("files", "Anzahl Dateinamen und Größen stimmen nicht überein")
    
    if len(filenames) > max_files:
        raise ValidationError("files", f"Maximal {max_files} Dateien pro Upload")
    
    for filename, size in zip(filenames, file_sizes):
        validate_filename(filename)
        validate_file_extension(filename, allowed_extensions)
        validate_file_size(size, max_file_size)
    
    return True


# ─────────────────────────────────────────────────────────────────────────────
# Decorator for Auto-Validation
# ─────────────────────────────────────────────────────────────────────────────

def require_valid_file_id(func):
    """Decorator to automatically validate file_id parameter."""
    async def wrapper(request, *args, **kwargs):
        file_id = request.file_id if hasattr(request, 'file_id') else kwargs.get('file_id')
        try:
            validate_analyze_request(file_id)
        except ValidationError as e:
            from fastapi import HTTPException
            raise HTTPException(status_code=422, detail=e.message)
        return await func(request, *args, **kwargs)
    return wrapper
