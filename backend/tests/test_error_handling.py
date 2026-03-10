"""
Tests for fail-fast error handling - AIServiceError and raise_ai_error helper.
"""

import pytest

from v2.exceptions import PipelineError, AIServiceError, raise_ai_error


# ---------------------------------------------------------------------------
# Mock exception classes that mimic anthropic SDK exceptions
# ---------------------------------------------------------------------------


class APIConnectionError(Exception):
    """Mock anthropic.APIConnectionError."""
    pass


class RateLimitError(Exception):
    """Mock anthropic.RateLimitError."""
    pass


class APIStatusError(Exception):
    """Mock anthropic.APIStatusError."""
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.status_code = status_code


# ---------------------------------------------------------------------------
# Tests: AIServiceError
# ---------------------------------------------------------------------------


class TestAIServiceError:
    def test_creation_with_stage_context(self):
        """AIServiceError carries code, German message, and stage details."""
        err = AIServiceError(
            message="KI-Service nicht erreichbar. Bitte Internetverbindung pruefen.",
            stage="matching",
            api_error="Connection refused",
        )

        assert err.code == "AI_SERVICE_ERROR"
        assert err.message == "KI-Service nicht erreichbar. Bitte Internetverbindung pruefen."
        assert err.details["stage"] == "matching"
        assert err.details["api_error"] == "Connection refused"

    def test_is_subclass_of_pipeline_error(self):
        """AIServiceError is a PipelineError."""
        err = AIServiceError(message="test", stage="extraction")
        assert isinstance(err, PipelineError)

    def test_str_representation(self):
        """AIServiceError string shows message."""
        err = AIServiceError(message="KI-Service Fehler", stage="validation")
        assert "KI-Service Fehler" in str(err)


# ---------------------------------------------------------------------------
# Tests: raise_ai_error
# ---------------------------------------------------------------------------


class TestRaiseAiError:
    def test_api_connection_error(self):
        """APIConnectionError maps to 'KI-Service nicht erreichbar'."""
        exc = APIConnectionError("Connection refused")

        with pytest.raises(AIServiceError) as exc_info:
            raise_ai_error(exc, stage="matching")

        assert "nicht erreichbar" in exc_info.value.message
        assert "Bitte Internetverbindung pruefen" in exc_info.value.message
        assert exc_info.value.details["stage"] == "matching"

    def test_rate_limit_error(self):
        """RateLimitError maps to 'KI-Service ueberlastet'."""
        exc = RateLimitError("Rate limit exceeded")

        with pytest.raises(AIServiceError) as exc_info:
            raise_ai_error(exc, stage="validation")

        assert "ueberlastet" in exc_info.value.message
        assert "einigen Minuten" in exc_info.value.message

    def test_api_status_error(self):
        """APIStatusError maps to 'KI-Service Fehler' with status code."""
        exc = APIStatusError("Internal server error", status_code=500)

        with pytest.raises(AIServiceError) as exc_info:
            raise_ai_error(exc, stage="extraction")

        assert "Fehler (500)" in exc_info.value.message
        assert "spaeter erneut versuchen" in exc_info.value.message

    def test_generic_exception(self):
        """Generic exceptions map to 'KI-Service nicht verfuegbar'."""
        exc = ValueError("something went wrong")

        with pytest.raises(AIServiceError) as exc_info:
            raise_ai_error(exc, stage="gap_analyse")

        assert "nicht verfuegbar" in exc_info.value.message
        assert "something went wrong" in exc_info.value.message

    def test_details_include_stage_and_api_error(self):
        """Details dict always includes stage and api_error."""
        exc = APIConnectionError("timeout")

        with pytest.raises(AIServiceError) as exc_info:
            raise_ai_error(exc, stage="matching")

        details = exc_info.value.details
        assert "stage" in details
        assert "api_error" in details
        assert details["stage"] == "matching"
        assert "timeout" in details["api_error"]

    def test_german_messages_correct(self):
        """All German messages use correct phrasing."""
        test_cases = [
            (APIConnectionError("err"), "nicht erreichbar"),
            (RateLimitError("err"), "ueberlastet"),
            (APIStatusError("err", 429), "Fehler (429)"),
            (ValueError("err"), "nicht verfuegbar"),
        ]
        for exc, expected_fragment in test_cases:
            with pytest.raises(AIServiceError) as exc_info:
                raise_ai_error(exc, stage="test")
            assert expected_fragment in exc_info.value.message, (
                f"Expected '{expected_fragment}' in message for {type(exc).__name__}"
            )
