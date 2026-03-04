"""
Custom Exception Classes – Centralized error handling for the application.
Provides type-safe, structured error responses.
"""

from typing import Optional, Any
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ErrorSeverity(str, Enum):
    """Error severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AppException(Exception):
    """Base application exception with structured error information."""
    
    def __init__(
        self,
        message: str,
        code: str = "APP_ERROR",
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        details: Optional[dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        """
        Initialize custom exception.
        
        Args:
            message: Human-readable error message
            code: Machine-readable error code
            severity: Error severity level
            details: Additional context details
            cause: Original exception that caused this
        """
        self.message = message
        self.code = code
        self.severity = severity
        self.details = details or {}
        self.cause = cause
        
        # Log the exception
        log_method = {
            ErrorSeverity.INFO: logger.info,
            ErrorSeverity.WARNING: logger.warning,
            ErrorSeverity.ERROR: logger.error,
            ErrorSeverity.CRITICAL: logger.critical,
        }.get(severity, logger.error)
        
        log_method(
            f"{code}: {message}",
            extra={"details": self.details, "cause": str(cause) if cause else None}
        )
        
        super().__init__(message)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            "error": self.code,
            "message": self.message,
            "severity": self.severity.value,
            "details": self.details,
        }
    
    def to_api_response(self, status_code: int = 400) -> tuple[dict, int]:
        """Return tuple of (response_dict, http_status_code)."""
        return self.to_dict(), status_code


# ─────────────────────────────────────────────────────────────────────────────
# File & Upload Exceptions
# ─────────────────────────────────────────────────────────────────────────────

class FileUploadException(AppException):
    """Raised when file upload fails."""
    
    def __init__(self, message: str, details: Optional[dict] = None, cause: Optional[Exception] = None):
        super().__init__(
            message=message,
            code="FILE_UPLOAD_ERROR",
            severity=ErrorSeverity.WARNING,
            details=details,
            cause=cause,
        )


class UnsupportedFileTypeException(FileUploadException):
    """Raised when file type is not supported."""
    
    def __init__(self, file_type: str, allowed: set[str]):
        super().__init__(
            message=f"Dateityp '{file_type}' nicht unterstützt",
            details={"provided": file_type, "allowed": sorted(allowed)},
        )


class FileSizeExceededException(FileUploadException):
    """Raised when file size exceeds limit."""
    
    def __init__(self, size_bytes: int, max_bytes: int):
        super().__init__(
            message=f"Datei zu groß ({size_bytes / (1024*1024):.1f}MB, max {max_bytes / (1024*1024):.1f}MB)",
            details={"size_mb": round(size_bytes / (1024*1024), 2), "max_mb": round(max_bytes / (1024*1024), 2)},
        )


# ─────────────────────────────────────────────────────────────────────────────
# Document Parsing Exceptions
# ─────────────────────────────────────────────────────────────────────────────

class DocumentParsingException(AppException):
    """Raised when document parsing fails."""
    
    def __init__(self, message: str, file_path: Optional[str] = None, cause: Optional[Exception] = None):
        super().__init__(
            message=message,
            code="DOCUMENT_PARSING_ERROR",
            severity=ErrorSeverity.WARNING,
            details={"file": file_path} if file_path else {},
            cause=cause,
        )


class EmptyDocumentException(DocumentParsingException):
    """Raised when document is empty or has no readable content."""
    
    def __init__(self):
        super().__init__(
            message="Dokument ist leer oder konnte nicht geparst werden",
        )


class PDFParsingException(DocumentParsingException):
    """Raised when PDF parsing fails."""
    
    def __init__(self, message: str = "PDF-Datei konnte nicht geparst werden", cause: Optional[Exception] = None):
        super().__init__(message=message, cause=cause)


class ExcelParsingException(DocumentParsingException):
    """Raised when Excel parsing fails."""
    
    def __init__(self, message: str = "Excel-Datei konnte nicht geparst werden", cause: Optional[Exception] = None):
        super().__init__(message=message, cause=cause)


# ─────────────────────────────────────────────────────────────────────────────
# AI/LLM Exceptions
# ─────────────────────────────────────────────────────────────────────────────

class LLMException(AppException):
    """Raised when LLM interaction fails."""
    
    def __init__(self, message: str, model: Optional[str] = None, cause: Optional[Exception] = None):
        super().__init__(
            message=message,
            code="LLM_ERROR",
            severity=ErrorSeverity.ERROR,
            details={"model": model} if model else {},
            cause=cause,
        )


class OllamaException(LLMException):
    """Raised when Ollama is unavailable or fails."""
    
    def __init__(self, message: str = "Ollama nicht erreichbar", cause: Optional[Exception] = None):
        super().__init__(
            message=message,
            code="OLLAMA_ERROR",
            model="ollama",
            cause=cause,
        )


class OllamaTimeoutException(OllamaException):
    """Raised when Ollama request times out."""
    
    def __init__(self, timeout_seconds: float):
        super().__init__(
            message=f"Ollama Anfrage hat Timeout nach {timeout_seconds}s überschritten"
        )


class JSONRepairException(LLMException):
    """Raised when JSON repair fails."""
    
    def __init__(self, message: str = "JSON konnte nicht repariert werden", cause: Optional[Exception] = None):
        super().__init__(
            message=message,
            code="JSON_REPAIR_ERROR",
            cause=cause,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Product Matching Exceptions
# ─────────────────────────────────────────────────────────────────────────────

class ProductMatchingException(AppException):
    """Raised when product matching fails."""
    
    def __init__(self, message: str, cause: Optional[Exception] = None):
        super().__init__(
            message=message,
            code="PRODUCT_MATCHING_ERROR",
            severity=ErrorSeverity.WARNING,
            cause=cause,
        )


class CatalogLoadException(ProductMatchingException):
    """Raised when product catalog cannot be loaded."""
    
    def __init__(self, catalog_path: str, cause: Optional[Exception] = None):
        super().__init__(
            message=f"Produktkatalog konnte nicht geladen werden: {catalog_path}",
            cause=cause,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Data & Cache Exceptions
# ─────────────────────────────────────────────────────────────────────────────

class DataException(AppException):
    """Raised when data operation fails."""
    
    def __init__(self, message: str, cause: Optional[Exception] = None):
        super().__init__(
            message=message,
            code="DATA_ERROR",
            severity=ErrorSeverity.ERROR,
            cause=cause,
        )


class CacheException(DataException):
    """Raised when cache operation fails."""
    
    def __init__(self, message: str, cause: Optional[Exception] = None):
        super().__init__(
            message=message,
            cause=cause,
        )


class NotFoundError(DataException):
    """Raised when requested resource is not found."""
    
    def __init__(self, resource_type: str, resource_id: str):
        super().__init__(
            message=f"{resource_type} '{resource_id}' nicht gefunden",
            code="NOT_FOUND",
            severity=ErrorSeverity.WARNING,
        )
    
    def to_api_response(self, status_code: int = 404) -> tuple[dict, int]:
        return self.to_dict(), 404


# ─────────────────────────────────────────────────────────────────────────────
# Validation Exceptions
# ─────────────────────────────────────────────────────────────────────────────

class ValidationException(AppException):
    """Raised when input validation fails."""
    
    def __init__(self, message: str, field: Optional[str] = None, value: Optional[Any] = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            severity=ErrorSeverity.WARNING,
            details={"field": field, "value": str(value)[:100]} if field else {},
        )


# ─────────────────────────────────────────────────────────────────────────────
# Configuration Exceptions
# ─────────────────────────────────────────────────────────────────────────────

class ConfigurationException(AppException):
    """Raised when configuration is invalid."""
    
    def __init__(self, message: str, setting: Optional[str] = None):
        super().__init__(
            message=message,
            code="CONFIG_ERROR",
            severity=ErrorSeverity.CRITICAL,
            details={"setting": setting} if setting else {},
        )


# ─────────────────────────────────────────────────────────────────────────────
# Job Exceptions
# ─────────────────────────────────────────────────────────────────────────────

class JobException(AppException):
    """Raised when job operation fails."""
    
    def __init__(self, message: str, job_id: Optional[str] = None):
        super().__init__(
            message=message,
            code="JOB_ERROR",
            severity=ErrorSeverity.ERROR,
            details={"job_id": job_id} if job_id else {},
        )


class JobTimeoutException(JobException):
    """Raised when job times out."""
    
    def __init__(self, job_id: str, timeout_seconds: int):
        super().__init__(
            message=f"Job {job_id} hat Timeout nach {timeout_seconds}s überschritten",
            code="JOB_TIMEOUT",
            severity=ErrorSeverity.WARNING,
            job_id=job_id,
        )
