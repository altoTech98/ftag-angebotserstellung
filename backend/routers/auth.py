"""
Auth Router – Login / Me / Logout / User Management
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from services.auth_service import (
    authenticate_user,
    create_access_token,
    get_current_user,
    list_users,
    add_user,
    delete_user,
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


class CreateUserRequest(BaseModel):
    email: str
    password: str
    role: str = "user"


class UserListItem(BaseModel):
    email: str
    role: str
    created_at: str = ""


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


# ─────────────────────────────────────────────────────────────────────
# USER MANAGEMENT (admin only)
# ─────────────────────────────────────────────────────────────────────

def _require_admin(user: dict = Depends(get_current_user)) -> dict:
    """Dependency: require admin role."""
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Nur Admins duerfen Benutzer verwalten",
        )
    return user


@router.get("/users", response_model=List[UserListItem])
async def get_users(admin: dict = Depends(_require_admin)):
    """List all users (admin only)."""
    return list_users()


@router.post("/users", response_model=UserListItem, status_code=201)
async def create_user(req: CreateUserRequest, admin: dict = Depends(_require_admin)):
    """Create a new user (admin only)."""
    try:
        return add_user(req.email, req.password, req.role)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/users/{email}")
async def remove_user(email: str, admin: dict = Depends(_require_admin)):
    """Delete a user (admin only). Cannot delete last admin."""
    try:
        delete_user(email)
        return {"message": f"Benutzer '{email}' geloescht"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
