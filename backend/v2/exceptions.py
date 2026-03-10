"""
V2 Exception Hierarchy - Independent from v1.

All v2 modules raise exceptions from this module only.
No imports from v1 exceptions.
"""


class V2Error(Exception):
    """Base exception for the v2 pipeline."""

    def __init__(self, message: str, code: str = "V2_ERROR", details: dict = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(code={self.code!r}, message={self.message!r})"


class ParseError(V2Error):
    """Document parsing failed."""

    def __init__(self, message: str, filename: str = "", details: dict = None):
        super().__init__(
            message,
            code="PARSE_ERROR",
            details={"filename": filename, **(details or {})},
        )


class SchemaValidationError(V2Error):
    """Pydantic schema validation failed."""

    def __init__(self, message: str, model: str = "", details: dict = None):
        super().__init__(
            message,
            code="SCHEMA_VALIDATION_ERROR",
            details={"model": model, **(details or {})},
        )


class ExtractionError(V2Error):
    """AI extraction from parsed text failed."""

    def __init__(self, message: str, details: dict = None):
        super().__init__(message, code="EXTRACTION_ERROR", details=details)


class MatchingError(V2Error):
    """Product matching failed."""

    def __init__(self, message: str, details: dict = None):
        super().__init__(message, code="MATCHING_ERROR", details=details)


class ValidationError(V2Error):
    """Adversarial validation failed."""

    def __init__(self, message: str, details: dict = None):
        super().__init__(message, code="VALIDATION_ERROR", details=details)


class PipelineError(V2Error):
    """Pipeline orchestration error."""

    def __init__(self, message: str, details: dict = None):
        super().__init__(message, code="PIPELINE_ERROR", details=details)


class AIServiceError(PipelineError):
    """AI service failure with German user-facing message.

    Used by raise_ai_error() to convert anthropic SDK exceptions
    into user-friendly errors with stage context.
    """

    def __init__(self, message: str, stage: str, api_error: str = ""):
        super().__init__(
            message=message,
            details={"stage": stage, "api_error": api_error},
        )
        self.code = "AI_SERVICE_ERROR"


def _is_anthropic_error(exception: Exception, class_name: str) -> bool:
    """Check if an exception is a specific anthropic error type by class name.

    Uses class name matching to avoid hard dependency on anthropic SDK.
    """
    for cls in type(exception).__mro__:
        if cls.__name__ == class_name:
            return True
    return False


def raise_ai_error(exception: Exception, stage: str) -> None:
    """Convert an exception to AIServiceError with German message.

    Maps common anthropic SDK exceptions to user-friendly German messages.
    Always raises AIServiceError - never returns.

    Args:
        exception: The caught exception (typically from anthropic SDK).
        stage: Pipeline stage where the error occurred.

    Raises:
        AIServiceError: Always raised with appropriate German message.
    """
    api_error_str = str(exception)

    if _is_anthropic_error(exception, "APIConnectionError"):
        raise AIServiceError(
            message="KI-Service nicht erreichbar. Bitte Internetverbindung pruefen.",
            stage=stage,
            api_error=api_error_str,
        )
    elif _is_anthropic_error(exception, "RateLimitError"):
        raise AIServiceError(
            message="KI-Service ueberlastet. Bitte in einigen Minuten erneut versuchen.",
            stage=stage,
            api_error=api_error_str,
        )
    elif _is_anthropic_error(exception, "APIStatusError"):
        status_code = getattr(exception, "status_code", "unbekannt")
        raise AIServiceError(
            message=f"KI-Service Fehler ({status_code}). Bitte spaeter erneut versuchen.",
            stage=stage,
            api_error=api_error_str,
        )
    else:
        raise AIServiceError(
            message=f"KI-Service nicht verfuegbar: {exception}. Bitte spaeter erneut versuchen.",
            stage=stage,
            api_error=api_error_str,
        )
