"""
Dashboard Routes — مسارات لوحة التحكم
=======================================
Aggregated statistics for the dashboard.
"""


from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.api.deps import get_db, require_auth
from src.api.models import DashboardStats
from src.database.ingester import Lead
from src.database.models import ClientRequest, MessageLog, Property

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(
    user: dict = Depends(require_auth),
    db: Session = Depends(get_db),
) -> dict:
    """Get aggregated dashboard statistics."""
    # Lead stats
    total_leads = db.query(Lead).count()
    leads_by_type = {}
    for lt in ["Developer", "Agency", "Buyer", "Investor", "Seller", "Unknown"]:
        count = db.query(Lead).filter(Lead.lead_type == lt).count()
        if count > 0:
            leads_by_type[lt] = count

    leads_by_status = {}
    for s in ["new", "contacted", "qualified", "converted"]:
        count = db.query(Lead).filter(Lead.status == s).count()
        if count > 0:
            leads_by_status[s] = count

    # Property stats
    total_properties = db.query(Property).count()
    properties_by_status = {}
    for s in ["available", "sold", "reserved", "pending"]:
        count = db.query(Property).filter(Property.status == s).count()
        if count > 0:
            properties_by_status[s] = count

    # Request stats
    total_requests = db.query(ClientRequest).count()
    requests_by_status = {}
    for s in ["pending", "matched", "notified", "converted", "expired"]:
        count = db.query(ClientRequest).filter(ClientRequest.status == s).count()
        if count > 0:
            requests_by_status[s] = count

    # Message stats
    total_messages = db.query(MessageLog).count()

    # Recent leads
    recent_leads = (
        db.query(Lead)
        .order_by(Lead.created_at.desc())
        .limit(5)
        .all()
    )

    # Recent messages
    recent_messages = (
        db.query(MessageLog)
        .order_by(MessageLog.sent_at.desc())
        .limit(5)
        .all()
    )

    return DashboardStats(
        total_leads=total_leads,
        total_properties=total_properties,
        total_requests=total_requests,
        total_messages=total_messages,
        leads_by_type=leads_by_type,
        leads_by_status=leads_by_status,
        properties_by_status=properties_by_status,
        requests_by_status=requests_by_status,
        recent_leads=[l.to_dict() for l in recent_leads],
        recent_messages=[m.to_dict() for m in recent_messages],
    )


@router.get("/charts")
def get_chart_data(
    user: dict = Depends(require_auth),
    db: Session = Depends(get_db),
) -> dict:
    """Get chart data for dashboard visualization."""
    # Lead type distribution
    lead_type_data = []
    for lt in ["Developer", "Agency", "Buyer", "Investor", "Unknown"]:
        count = db.query(Lead).filter(Lead.lead_type == lt).count()
        if count > 0:
            lead_type_data.append({"name": lt, "value": count})

    # Property price ranges
    price_ranges = [
        {"label": "< 1M", "min": 0, "max": 1000000},
        {"label": "1M-3M", "min": 1000000, "max": 3000000},
        {"label": "3M-5M", "min": 3000000, "max": 5000000},
        {"label": "5M-10M", "min": 5000000, "max": 10000000},
        {"label": "> 10M", "min": 10000000, "max": 999999999},
    ]
    price_distribution = []
    for pr in price_ranges:
        count = db.query(Property).filter(
            Property.price >= pr["min"],
            Property.price < pr["max"],
            Property.status == "available",
        ).count()
        price_distribution.append({"range": pr["label"], "count": count})

    # Area distribution (top 10)
    area_data = (
        db.query(Property.area, func.count(Property.id))
        .filter(Property.status == "available")
        .group_by(Property.area)
        .order_by(func.count(Property.id).desc())
        .limit(10)
        .all()
    )
    area_distribution = [{"area": a[0], "count": a[1]} for a in area_data if a[0]]

    return {
        "lead_type_distribution": lead_type_data,
        "price_distribution": price_distribution,
        "area_distribution": area_distribution,
    }
