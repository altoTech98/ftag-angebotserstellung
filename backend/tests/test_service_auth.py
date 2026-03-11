"""
Tests for service_auth.py -- service key middleware, user context extraction, role enforcement.
"""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock
from starlette.requests import Request
from starlette.datastructures import Headers
from fastapi import HTTPException


def _make_request(path: str, method: str = "GET", headers: dict = None) -> MagicMock:
    """Create a mock Request with the given path, method, and headers."""
    req = MagicMock(spec=Request)
    req.url = MagicMock()
    req.url.path = path
    req.method = method
    req.headers = Headers(headers or {})
    return req


@pytest.fixture(autouse=True)
def set_service_key(monkeypatch):
    """Set a known service key for all tests."""
    monkeypatch.setenv("PYTHON_SERVICE_KEY", "test-secret-key-123")


# ─── service_key_middleware ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_service_key_middleware_rejects_missing_key():
    """Request to /api/analyze without X-Service-Key returns 401."""
    from services.service_auth import service_key_middleware

    request = _make_request("/api/analyze")
    call_next = AsyncMock()

    response = await service_key_middleware(request, call_next)

    call_next.assert_not_called()
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_service_key_middleware_rejects_wrong_key():
    """Request with wrong key returns 401."""
    from services.service_auth import service_key_middleware

    request = _make_request("/api/analyze", headers={"x-service-key": "wrong-key"})
    call_next = AsyncMock()

    response = await service_key_middleware(request, call_next)

    call_next.assert_not_called()
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_service_key_middleware_accepts_valid_key():
    """Request with correct key passes through (call_next called)."""
    from services.service_auth import service_key_middleware

    request = _make_request(
        "/api/analyze", headers={"x-service-key": "test-secret-key-123"}
    )
    call_next = AsyncMock(return_value=MagicMock(status_code=200))

    response = await service_key_middleware(request, call_next)

    call_next.assert_called_once_with(request)


@pytest.mark.asyncio
async def test_service_key_middleware_skips_whitelist():
    """/health, /docs, /openapi.json pass without key."""
    from services.service_auth import service_key_middleware

    whitelist_paths = ["/health", "/docs", "/openapi.json", "/redoc", "/info", "/", "/api/health"]
    call_next = AsyncMock(return_value=MagicMock(status_code=200))

    for path in whitelist_paths:
        call_next.reset_mock()
        request = _make_request(path)
        await service_key_middleware(request, call_next)
        call_next.assert_called_once_with(request), f"Expected call_next for {path}"


@pytest.mark.asyncio
async def test_service_key_middleware_skips_options():
    """OPTIONS requests pass without key."""
    from services.service_auth import service_key_middleware

    request = _make_request("/api/analyze", method="OPTIONS")
    call_next = AsyncMock(return_value=MagicMock(status_code=200))

    await service_key_middleware(request, call_next)

    call_next.assert_called_once_with(request)


@pytest.mark.asyncio
async def test_service_key_middleware_skips_sse_stream():
    """/api/analyze/stream/* paths pass without service key (uses token auth)."""
    from services.service_auth import service_key_middleware

    request = _make_request("/api/analyze/stream/some-job-id")
    call_next = AsyncMock(return_value=MagicMock(status_code=200))

    await service_key_middleware(request, call_next)

    call_next.assert_called_once_with(request)


@pytest.mark.asyncio
async def test_service_key_middleware_rejects_unconfigured(monkeypatch):
    """Returns 500 if PYTHON_SERVICE_KEY env var is empty."""
    from services.service_auth import service_key_middleware

    monkeypatch.setenv("PYTHON_SERVICE_KEY", "")
    request = _make_request(
        "/api/analyze", headers={"x-service-key": "anything"}
    )
    call_next = AsyncMock()

    response = await service_key_middleware(request, call_next)

    call_next.assert_not_called()
    assert response.status_code == 500


# ─── get_user_context ─────────────────────────────────────────────────────


def test_get_user_context_extracts_headers():
    """Extracts X-User-Id, X-User-Role, X-User-Email from request headers."""
    from services.service_auth import get_user_context

    request = _make_request(
        "/api/analyze",
        headers={
            "x-user-id": "user-42",
            "x-user-role": "admin",
            "x-user-email": "admin@example.com",
        },
    )

    ctx = get_user_context(request)
    assert ctx["user_id"] == "user-42"
    assert ctx["role"] == "admin"
    assert ctx["email"] == "admin@example.com"


def test_get_user_context_defaults():
    """Missing headers default to empty string for id/email and 'viewer' for role."""
    from services.service_auth import get_user_context

    request = _make_request("/api/analyze")

    ctx = get_user_context(request)
    assert ctx["user_id"] == ""
    assert ctx["role"] == "viewer"
    assert ctx["email"] == ""


# ─── require_role ─────────────────────────────────────────────────────────


def test_require_role_allows():
    """require_role(request, 'admin', 'manager') passes when X-User-Role is 'admin'."""
    from services.service_auth import require_role

    request = _make_request(
        "/api/analyze",
        headers={"x-user-role": "admin"},
    )

    ctx = require_role(request, "admin", "manager")
    assert ctx["role"] == "admin"


def test_require_role_denies():
    """require_role(request, 'admin') raises HTTPException 403 when role is 'viewer'."""
    from services.service_auth import require_role

    request = _make_request(
        "/api/analyze",
        headers={"x-user-role": "viewer"},
    )

    with pytest.raises(HTTPException) as exc_info:
        require_role(request, "admin")

    assert exc_info.value.status_code == 403
