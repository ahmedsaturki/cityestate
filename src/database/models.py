"""
Database Models — جداول قاعدة البيانات
=======================================
Extended models for the CityEstate Master OS.
"""

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Session, relationship, sessionmaker

# Reuse the existing Base from ingester
from src.database.ingester import Base


# ---------------------------------------------------------------------------
# User Model — المستخدمين
# ---------------------------------------------------------------------------
class User(Base):
    """User accounts for CRM authentication."""

    __tablename__ = "users"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    username: str = Column(String(128), unique=True, nullable=False)
    password_hash: str = Column(String(256), nullable=False)
    full_name: str = Column(String(256), nullable=True)
    role: str = Column(String(32), nullable=False, default="user")  # admin, user, viewer
    is_active: bool = Column(Boolean, default=True)
    created_at: datetime = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_login: datetime = Column(DateTime, nullable=True)

    def to_dict(self) -> dict:
        """Serialize the user to a plain dictionary for API responses."""
        return {
            "id": self.id,
            "username": self.username,
            "full_name": self.full_name,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
        }


# ---------------------------------------------------------------------------
# Property Model — العقارات (المخزون)
# ---------------------------------------------------------------------------
class Property(Base):
    """Property inventory — primary and resale listings."""

    __tablename__ = "properties"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    title: str = Column(Text, nullable=False)
    description: str = Column(Text, nullable=True)

    # Property classification
    property_type: str = Column(String(32), nullable=False, default="primary")
    # primary = off-plan from developer, resale = secondary market

    status: str = Column(String(32), nullable=False, default="available")
    # available, sold, reserved, pending

    # Location
    area: str = Column(String(128), nullable=False)
    city: str = Column(String(64), nullable=True, default="Cairo")
    district: str = Column(String(128), nullable=True)

    # Pricing
    price: float = Column(Float, nullable=False)
    price_currency: str = Column(String(8), nullable=False, default="EGP")

    # Property details
    bedrooms: int = Column(Integer, nullable=True)
    bathrooms: int = Column(Integer, nullable=True)
    area_sqm: float = Column(Float, nullable=True)

    # Developer info (for primary/off-plan)
    developer: str = Column(String(256), nullable=True)
    project_name: str = Column(String(256), nullable=True)
    delivery_date: str = Column(String(64), nullable=True)

    # Payment plan (for primary/off-plan)
    down_payment: float = Column(Float, nullable=True)
    monthly_installment: float = Column(Float, nullable=True)
    installment_years: int = Column(Integer, nullable=True)
    payment_plan_details: str = Column(Text, nullable=True)

    # Contact
    contact_name: str = Column(String(256), nullable=True)
    contact_phone: str = Column(String(32), nullable=True)
    contact_email: str = Column(String(256), nullable=True)

    # Source and scoring
    source: str = Column(String(128), nullable=True)
    source_url: str = Column(Text, nullable=True)
    score: float = Column(Float, default=0.0)
    tags: str = Column(Text, nullable=True)

    # Audit
    created_at: datetime = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_properties_area", "area"),
        Index("ix_properties_type", "property_type"),
        Index("ix_properties_status", "status"),
        Index("ix_properties_price", "price"),
        Index("ix_properties_status_area", "status", "area"),
        Index("ix_properties_status_price", "status", "price"),
        Index("ix_properties_status_type", "status", "property_type"),
    )

    def to_dict(self) -> dict:
        """Serialize the property to a plain dictionary for API responses."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "property_type": self.property_type,
            "status": self.status,
            "area": self.area,
            "city": self.city,
            "district": self.district,
            "price": self.price,
            "price_currency": self.price_currency,
            "bedrooms": self.bedrooms,
            "bathrooms": self.bathrooms,
            "area_sqm": self.area_sqm,
            "developer": self.developer,
            "project_name": self.project_name,
            "delivery_date": self.delivery_date,
            "down_payment": self.down_payment,
            "monthly_installment": self.monthly_installment,
            "installment_years": self.installment_years,
            "payment_plan_details": self.payment_plan_details,
            "contact_name": self.contact_name,
            "contact_phone": self.contact_phone,
            "contact_email": self.contact_email,
            "source": self.source,
            "source_url": self.source_url,
            "score": self.score,
            "tags": self.tags,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# ---------------------------------------------------------------------------
# Client Request Model — طلبات العملاء
# ---------------------------------------------------------------------------
class ClientRequest(Base):
    """Client property search requests for match-making."""

    __tablename__ = "client_requests"

    id: int = Column(Integer, primary_key=True, autoincrement=True)

    # Client info
    client_name: str = Column(String(256), nullable=False)
    phone: str = Column(String(32), nullable=True)
    email: str = Column(String(256), nullable=True)
    notes: str = Column(Text, nullable=True)

    # Search criteria
    area: str = Column(String(128), nullable=True)
    property_type: str = Column(String(32), nullable=True)
    min_budget: float = Column(Float, nullable=True)
    max_budget: float = Column(Float, nullable=True)
    bedrooms: int = Column(Integer, nullable=True)
    min_area_sqm: float = Column(Float, nullable=True)
    max_area_sqm: float = Column(Float, nullable=True)
    prefer_payment_plan: bool = Column(Boolean, default=False)

    # Status
    status: str = Column(String(32), nullable=False, default="pending")
    # pending, matched, notified, converted, expired

    # Match result
    matched_property_id: int = Column(Integer, ForeignKey("properties.id"), nullable=True, index=True)
    matched_at: datetime = Column(DateTime, nullable=True)
    match_score: float = Column(Float, nullable=True)

    # Notification status
    notified_at: datetime = Column(DateTime, nullable=True)
    notification_channel: str = Column(String(32), nullable=True)

    # Priority and urgency
    priority: str = Column(String(16), nullable=False, default="normal")
    # high, normal, low

    # Audit
    created_at: datetime = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    matched_property = relationship("Property", foreign_keys=[matched_property_id])

    __table_args__ = (
        Index("ix_client_requests_status", "status"),
        Index("ix_client_requests_area", "area"),
        Index("ix_client_requests_budget", "min_budget", "max_budget"),
        Index("ix_client_requests_priority", "priority"),
        Index("ix_client_requests_created", "created_at"),
    )

    def to_dict(self) -> dict:
        """Serialize the client request to a plain dictionary for API responses."""
        return {
            "id": self.id,
            "client_name": self.client_name,
            "phone": self.phone,
            "email": self.email,
            "notes": self.notes,
            "area": self.area,
            "property_type": self.property_type,
            "min_budget": self.min_budget,
            "max_budget": self.max_budget,
            "bedrooms": self.bedrooms,
            "min_area_sqm": self.min_area_sqm,
            "max_area_sqm": self.max_area_sqm,
            "prefer_payment_plan": self.prefer_payment_plan,
            "status": self.status,
            "matched_property_id": self.matched_property_id,
            "matched_at": self.matched_at.isoformat() if self.matched_at else None,
            "match_score": self.match_score,
            "notified_at": self.notified_at.isoformat() if self.notified_at else None,
            "notification_channel": self.notification_channel,
            "priority": self.priority,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# ---------------------------------------------------------------------------
# Message Log Model — سجل الرسائل
# ---------------------------------------------------------------------------
class MessageLog(Base):
    """Message delivery log for outreach tracking."""

    __tablename__ = "message_log"

    id: int = Column(Integer, primary_key=True, autoincrement=True)

    # References
    lead_id: int = Column(Integer, ForeignKey("leads.id"), nullable=True)
    property_id: int = Column(Integer, ForeignKey("properties.id"), nullable=True)
    client_request_id: int = Column(Integer, ForeignKey("client_requests.id"), nullable=True)

    # Message details
    channel: str = Column(String(32), nullable=False)
    # whatsapp, facebook, email, sms
    message: str = Column(Text, nullable=False)
    message_type: str = Column(String(32), nullable=True, default="text")

    # Status
    status: str = Column(String(32), nullable=False, default="sent")
    # sent, delivered, read, failed, pending
    error_message: str = Column(Text, nullable=True)

    # Tracking
    sent_at: datetime = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    delivered_at: datetime = Column(DateTime, nullable=True)
    read_at: datetime = Column(DateTime, nullable=True)

    # Metadata
    phone: str = Column(String(32), nullable=True)
    recipient_name: str = Column(String(256), nullable=True)
    campaign_name: str = Column(String(128), nullable=True)

    __table_args__ = (
        Index("ix_message_log_lead_id", "lead_id"),
        Index("ix_message_log_property_id", "property_id"),
        Index("ix_message_log_client_request_id", "client_request_id"),
        Index("ix_message_log_channel", "channel"),
        Index("ix_message_log_status", "status"),
        Index("ix_message_log_sent_at", "sent_at"),
    )

    def to_dict(self) -> dict:
        """Serialize the message log entry to a plain dictionary for API responses."""
        return {
            "id": self.id,
            "lead_id": self.lead_id,
            "property_id": self.property_id,
            "client_request_id": self.client_request_id,
            "channel": self.channel,
            "message": self.message,
            "message_type": self.message_type,
            "status": self.status,
            "error_message": self.error_message,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "phone": self.phone,
            "recipient_name": self.recipient_name,
            "campaign_name": self.campaign_name,
        }


# ---------------------------------------------------------------------------
# Database Helper Functions
# ---------------------------------------------------------------------------

def get_engine(database_url: str | None = None):
    """Create SQLAlchemy engine — delegates to deps.py for single-engine consistency."""
    from src.api.deps import engine
    return engine


def get_session(engine) -> Session:
    """Create a database session."""
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def init_database(database_url: str | None = None) -> Session:
    """Initialize database and return a session — uses shared engine from deps.py."""
    engine = get_engine(database_url)
    return get_session(engine)
