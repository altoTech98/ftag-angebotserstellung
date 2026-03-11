"""
Service key authentication middleware for Python backend.

Validates X-Service-Key header on all /api/* routes (except whitelist and SSE stream paths).
Extracts user context from X-User-* headers forwarded by Next.js BFF proxy.
Provides role enforcement via require_role().

Uses os.environ.get() directly (not Settings import) for self-contained testability.
"""

import os
import logging

from fastapi import HTTPException
from fastapi.responses import JSONResponse
from starlette.requests import Request

logger = logging.getLogger(__name__)

# Paths that do not require service key authentication
AUTH_WHITELIST = {
    "/health",
    "/api/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/info",
    "/",
}


async def service_key_middleware(request: Request, call_next):
    """
    Validate X-Service-Key header on all /api/* routes.

    - Whitelisted paths pass without key.
    - OPTIONS requests pass without key (CORS preflight).
    - SSE stream paths (/api/analyze/stream/) pass without key (use token auth).
    - Returns 401 JSON if key is missing or wrong.
    - Returns 500 if PYTHON_SERVICE_KEY is not configured.
    """
    path = request.url.path
    method = request.method

    # Skip auth for OPTIONS (CORS preflight)
    if method == "OPTIONS":
        return await call_next(request)

    # Skip auth for whitelisted paths
    if path in AUTH_WHITELIST:
        return await call_next(request)

    # Skip auth for static files and non-API paths
    if path.startswith("/static/") or not path.startswith("/api/"):
        return await call_next(request)

    # Skip service key for SSE stream paths (these use token auth)
    if path.startswith("/api/analyze/stream/"):
        return await call_next(request)

    # Check that service key is configured
    expected_key = os.environ.get("PYTHON_SERVICE_KEY", "")
    if not expected_key:
        logger.error("PYTHON_SERVICE_KEY is not configured")
        return JSONResponse(
            status_code=500,
            content={"detail": "Service authentication not configured"},
        )

    # Validate X-Service-Key header
    provided_key = request.headers.get("x-service-key", "")
    if not provided_key or provided_key != expected_key:
        return JSONResponse(
            status_code=401,
            content={"detail": "Invalid or missing service key"},
        )

    return await call_next(request)


def get_user_context(request: Request) -> dict:
    """
    Extract user context from X-User-* headers set by Next.js BFF proxy.

    Returns dict with user_id, role, email.
    Defaults: empty string for id/email, "viewer" for role.
    """
    return {
        "user_id": request.headers.get("x-user-id", ""),
        "role": request.headers.get("x-user-role", "viewer"),
        "email": request.headers.get("x-user-email", ""),
    }


def require_role(request: Request, *allowed_roles: str) -> dict:
    """
    Enforce role-based access. Raises HTTPException 403 if user's role
    is not in allowed_roles.

    Returns user context dict if authorized.
    """
    ctx = get_user_context(request)
    if ctx["role"] not in allowed_roles:
        raise HTTPException(
            status_code=403,
            detail=f"Role '{ctx['role']}' not authorized. Required: {', '.join(allowed_roles)}",
        )
    return ctx
