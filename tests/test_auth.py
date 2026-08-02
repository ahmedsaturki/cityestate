"""
Auth Module Tests — اختبارات نظام المصادقة
==========================================
Tests for JWT tokens, password hashing, and authentication logic.
"""

import os
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock


class TestJWTTokenOperations:
    """Test JWT token creation and validation."""

    def test_create_jwt_token(self):
        from src.api.auth import create_jwt_token
        token = create_jwt_token(user_id=1, username="testuser", role="admin")
        assert isinstance(token, str)
        assert len(token) > 20

    def test_decode_jwt_token(self):
        from src.api.auth import create_jwt_token, decode_jwt_token
        token = create_jwt_token(user_id=42, username="testuser", role="user")
        payload = decode_jwt_token(token)
        assert payload["user_id"] == 42
        assert payload["username"] == "testuser"
        assert payload["role"] == "user"

    def test_decode_expired_token(self):
        from src.api.auth import create_jwt_token, decode_jwt_token, JWT_SECRET, JWT_ALGORITHM
        import jwt as pyjwt

        # Create an already-expired token
        payload = {
            "user_id": 1,
            "username": "test",
            "role": "user",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
        }
        expired_token = pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

        with pytest.raises(Exception) as exc_info:
            decode_jwt_token(expired_token)
        assert "expired" in str(exc_info.value.detail).lower() or "401" in str(exc_info.value)

    def test_decode_invalid_token(self):
        from src.api.auth import decode_jwt_token
        with pytest.raises(Exception):
            decode_jwt_token("invalid.token.here")


class TestPasswordHashing:
    """Test bcrypt password hashing."""

    def test_hash_password(self):
        from src.session_vault.encryption import EncryptionManager
        em = EncryptionManager()
        hashed = em.hash_password("test_password_123")
        assert hashed.startswith("$2b$")
        assert len(hashed) > 50

    def test_verify_correct_password(self):
        from src.session_vault.encryption import EncryptionManager
        em = EncryptionManager()
        password = "MyS3cur3P@ssw0rd!"
        hashed = em.hash_password(password)
        assert em.verify_password(password, hashed) is True

    def test_verify_wrong_password(self):
        from src.session_vault.encryption import EncryptionManager
        em = EncryptionManager()
        hashed = em.hash_password("correct_password")
        assert em.verify_password("wrong_password", hashed) is False

    def test_verify_empty_password(self):
        from src.session_vault.encryption import EncryptionManager
        em = EncryptionManager()
        hashed = em.hash_password("password")
        assert em.verify_password("", hashed) is False


class TestUserCreation:
    """Test user creation in database."""

    def test_create_user(self):
        from src.database.models import User
        from src.api.deps import SessionLocal
        from src.api.auth import create_user

        db = SessionLocal()
        try:
            # Use a unique username
            import uuid
            unique_user = f"testuser_{uuid.uuid4().hex[:8]}"
            user = create_user(db, unique_user, "TestPass123!", full_name="Test User", role="user")
            assert user.id is not None
            assert user.username == unique_user
            assert user.role == "user"
            assert user.is_active is True
            # Cleanup
            db.delete(user)
            db.commit()
        finally:
            db.close()

    def test_create_duplicate_user_raises(self):
        from src.database.models import User
        from src.api.deps import SessionLocal
        from src.api.auth import create_user
        from fastapi import HTTPException

        db = SessionLocal()
        try:
            import uuid
            unique_user = f"dupuser_{uuid.uuid4().hex[:8]}"
            create_user(db, unique_user, "Pass123!")
            with pytest.raises(HTTPException) as exc_info:
                create_user(db, unique_user, "Pass123!")
            assert exc_info.value.status_code == 409
            # Cleanup
            user = db.query(User).filter(User.username == unique_user).first()
            if user:
                db.delete(user)
                db.commit()
        finally:
            db.close()


class TestEnsureDefaultAdmin:
    """Test admin user initialization."""

    def test_admin_exists_returns_none(self):
        from src.api.deps import SessionLocal
        from src.api.auth import ensure_default_admin

        db = SessionLocal()
        try:
            result = ensure_default_admin(db)
            # If admin exists, should return None
            assert result is None
        finally:
            db.close()
