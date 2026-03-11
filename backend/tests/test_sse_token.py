"""
Tests for sse_token_validator.py -- HMAC-signed SSE token validation.
"""

import base64
import hashlib
import hmac
import json
import os
import time

import pytest


def _make_token(payload: dict, secret: str = "test-secret-key-123") -> str:
    """Create a valid HMAC-signed token for testing."""
    payload_bytes = json.dumps(payload).encode("utf-8")
    payload_b64 = base64.urlsafe_b64encode(payload_bytes).decode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
    return f"{payload_b64}.{sig}"


@pytest.fixture(autouse=True)
def set_token_secret(monkeypatch):
    """Set a known secret for all tests."""
    monkeypatch.setenv("SSE_TOKEN_SECRET", "test-secret-key-123")
    monkeypatch.setenv("PYTHON_SERVICE_KEY", "test-secret-key-123")


# ─── validate_sse_token ──────────────────────────────────────────────────


def test_validate_sse_token_valid():
    """Valid HMAC-signed token returns payload dict with sub, role, email, exp."""
    from services.sse_token_validator import validate_sse_token

    payload = {
        "sub": "user-42",
        "role": "admin",
        "email": "admin@example.com",
        "exp": int(time.time()) + 300,  # 5 min in future
    }
    token = _make_token(payload)

    result = validate_sse_token(token)

    assert result is not None
    assert result["sub"] == "user-42"
    assert result["role"] == "admin"
    assert result["email"] == "admin@example.com"


def test_validate_sse_token_expired():
    """Token with past exp returns None."""
    from services.sse_token_validator import validate_sse_token

    payload = {
        "sub": "user-42",
        "role": "admin",
        "email": "admin@example.com",
        "exp": int(time.time()) - 60,  # 1 min in past
    }
    token = _make_token(payload)

    result = validate_sse_token(token)

    assert result is None


def test_validate_sse_token_tampered():
    """Token with modified payload but original signature returns None."""
    from services.sse_token_validator import validate_sse_token

    # Create valid token
    original_payload = {
        "sub": "user-42",
        "role": "viewer",
        "email": "viewer@example.com",
        "exp": int(time.time()) + 300,
    }
    token = _make_token(original_payload)

    # Tamper with payload (change role to admin)
    tampered_payload = {**original_payload, "role": "admin"}
    tampered_bytes = json.dumps(tampered_payload).encode("utf-8")
    tampered_b64 = base64.urlsafe_b64encode(tampered_bytes).decode("utf-8")

    # Keep original signature
    original_sig = token.split(".")[1]
    tampered_token = f"{tampered_b64}.{original_sig}"

    result = validate_sse_token(tampered_token)

    assert result is None


def test_validate_sse_token_malformed():
    """Non-base64 or missing dot returns None."""
    from services.sse_token_validator import validate_sse_token

    assert validate_sse_token("not-a-valid-token") is None
    assert validate_sse_token("") is None
    assert validate_sse_token("abc.def.ghi") is None  # too many dots
    assert validate_sse_token("!!!invalid-base64!!!.abcdef") is None
