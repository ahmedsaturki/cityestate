"""
Auth Routes — مسارات المصادقة
==============================
Login, register, and user management endpoints.
"""

import hmac
import os
import time
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.api.auth import (
    authenticate_user,
    create_jwt_token,
    create_user,
)
from src.api.deps import get_db, require_admin, require_auth
from src.api.models import LoginRequest, TokenResponse, UserCreate, UserResponse
from src.database.models import User

router = APIRouter(prefix="/auth", tags=["Authentication"])

# In-memory rate limiter for login attempts
_login_attempts: dict[str, list[float]] = defaultdict(list)
_MAX_ATTEMPTS = 5
_WINDOW_SECONDS = 300  # 5 minutes
_LOCKOUT_SECONDS = 900  # 15 minutes


def _check_rate_limit(ip: str) -> tuple[bool, float]:
    """Check if IP is rate-limited. Returns (allowed, seconds_remaining)."""
    now = time.time()
    # Purge old entries
    _login_attempts[ip] = [t for t in _login_attempts[ip] if now - t < _WINDOW_SECONDS]

    if len(_login_attempts[ip]) >= _MAX_ATTEMPTS:
        oldest = _login_attempts[ip][0]
        remaining = _LOCKOUT_SECONDS - (now - oldest)
        if remaining > 0:
            return False, remaining
        # Window expired, reset
        _login_attempts[ip].clear()

    return True, 0


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, req: Request, db: Session = Depends(get_db)) -> dict:
    """Authenticate user and return JWT token. Rate-limited to 5 attempts per 5 min."""
    client_ip = req.client.host if req.client else "unknown"

    allowed, remaining = _check_rate_limit(client_ip)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many login attempts. Try again in {int(remaining)}s"
        )

    user = authenticate_user(db, request.username, request.password)
    if not user:
        _login_attempts[client_ip].append(time.time())
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    # Successful login — clear attempts
    _login_attempts[client_ip].clear()

    token = create_jwt_token(user.id, user.username, user.role)
    response = JSONResponse(content={
        "access_token": token,
        "token_type": "bearer",
        "user": user.to_dict(),
    })
    response.set_cookie(
        key="cityestate_token",
        value=token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=8 * 3600,
        path="/",
    )
    return response


@router.post("/register", response_model=UserResponse)
def register(request: UserCreate, user: dict = Depends(require_admin), db: Session = Depends(get_db)) -> dict:
    """Register a new user (admin only)."""
    user = create_user(
        db,
        username=request.username,
        password=request.password,
        full_name=request.full_name,
        role=request.role,
    )
    return UserResponse(**user.to_dict())


@router.get("/me", response_model=UserResponse)
def get_me(user: dict = Depends(require_auth), db: Session = Depends(get_db)) -> dict:
    """Get current user profile."""
    from src.database.models import User
    db_user = db.query(User).filter(User.id == user["user_id"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(**db_user.to_dict())


@router.get("/users", response_model=list[UserResponse])
def list_users(
    limit: int = Query(100, le=500),
    offset: int = 0,
    user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[dict]:
    """List all users (admin only) — paginated."""
    from src.database.models import User
    users = db.query(User).order_by(User.id.desc()).offset(offset).limit(limit).all()
    return [UserResponse(**u.to_dict()) for u in users]


# ---------------------------------------------------------------------------
# Extension Token — Shared-secret handshake for Chrome Extension
# ---------------------------------------------------------------------------
class ExtensionTokenRequest(BaseModel):
    """Payload for the extension token handshake."""
    extension_secret: str = Field(..., min_length=16)
    profile_id: str | None = None


@router.post("/extension-token")
def extension_token(request: ExtensionTokenRequest, req: Request, db: Session = Depends(get_db)) -> dict:
    """Issue a JWT for the Chrome Extension.

    Authentication: caller must know `EXTENSION_SHARED_SECRET`, sent as
    a JSON field in the body. The previous implementation authenticated
    by reading `ADMIN_PASSWORD` from the environment, which made the
    endpoint an admin-JWT mint for anyone who could hit the URL. That
    backdoor is now closed.

    The issued token uses the `extension` role, which has access to the
    WebSocket bridge and read-only data routes, but cannot hit admin
    endpoints (user management, secret rotation, etc.).

    To configure:
        1. Generate a long random secret (>= 32 chars).
        2. Set `EXTENSION_SHARED_SECRET=<secret>` in the server's `.env`.
        3. In the Chrome extension popup, paste the same secret. It is
           stored in `chrome.storage.local` and never sent in plain HTTP
           again (only via HTTPS in production).
    """
    from fastapi import HTTPException
    from fastapi import status as http_status

    expected = os.getenv("EXTENSION_SHARED_SECRET", "").strip()
    if not expected:
        raise HTTPException(
            status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="EXTENSION_SHARED_SECRET not configured on the server. "
                   "Extension auto-auth is disabled.",
        )
    # Constant-time comparison to avoid timing attacks.
    if not hmac.compare_digest(request.extension_secret, expected):
        raise HTTPException(
            status_code=http_status.HTTP_401_UNAUTHORIZED,
            detail="Invalid extension secret.",
        )

    user = db.query(User).filter(User.role == "extension").first()
    if user is None:
        # Provision a dedicated extension user the first time the
        # extension connects. It has a randomly generated unusable
        # password hash (the extension never logs in via /auth/login).
        import secrets as _secrets
        from datetime import datetime, timezone

        from src.session_vault.encryption import EncryptionManager
        random_password = _secrets.token_urlsafe(48)
        user = User(
            username="extension",
            password_hash=EncryptionManager.hash_password(random_password),
            full_name="Chrome Extension (auto-provisioned)",
            role="extension",
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    token = create_jwt_token(user.id, user.username, user.role)
    response = JSONResponse(content={
        "access_token": token,
        "token_type": "bearer",
        "expires_in": 8 * 3600,
        "server_url": f"ws://{req.headers.get('host', 'localhost:8000')}/ws/bridge",
        "profile_id": request.profile_id or f"ext_{user.id}",
    })
    response.set_cookie(
        key="cityestate_token",
        value=token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=8 * 3600,
        path="/",
    )
    return response
