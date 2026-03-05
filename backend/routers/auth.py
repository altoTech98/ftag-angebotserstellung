"""
Auth Router – Login / Me / Logout
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from services.auth_service import (
    authenticate_user,
    create_access_token,
    get_current_user,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    token: str
    email: str
    role: str


class UserInfo(BaseModel):
    email: str
    role: str


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest):
    """Authenticate with email + password, returns JWT token."""
    user = authenticate_user(req.email, req.password)
    if not user:
        logger.warning(f"[AUTH] Failed login attempt for: {req.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-Mail oder Passwort falsch",
        )
    token = create_access_token(user["email"])
    logger.info(f"[AUTH] Login successful: {user['email']}")
    return LoginResponse(token=token, email=user["email"], role=user["role"])


@router.get("/me", response_model=UserInfo)
async def get_me(user: dict = Depends(get_current_user)):
    """Verify token and return current user info."""
    return UserInfo(email=user["email"], role=user["role"])


@router.post("/logout")
async def logout():
    """Logout (no-op server-side, token invalidation happens client-side)."""
    return {"message": "Abgemeldet"}
