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


# ─── SSE stream endpoint integration tests ───────────────────────────────


# ─── Cross-system compatibility tests ────────────────────────────────────


def test_validate_nextjs_format_token():
    """Token minted using Next.js logic (base64url payload + hex HMAC) is accepted by Python."""
    from services.sse_token_validator import validate_sse_token

    secret = "test-secret-key-123"

    # Step 1: Create payload (same shape as Next.js route produces)
    payload = {
        "sub": "user-nextjs-1",
        "role": "analyst",
        "email": "analyst@example.com",
        "exp": int(time.time()) + 600,
        "iat": int(time.time()),
    }

    # Step 2: JSON-encode to bytes (equivalent to JSON.stringify in Node.js)
    payload_json_bytes = json.dumps(payload).encode("utf-8")

    # Step 3: base64url-encode with padding stripped (matches Buffer.toString('base64url'))
    payload_b64 = base64.urlsafe_b64encode(payload_json_bytes).rstrip(b"=").decode("utf-8")

    # Step 4: HMAC-SHA256 of raw JSON bytes, hex-encoded (matches .digest('hex'))
    hex_signature = hmac.new(
        secret.encode("utf-8"),
        payload_json_bytes,
        hashlib.sha256,
    ).hexdigest()

    # Step 5: Construct token in Next.js format
    token = f"{payload_b64}.{hex_signature}"

    # Step 6: Validate with Python validator
    result = validate_sse_token(token)

    assert result is not None, "Python validator must accept Next.js format token"
    assert result["sub"] == "user-nextjs-1"
    assert result["role"] == "analyst"
    assert result["email"] == "analyst@example.com"


def test_validate_rejects_base64url_signature():
    """Token with OLD base64url-encoded signature is rejected (regression test)."""
    from services.sse_token_validator import validate_sse_token

    secret = "test-secret-key-123"

    payload = {
        "sub": "user-old-1",
        "role": "viewer",
        "email": "viewer@example.com",
        "exp": int(time.time()) + 600,
        "iat": int(time.time()),
    }

    payload_json_bytes = json.dumps(payload).encode("utf-8")
    payload_b64 = base64.urlsafe_b64encode(payload_json_bytes).rstrip(b"=").decode("utf-8")

    # Create signature using OLD base64url encoding (NOT hex)
    raw_sig = hmac.new(
        secret.encode("utf-8"),
        payload_json_bytes,
        hashlib.sha256,
    ).digest()
    base64url_signature = base64.urlsafe_b64encode(raw_sig).rstrip(b"=").decode("utf-8")

    token = f"{payload_b64}.{base64url_signature}"

    result = validate_sse_token(token)

    assert result is None, "Python validator must reject base64url-encoded signatures"


# ─── SSE stream endpoint integration tests ───────────────────────────────


def test_sse_stream_rejects_missing_token():
    """GET /api/analyze/stream/test-job without ?token= returns 401."""
    from fastapi.testclient import TestClient
    from main import app

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/api/analyze/stream/test-job")

    assert response.status_code == 401
    assert "SSE token required" in response.json().get("detail", "")


def test_sse_stream_rejects_invalid_token():
    """GET /api/analyze/stream/test-job?token=garbage returns 401."""
    from fastapi.testclient import TestClient
    from main import app

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/api/analyze/stream/test-job?token=garbage")

    assert response.status_code == 401
    assert "Invalid or expired SSE token" in response.json().get("detail", "")
