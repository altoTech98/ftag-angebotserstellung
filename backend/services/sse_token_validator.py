"""
SSE token validator -- validates HMAC-signed tokens for SSE stream endpoints.

Tokens are issued by Next.js BFF (Plan 02) and validated here.
Format: base64url(payload).hmac_sha256_hex(payload)

Uses os.environ.get() directly (not Settings import) for self-contained testability.
"""

import base64
import hashlib
import hmac
import json
import logging
import os
import time

logger = logging.getLogger(__name__)


def validate_sse_token(token: str) -> dict | None:
    """
    Validate an HMAC-SHA256 signed SSE token.

    Token format: base64url(JSON payload).hex(HMAC-SHA256 signature)

    Returns payload dict on success, None on any failure (expired, tampered, malformed).
    """
    if not token:
        return None

    # Split token into payload and signature parts
    parts = token.split(".")
    if len(parts) != 2:
        return None

    payload_b64, provided_sig = parts

    # Get the secret (SSE_TOKEN_SECRET with PYTHON_SERVICE_KEY fallback)
    secret = os.environ.get(
        "SSE_TOKEN_SECRET",
        os.environ.get("PYTHON_SERVICE_KEY", ""),
    )
    if not secret:
        logger.error("SSE_TOKEN_SECRET is not configured")
        return None

    # Decode payload
    try:
        # Add padding if needed for base64url
        padded = payload_b64 + "=" * (4 - len(payload_b64) % 4) if len(payload_b64) % 4 else payload_b64
        payload_bytes = base64.urlsafe_b64decode(padded)
    except Exception:
        return None

    # Verify HMAC signature
    expected_sig = hmac.new(
        secret.encode("utf-8"),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected_sig, provided_sig):
        return None

    # Parse payload JSON
    try:
        payload = json.loads(payload_bytes)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None

    # Check expiry
    exp = payload.get("exp")
    if exp is None or exp < time.time():
        return None

    return payload
