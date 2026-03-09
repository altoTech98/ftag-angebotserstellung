"""
Authentication Service – JWT + bcrypt + SQLAlchemy
Admin-User Management für Frank Türen AG

Uses database (SQLAlchemy) as primary store.
Falls back to JSON file if database is not available (graceful degradation).
"""

import json
import logging
import os
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

# Default admin credentials from environment (fallback for first-time setup only)
DEFAULT_ADMIN_EMAIL = os.environ.get("DEFAULT_ADMIN_EMAIL", "admin@franktueren.ch")
DEFAULT_ADMIN_PASSWORD = os.environ.get("DEFAULT_ADMIN_PASSWORD", "ChangeMeOnFirstLogin!")

# Flag to track if DB is available
_use_db = False


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def _normalize_email(email: str) -> str:
    return unicodedata.normalize("NFC", email).lower()


def _get_jwt_secret() -> str:
    # Prefer environment variable
    env_secret = os.environ.get("JWT_SECRET")
    if env_secret:
        return env_secret
    if JWT_SECRET_FILE.exists():
        return JWT_SECRET_FILE.read_text().strip()
    secret = secrets.token_hex(32)
    JWT_SECRET_FILE.write_text(secret)
    logger.info("[AUTH] JWT secret generated and saved")
    return secret


JWT_SECRET = _get_jwt_secret()


# ─────────────────────────────────────────────────────────────────────────────
# Database helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_db_session():
    """Get a sync database session (for auth operations)."""
    try:
        from db.engine import SyncSessionLocal
        return SyncSessionLocal()
    except Exception:
        return None


def _check_db_available():
    """Check if database is available and set flag."""
    global _use_db
    session = _get_db_session()
    if session:
        try:
            from db.models import User  # noqa: F401
            # Try a simple query
            session.execute(__import__("sqlalchemy").text("SELECT 1"))
            _use_db = True
            session.close()
        except Exception:
            _use_db = False
            session.close()


# ─────────────────────────────────────────────────────────────────────────────
# JSON fallback (backward compatibility)
# ─────────────────────────────────────────────────────────────────────────────

def _load_users_json() -> list[dict]:
    if not USERS_FILE.exists():
        return []
    try:
        return json.loads(USERS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _save_users_json(users: list[dict]) -> None:
    USERS_FILE.write_text(json.dumps(users, indent=2, ensure_ascii=False), encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# Public API (works with DB or JSON fallback)
# ─────────────────────────────────────────────────────────────────────────────

def init_admin_user() -> None:
    """Create default admin user if no users exist."""
    _check_db_available()

    if _use_db:
        from db.models import User
        session = _get_db_session()
        try:
            count = session.query(User).count()
            if count > 0:
                logger.info(f"[AUTH] {count} user(s) found in database")
                return
            admin = User(
                email=DEFAULT_ADMIN_EMAIL,
                password_hash=_hash_password(DEFAULT_ADMIN_PASSWORD),
                role="admin",
            )
            session.add(admin)
            session.commit()
            logger.info(f"[AUTH] Admin user created in DB: {DEFAULT_ADMIN_EMAIL}")
        except Exception as e:
            session.rollback()
            logger.error(f"[AUTH] DB init failed, falling back to JSON: {e}")
            _init_admin_json()
        finally:
            session.close()
    else:
        _init_admin_json()


def _init_admin_json():
    users = _load_users_json()
    if users:
        logger.info(f"[AUTH] {len(users)} user(s) found in {USERS_FILE}")
        return
    admin = {
        "email": DEFAULT_ADMIN_EMAIL,
        "password_hash": _hash_password(DEFAULT_ADMIN_PASSWORD),
        "role": "admin",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _save_users_json([admin])
    logger.info(f"[AUTH] Admin user created: {DEFAULT_ADMIN_EMAIL}")


def authenticate_user(email: str, password: str) -> dict | None:
    """Verify email + password, return user dict or None."""
    email_norm = _normalize_email(email)

    if _use_db:
        from db.models import User
        session = _get_db_session()
        try:
            user = session.query(User).filter(
                User.email == email_norm
            ).first()
            if user and _verify_password(password, user.password_hash):
                return {"email": user.email, "role": user.role}
            return None
        finally:
            session.close()

    # JSON fallback
    users = _load_users_json()
    for user in users:
        if _normalize_email(user["email"]) == email_norm:
            if _verify_password(password, user["password_hash"]):
                return user
            return None
    return None


def create_access_token(email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {
        "sub": email,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)


def verify_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if not email:
            return None
        email_norm = _normalize_email(email)

        if _use_db:
            from db.models import User
            session = _get_db_session()
            try:
                user = session.query(User).filter(
                    User.email == email_norm
                ).first()
                if user:
                    return {"email": user.email, "role": user.role}
                return None
            finally:
                session.close()

        # JSON fallback
        users = _load_users_json()
        for user in users:
            if _normalize_email(user["email"]) == email_norm:
                return {"email": user["email"], "role": user["role"]}
        return None
    except JWTError:
        return None


def list_users() -> list[dict]:
    if _use_db:
        from db.models import User
        session = _get_db_session()
        try:
            users = session.query(User).all()
            return [
                {"email": u.email, "role": u.role, "created_at": u.created_at.isoformat() if u.created_at else ""}
                for u in users
            ]
        finally:
            session.close()

    # JSON fallback
    users = _load_users_json()
    return [
        {"email": u["email"], "role": u.get("role", "user"), "created_at": u.get("created_at", "")}
        for u in users
    ]


def add_user(email: str, password: str, role: str = "user") -> dict:
    if role not in ("admin", "user"):
        raise ValueError(f"Ungueltige Rolle: {role}")
    email_norm = _normalize_email(email)

    if _use_db:
        from db.models import User
        session = _get_db_session()
        try:
            existing = session.query(User).filter(User.email == email_norm).first()
            if existing:
                raise ValueError(f"Benutzer '{email}' existiert bereits")
            new_user = User(email=email_norm, password_hash=_hash_password(password), role=role)
            session.add(new_user)
            session.commit()
            logger.info(f"[AUTH] User created: {email} (role={role})")
            return {"email": new_user.email, "role": new_user.role, "created_at": new_user.created_at.isoformat()}
        except ValueError:
            session.rollback()
            raise
        except Exception as e:
            session.rollback()
            raise ValueError(f"Fehler beim Erstellen: {e}")
        finally:
            session.close()

    # JSON fallback
    users = _load_users_json()
    for u in users:
        if _normalize_email(u["email"]) == email_norm:
            raise ValueError(f"Benutzer '{email}' existiert bereits")
    new_user = {
        "email": email,
        "password_hash": _hash_password(password),
        "role": role,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    users.append(new_user)
    _save_users_json(users)
    logger.info(f"[AUTH] User created: {email} (role={role})")
    return {"email": email, "role": role, "created_at": new_user["created_at"]}


def delete_user(email: str) -> bool:
    email_norm = _normalize_email(email)

    if _use_db:
        from db.models import User
        session = _get_db_session()
        try:
            user = session.query(User).filter(User.email == email_norm).first()
            if not user:
                raise ValueError(f"Benutzer '{email}' nicht gefunden")
            if user.role == "admin":
                admin_count = session.query(User).filter(User.role == "admin").count()
                if admin_count <= 1:
                    raise ValueError("Letzter Admin kann nicht geloescht werden")
            session.delete(user)
            session.commit()
            logger.info(f"[AUTH] User deleted: {email}")
            return True
        except ValueError:
            session.rollback()
            raise
        except Exception as e:
            session.rollback()
            raise ValueError(f"Fehler beim Loeschen: {e}")
        finally:
            session.close()

    # JSON fallback
    users = _load_users_json()
    target_idx = None
    for i, u in enumerate(users):
        if _normalize_email(u["email"]) == email_norm:
            target_idx = i
            break
    if target_idx is None:
        raise ValueError(f"Benutzer '{email}' nicht gefunden")
    if users[target_idx].get("role") == "admin":
        admin_count = sum(1 for u in users if u.get("role") == "admin")
        if admin_count <= 1:
            raise ValueError("Letzter Admin kann nicht geloescht werden")
    removed = users.pop(target_idx)
    _save_users_json(users)
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
