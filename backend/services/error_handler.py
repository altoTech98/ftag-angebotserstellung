"""
═══════════════════════════════════════════════════════════════════════════════
Error Handler & Validation Service
Zentrale Fehlerbehandlung, Logging & Validierung
═══════════════════════════════════════════════════════════════════════════════
"""

import logging
import traceback
from typing import Optional, Any, Callable
from functools import wraps
from enum import Enum

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


class AppException(Exception):
    """Basis Exception für die Applikation"""
    
    def __init__(
        self, 
        code: ErrorCode, 
        message: str, 
        status_code: int = 400,
        details: Optional[dict] = None,
        original_error: Optional[Exception] = None
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        self.original_error = original_error
        super().__init__(message)
    
    def to_dict(self) -> dict:
        """Konvertiert Exception zu API Response"""
        return {
            "error": {
                "code": self.code.value,
                "message": self.message,
                "details": self.details
            }
        }
    
    def log(self, context: str = ""):
        """Loggt Exception mit Kontext"""
        logger.error(
            f"[{self.code.value}] {self.message} | Context: {context}",
            exc_info=self.original_error,
            extra={"details": self.details}
        )


class ValidationError(AppException):
    """Input-Validierungsfehler"""
    def __init__(self, message: str, field: str = "", details: dict = None):
        super().__init__(
            code=ErrorCode.INVALID_INPUT,
            message=message,
            status_code=422,
            details=details or {"field": field}
        )


class FileError(AppException):
    """Dateioperation-Fehler"""
    def __init__(self, code: ErrorCode, message: str, filename: str = ""):
        super().__init__(
            code=code,
            message=message,
            status_code=400 if code != ErrorCode.FILE_NOT_FOUND else 404,
            details={"filename": filename}
        )


class ProcessingError(AppException):
    """Verarbeitungsfehler"""
    def __init__(self, message: str, operation: str = "", original_error: Exception = None):
        super().__init__(
            code=ErrorCode.ANALYSIS_FAILED,
            message=message,
            status_code=500,
            details={"operation": operation},
            original_error=original_error
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
            except AppException as e:
                e.log(context=func.__name__)
                raise
            except Exception as e:
                if log_traceback:
                    logger.exception(f"Unbehandelte Exception in {func.__name__}")
                exc = ProcessingError(
                    message=str(e) or f"Fehler in {func.__name__}",
                    operation=func.__name__,
                    original_error=e
                )
                exc.log()
                raise exc
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except AppException as e:
                e.log(context=func.__name__)
                raise
            except Exception as e:
                if log_traceback:
                    logger.exception(f"Unbehandelte Exception in {func.__name__}")
                exc = ProcessingError(
                    message=str(e) or f"Fehler in {func.__name__}",
                    operation=func.__name__,
                    original_error=e
                )
                exc.log()
                raise exc
        
        # Wähle Wrapper basierend auf async/sync
        if hasattr(func, '__await__') or 'async' in str(func.__code__.co_flags):
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
