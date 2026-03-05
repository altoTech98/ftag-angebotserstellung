"""
Authentication Service – JWT + bcrypt
Admin-User Management für Frank Türen AG
"""

import json
import logging
import secrets
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from jose import JWTError, jwt
import bcrypt

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
USERS_FILE = DATA_DIR / "users.json"
JWT_SECRET_FILE = DATA_DIR / ".jwt_secret"

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

security = HTTPBearer(auto_error=False)

# Default admin credentials (user should change password after first login)
DEFAULT_ADMIN_EMAIL = "admin@franktueren.ch"
DEFAULT_ADMIN_PASSWORD = "Frank2024!"


def _hash_password(password: str) -> str:
    """Hash password with bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, password_hash: str) -> bool:
    """Verify password against bcrypt hash."""
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def _normalize_email(email: str) -> str:
    """Normalize email for consistent comparison (NFC + lowercase)."""
    return unicodedata.normalize("NFC", email).lower()


def _get_jwt_secret() -> str:
    """Load or generate JWT secret key."""
    if JWT_SECRET_FILE.exists():
        return JWT_SECRET_FILE.read_text().strip()
    secret = secrets.token_hex(32)
    JWT_SECRET_FILE.write_text(secret)
    logger.info("[AUTH] JWT secret generated and saved")
    return secret


JWT_SECRET = _get_jwt_secret()


def _load_users() -> list[dict]:
    """Load users from JSON file."""
    if not USERS_FILE.exists():
        return []
    try:
        return json.loads(USERS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _save_users(users: list[dict]) -> None:
    """Save users to JSON file."""
    USERS_FILE.write_text(json.dumps(users, indent=2, ensure_ascii=False), encoding="utf-8")


def init_admin_user() -> None:
    """Create default admin user if no users exist."""
    users = _load_users()
    if users:
        logger.info(f"[AUTH] {len(users)} user(s) found in {USERS_FILE}")
        return

    admin = {
        "email": DEFAULT_ADMIN_EMAIL,
        "password_hash": _hash_password(DEFAULT_ADMIN_PASSWORD),
        "role": "admin",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _save_users([admin])
    logger.info(f"[AUTH] Admin user created: {DEFAULT_ADMIN_EMAIL}")


def authenticate_user(email: str, password: str) -> dict | None:
    """Verify email + password, return user dict or None."""
    users = _load_users()
    email_norm = _normalize_email(email)
    for user in users:
        if _normalize_email(user["email"]) == email_norm:
            if _verify_password(password, user["password_hash"]):
                return user
            return None
    return None


def create_access_token(email: str) -> str:
    """Create JWT token with expiration."""
    expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {
        "sub": email,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)


def verify_token(token: str) -> dict | None:
    """Verify JWT token, return payload or None."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if not email:
            return None
        # Check user still exists
        users = _load_users()
        email_norm = _normalize_email(email)
        for user in users:
            if _normalize_email(user["email"]) == email_norm:
                return {"email": user["email"], "role": user["role"]}
        return None
    except JWTError:
        return None


def list_users() -> list[dict]:
    """List all users (without password hashes)."""
    users = _load_users()
    return [
        {
            "email": u["email"],
            "role": u.get("role", "user"),
            "created_at": u.get("created_at", ""),
        }
        for u in users
    ]


def add_user(email: str, password: str, role: str = "user") -> dict:
    """Add a new user. Raises ValueError if duplicate."""
    users = _load_users()
    email_norm = _normalize_email(email)
    for u in users:
        if _normalize_email(u["email"]) == email_norm:
            raise ValueError(f"Benutzer '{email}' existiert bereits")
    if role not in ("admin", "user"):
        raise ValueError(f"Ungueltige Rolle: {role}")
    new_user = {
        "email": email,
        "password_hash": _hash_password(password),
        "role": role,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    users.append(new_user)
    _save_users(users)
    logger.info(f"[AUTH] User created: {email} (role={role})")
    return {"email": email, "role": role, "created_at": new_user["created_at"]}


def delete_user(email: str) -> bool:
    """Delete a user. Protects last admin. Raises ValueError on error."""
    users = _load_users()
    email_norm = _normalize_email(email)
    target_idx = None
    for i, u in enumerate(users):
        if _normalize_email(u["email"]) == email_norm:
            target_idx = i
            break
    if target_idx is None:
        raise ValueError(f"Benutzer '{email}' nicht gefunden")
    # Protect last admin
    if users[target_idx].get("role") == "admin":
        admin_count = sum(1 for u in users if u.get("role") == "admin")
        if admin_count <= 1:
            raise ValueError("Letzter Admin kann nicht geloescht werden")
    removed = users.pop(target_idx)
    _save_users(users)
    logger.info(f"[AUTH] User deleted: {removed['email']}")
    return True


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """FastAPI dependency: extract and verify user from Bearer token."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nicht authentifiziert",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = verify_token(credentials.credentials)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token ungueltig oder abgelaufen",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
