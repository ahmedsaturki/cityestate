"""
Dependencies — التبعيات المشتركة
=================================
Shared FastAPI dependencies for database sessions and authentication.
Supports both SQLite (development) and PostgreSQL (production).
"""

import os
from pathlib import Path

from fastapi import Depends
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from src.api.auth import get_current_user

# Database path
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{PROJECT_ROOT / 'output' / 'cityestate.db'}")

# Engine and session factory with connection pooling
_is_postgres = DATABASE_URL.startswith("postgresql")

if _is_postgres:
    # PostgreSQL connection pooling
    engine = create_engine(
        DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,
        pool_recycle=1800,
    )
else:
    # SQLite (development) - no pooling needed
    engine = create_engine(
        DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        connect_args={"timeout": 30},
    )
    # Enable WAL mode for better concurrency with SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        """Set SQLite pragmas for optimal performance and data integrity.

        Enables WAL journal mode, NORMAL synchronous mode, and foreign key
        enforcement on each new database connection.
        """
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(bind=engine)


def get_db():
    """FastAPI dependency for database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def require_auth(user: dict = Depends(get_current_user)) -> dict:
    """Dependency that requires authentication."""
    return user


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """Dependency that requires admin role."""
    if user["role"] != "admin":
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return user


def get_db_status() -> dict:
    """Check database health status."""
    try:
        from sqlalchemy import text
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            return {"status": "healthy", "url": DATABASE_URL.split("@")[-1] if "@" in DATABASE_URL else "local"}
        finally:
            db.close()
    except Exception as e:
        return {"status": "error", "error": str(e)}
