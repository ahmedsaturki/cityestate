"""
Database Models Tests — اختبارات نماذج قاعدة البيانات
====================================================
Tests for User, Property, ClientRequest, MessageLog models and init_database.
"""

import pytest
from datetime import datetime, timezone


class TestUserModel:
    """Test User model operations."""

    def test_create_user(self):
        from src.database.models import User
        from src.api.deps import SessionLocal

        db = SessionLocal()
        try:
            import uuid
            user = User(
                username=f"db_test_{uuid.uuid4().hex[:8]}",
                password_hash="$2b$12$fakehashfor testing purposes only",
                full_name="DB Test User",
                role="user",
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            assert user.id is not None
            assert user.is_active is True
            assert user.created_at is not None
            # Cleanup
            db.delete(user)
            db.commit()
        finally:
            db.close()

    def test_user_to_dict(self):
        from src.database.models import User
        user = User(id=1, username="test", full_name="Test User", role="user")
        d = user.to_dict()
        assert d["username"] == "test"
        assert d["role"] == "user"


class TestPropertyModel:
    """Test Property model operations."""

    def test_create_property(self):
        from src.database.models import Property
        from src.api.deps import SessionLocal

        db = SessionLocal()
        try:
            prop = Property(
                title="Test Villa",
                description="A test property",
                price=5000000.0,
                area="المنطقة 7",
                property_type="فيلا",
                bedrooms=4,
                bathrooms=3,
                status="available",
            )
            db.add(prop)
            db.commit()
            db.refresh(prop)
            assert prop.id is not None
            assert prop.status == "available"
            assert prop.price == 5000000.0
            # Cleanup
            db.delete(prop)
            db.commit()
        finally:
            db.close()

    def test_property_to_dict(self):
        from src.database.models import Property
        prop = Property(
            id=1, title="Villa", price=3000000.0,
            area="الشريط المميز", property_type="فيلا",
            status="available"
        )
        d = prop.to_dict()
        assert d["title"] == "Villa"
        assert d["price"] == 3000000.0


class TestClientRequestModel:
    """Test ClientRequest model operations."""

    def test_create_request(self):
        from src.database.models import ClientRequest
        from src.api.deps import SessionLocal

        db = SessionLocal()
        try:
            req = ClientRequest(
                client_name="Test Client",
                phone="+201000000000",
                notes="Looking for a villa",
                property_type="فيلا",
                min_budget=3000000.0,
                max_budget=7000000.0,
                area="المنطقة 7",
                status="pending",
                priority="high",
            )
            db.add(req)
            db.commit()
            db.refresh(req)
            assert req.id is not None
            assert req.status == "pending"
            # Cleanup
            db.delete(req)
            db.commit()
        finally:
            db.close()


class TestMessageLogModel:
    """Test MessageLog model operations."""

    def test_create_message_log(self):
        from src.database.models import MessageLog
        from src.api.deps import SessionLocal

        db = SessionLocal()
        try:
            log = MessageLog(
                channel="whatsapp",
                message="Test message",
                message_type="text",
                status="sent",
            )
            db.add(log)
            db.commit()
            db.refresh(log)
            assert log.id is not None
            assert log.sent_at is not None
            # Cleanup
            db.delete(log)
            db.commit()
        finally:
            db.close()


class TestInitDatabase:
    """Test database initialization."""

    def test_init_database_creates_tables(self):
        from src.database.models import init_database
        from src.api.deps import engine
        from sqlalchemy import inspect

        # Should not raise
        init_database()

        # Verify tables exist
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        assert "users" in tables
        assert "properties" in tables
        assert "client_requests" in tables
        # MessageLog table name may be message_log or message_logs
        assert any("message" in t for t in tables)
