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
