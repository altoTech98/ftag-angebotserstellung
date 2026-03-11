"""
═══════════════════════════════════════════════════════════════════════════════
Error Handler & Validation Service
Zentrale Fehlerbehandlung, Logging & Validierung

NOTE: Exception-Hierarchie basiert auf FrankTuerenError (services/exceptions.py).
FileError, ProcessingError etc. sind spezialisierte Subklassen für den Parser.
═══════════════════════════════════════════════════════════════════════════════
"""

import logging
import traceback
from typing import Optional, Any, Callable
from functools import wraps
from enum import Enum

from services.exceptions import FrankTuerenError

logger = logging.getLogger(__name__)


class ErrorCode(str, Enum):
    """Standardisierte Fehler-Codes"""
    # Validation
    INVALID_FILE = "INVALID_FILE"
    INVALID_INPUT = "INVALID_INPUT"
    INVALID_JSON = "INVALID_JSON"

    # File Operations
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    FILE_PARSE_ERROR = "FILE_PARSE_ERROR"
    FILE_SIZE_EXCEEDED = "FILE_SIZE_EXCEEDED"

    # Processing
    ANALYSIS_FAILED = "ANALYSIS_FAILED"
    MATCH_FAILED = "MATCH_FAILED"
    GENERATION_FAILED = "GENERATION_FAILED"

    # External Services
    CLAUDE_API_ERROR = "CLAUDE_API_ERROR"
    OLLAMA_ERROR = "OLLAMA_ERROR"
    ERP_ERROR = "ERP_ERROR"

    # System
    INTERNAL_ERROR = "INTERNAL_ERROR"
    RESOURCE_EXPIRED = "RESOURCE_EXPIRED"
    TIMEOUT = "TIMEOUT"


class FileError(FrankTuerenError):
    """Dateioperation-Fehler"""
    def __init__(self, code: ErrorCode, message: str, filename: str = ""):
        super().__init__(
            message=message,
            error_code=code.value,
            status_code=400 if code != ErrorCode.FILE_NOT_FOUND else 404,
            details={"filename": filename},
        )


class ProcessingError(FrankTuerenError):
    """Verarbeitungsfehler"""
    def __init__(self, message: str, operation: str = "", original_error: Exception = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.ANALYSIS_FAILED.value,
            status_code=500,
            details={"operation": operation},
        )
        self.original_error = original_error


class ValidationError(FrankTuerenError):
    """Input-Validierungsfehler"""
    def __init__(self, message: str, field: str = "", details: dict = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.INVALID_INPUT.value,
            status_code=422,
            details=details or {"field": field},
        )


def handle_exceptions(
    error_code: ErrorCode = ErrorCode.INTERNAL_ERROR,
    log_traceback: bool = True,
    return_default: Any = None
):
    """Decorator für automatische Exception-Behandlung"""
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except FrankTuerenError:
                raise
            except Exception as e:
                if log_traceback:
                    logger.exception(f"Unbehandelte Exception in {func.__name__}")
                raise ProcessingError(
                    message=str(e) or f"Fehler in {func.__name__}",
                    operation=func.__name__,
                    original_error=e
                )

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except FrankTuerenError:
                raise
            except Exception as e:
                if log_traceback:
                    logger.exception(f"Unbehandelte Exception in {func.__name__}")
                raise ProcessingError(
                    message=str(e) or f"Fehler in {func.__name__}",
                    operation=func.__name__,
                    original_error=e
                )

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def validate_file_extension(filename: str, allowed_extensions: list[str]) -> bool:
    """Validiert Dateiendung"""
    if not filename:
        raise ValidationError("Dateiname ist erforderlich", field="filename")
    
    ext = filename.split('.')[-1].lower()
    if ext not in allowed_extensions:
        raise ValidationError(
            f"Dateiendung nicht erlaubt. Erlaubt: {', '.join(allowed_extensions)}",
            field="filename",
            details={"given": ext, "allowed": allowed_extensions}
        )
    return True


def validate_file_size(size: int, max_size_mb: int = 100) -> bool:
    """Validiert Dateigröße"""
    max_bytes = max_size_mb * 1024 * 1024
    if size > max_bytes:
        raise ValidationError(
            f"Datei zu groß. Maximum: {max_size_mb}MB",
            field="file_size",
            details={"given_mb": size / (1024 * 1024), "max_mb": max_size_mb}
        )
    return True


def validate_non_empty_string(value: Optional[str], field_name: str) -> str:
    """Validiert nicht-leere Strings"""
    if not value or not value.strip():
        raise ValidationError(f"{field_name} darf nicht leer sein", field=field_name)
    return value.strip()


def safe_get_nested(data: dict, keys: list[str], default: Any = None) -> Any:
    """Sicherer Zugriff auf verschachtelte Dict-Keys"""
    try:
        current = data
        for key in keys:
            if isinstance(current, dict):
                current = current.get(key)
            else:
                return default
        return current if current is not None else default
    except (KeyError, TypeError, AttributeError):
        return default


def format_error_response(error: AppException, include_traceback: bool = False) -> dict:
    """Formatiert Error-Response für API"""
    response = error.to_dict()
    
    if include_traceback and error.original_error:
        response["error"]["traceback"] = traceback.format_exc()
    
    return response
