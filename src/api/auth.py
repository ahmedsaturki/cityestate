"""
Auth Module — نظام المصادقة
============================
JWT authentication with bcrypt password hashing.
Security: JWT_SECRET from env (required), bcrypt for passwords.
"""

import logging
import os
import secrets
import string
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

# Load .env BEFORE reading any env vars
_env_path = Path(__file__).parent.parent.parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path)

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.database.models import User
from src.session_vault.encryption import EncryptionManager

logger = logging.getLogger("auth")

# ---------------------------------------------------------------------------
# JWT Settings — from environment (REQUIRED)
# ---------------------------------------------------------------------------
JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    logger.warning(
        "\n"
        "JWT_SECRET is not set in the environment. "
        "Auth endpoints will return 500 until JWT_SECRET is configured.\n"
        "Generate one with:\n"
        "  python -c \"import secrets; print(secrets.token_urlsafe(64))\"\n"
        "Then add it to your .env file:\n"
        "  JWT_SECRET=<generated_value>"
    )

JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = int(os.getenv("JWT_EXPIRY_HOURS", "8"))  # Reduced from 24 to 8

security = HTTPBearer()
encryption = EncryptionManager()


def _require_jwt_secret() -> str:
    """Return JWT_SECRET or raise a 500 HTTPException if not configured."""
    if not JWT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="JWT_SECRET is not configured. Add it to the .env file.",
        )
    return JWT_SECRET


# ---------------------------------------------------------------------------
# JWT Token Operations
# ---------------------------------------------------------------------------
def create_jwt_token(user_id: int, username: str, role: str) -> str:
    """Create a JWT token for a user."""
    secret = _require_jwt_secret()
    payload = {
        "user_id": user_id,
        "username": username,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, secret, algorithm=JWT_ALGORITHM)


def decode_jwt_token(token: str) -> dict:
    """Decode and validate a JWT token."""
    secret = _require_jwt_secret()
    try:
        payload = jwt.decode(token, secret, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


# ---------------------------------------------------------------------------
# FastAPI Dependencies
# ---------------------------------------------------------------------------
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """FastAPI dependency to get the current authenticated user."""
    token = credentials.credentials
    payload = decode_jwt_token(token)
    return {
        "user_id": payload["user_id"],
        "username": payload["username"],
        "role": payload["role"],
    }


# ---------------------------------------------------------------------------
# Database Auth Helpers
# ---------------------------------------------------------------------------
def authenticate_user(db_session, username: str, password: str) -> User | None:
    """Authenticate a user by username and password."""
    user = db_session.query(User).filter(User.username == username).first()
    if not user:
        return None
    if not encryption.verify_password(password, user.password_hash):
        return None
    if not user.is_active:
        return None
    # Update last login
    user.last_login = datetime.now(timezone.utc)
    db_session.commit()
    return user


def create_user(db_session, username: str, password: str,
                full_name: str | None = None, role: str = "user") -> User:
    """Create a new user."""
    # Check if username exists
    existing = db_session.query(User).filter(User.username == username).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists"
        )

    user = User(
        username=username,
        password_hash=encryption.hash_password(password),
        full_name=full_name,
        role=role,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _generate_strong_password(length: int = 16) -> str:
    """Generate a cryptographically strong random password."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    # Ensure at least one of each category
    password = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
        secrets.choice("!@#$%^&*"),
    ]
    # Fill the rest randomly
    password += [secrets.choice(alphabet) for _ in range(length - 4)]
    # Shuffle
    secrets.SystemRandom().shuffle(password)
    return "".join(password)


def ensure_default_admin(db_session) -> str:
    """
    Ensure a default admin user exists.

    Strategy:
    1. If ADMIN_PASSWORD env var is set → use it
    2. If admin user already exists → skip
    3. Otherwise → fail with clear instructions

    Returns:
        The admin password (for console display only)
    """
    admin = db_session.query(User).filter(User.username == "admin").first()
    if admin:
        return None  # Admin already exists

    # Get password from env or fail
    admin_password = os.getenv("ADMIN_PASSWORD")
    if not admin_password:
        logger.critical(
            "\n"
            "=" * 60 + "\n"
            "[SECURITY ERROR] ADMIN_PASSWORD not set and no admin user exists!\n\n"
            "Set ADMIN_PASSWORD in your .env file:\n"
            "  ADMIN_PASSWORD=<your_secure_password>\n\n"
            "Or create admin manually:\n"
            "  python -c \"from src.api.auth import create_user; from src.api.deps import SessionLocal; create_user(SessionLocal(), 'admin', 'YOUR_PASSWORD', role='admin')\"\n"
            "=" * 60
        )
        raise RuntimeError(
            "ADMIN_PASSWORD is required when no admin user exists.\n"
            "Set it in your .env file."
        )

    create_user(
        db_session,
        username="admin",
        password=admin_password,
        full_name="System Admin",
        role="admin",
    )

    logger.info("Default admin user created (password from ADMIN_PASSWORD env var)")

    return admin_password
