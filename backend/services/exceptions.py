"""
Custom exception classes and error handling utilities.
Provides structured error responses and logging.
"""

import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class FrankTuerenError(Exception):
    """Base exception for Frank Türen AG application."""
    
    def __init__(
        self,
        message: str,
        error_code: str = "UNKNOWN_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to API response dict."""
        return {
            "error": self.error_code,
            "message": self.message,
            "status_code": self.status_code,
            "details": self.details,
        }


class FileUploadError(FrankTuerenError):
    """Raised when file upload/processing fails."""
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            message,
            error_code="FILE_UPLOAD_ERROR",
            status_code=400,
            details=details,
        )


class FileParsingError(FrankTuerenError):
    """Raised when file parsing fails."""
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            message,
            error_code="FILE_PARSING_ERROR",
            status_code=422,
            details=details,
        )


class AnalysisError(FrankTuerenError):
    """Raised when document analysis fails."""
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            message,
            error_code="ANALYSIS_ERROR",
            status_code=422,
            details=details,
        )


class MatchingError(FrankTuerenError):
    """Raised when product matching fails."""
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            message,
            error_code="MATCHING_ERROR",
            status_code=422,
            details=details,
        )


class OfferGenerationError(FrankTuerenError):
    """Raised when offer generation fails."""
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            message,
            error_code="OFFER_GENERATION_ERROR",
            status_code=500,
            details=details,
        )


class LLMError(FrankTuerenError):
    """Raised when LLM (Ollama) operations fail."""
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            message,
            error_code="LLM_ERROR",
            status_code=503,
            details=details,
        )


class ValidationError(FrankTuerenError):
    """Raised when input validation fails."""
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            message,
            error_code="VALIDATION_ERROR",
            status_code=400,
            details=details,
        )


def log_exception(exc: Exception, context: str = "") -> None:
    """Log exception with context information."""
    if isinstance(exc, FrankTuerenError):
        logger.error(
            f"{context} - {exc.error_code}: {exc.message}",
            extra={"details": exc.details},
            exc_info=True,
        )
    else:
        logger.error(f"{context}: {str(exc)}", exc_info=True)
