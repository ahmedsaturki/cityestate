"""
Leads Routes — مسارات إدارة العملاء
=====================================
CRUD operations for leads.
"""


from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.api.deps import get_db, require_auth
from src.api.models import LeadCreate, LeadResponse, LeadUpdate
from src.cache_utils import cache
from src.database.ingester import Lead

router = APIRouter(prefix="/leads", tags=["Leads"])


@router.get("", response_model=list[LeadResponse])
def list_leads(
    lead_type: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
    area: str | None = None,
    limit: int = Query(100, le=500),
    offset: int = 0,
    user: dict = Depends(require_auth),
    db: Session = Depends(get_db),
) -> list[dict]:
    """List leads with optional filters. Results are cached for 60 seconds."""
    cache_key = f"leads:{lead_type}:{status_filter}:{area}:{limit}:{offset}"
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return cached_result

    query = db.query(Lead)

    if lead_type:
        query = query.filter(Lead.lead_type == lead_type)
    if status_filter:
        query = query.filter(Lead.status == status_filter)
    if area:
        query = query.filter(Lead.area == area)

    leads = query.order_by(Lead.created_at.desc()).offset(offset).limit(limit).all()
    result = [LeadResponse(**l.to_dict()) for l in leads]
    cache.set(cache_key, result, ttl=60)
    return result


@router.get("/stats/summary")
def get_lead_stats(
    user: dict = Depends(require_auth),
    db: Session = Depends(get_db),
) -> dict:
    """Get lead statistics — uses consolidated queries to avoid N+1.
    Results are cached for 120 seconds."""
    cache_key = "leads:stats:summary"
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return cached_result

    from sqlalchemy import func

    total = db.query(Lead).count()

    # Single query for type counts
    type_counts = (
        db.query(Lead.lead_type, func.count(Lead.id))
        .group_by(Lead.lead_type)
        .all()
    )
    by_type = {lt: cnt for lt, cnt in type_counts if cnt > 0}

    # Single query for status counts
    status_counts = (
        db.query(Lead.status, func.count(Lead.id))
        .group_by(Lead.status)
        .all()
    )
    by_status = {s: cnt for s, cnt in status_counts if cnt > 0}

    result = {
        "total_leads": total,
        "by_type": by_type,
        "by_status": by_status,
    }
    cache.set(cache_key, result, ttl=120)
    return result


@router.get("/{lead_id}", response_model=LeadResponse)
def get_lead(
    lead_id: int,
    user: dict = Depends(require_auth),
    db: Session = Depends(get_db),
) -> dict:
    """Get a single lead by ID."""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return LeadResponse(**lead.to_dict())


@router.post("", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
def create_lead(
    request: LeadCreate,
    user: dict = Depends(require_auth),
    db: Session = Depends(get_db),
) -> dict:
    """Create a new lead."""
    # Check URL uniqueness
    existing = db.query(Lead).filter(Lead.url == request.url).first()
    if existing:
        raise HTTPException(status_code=409, detail="Lead with this URL already exists")

    lead = Lead(
        title=request.title,
        url=request.url,
        source=request.source,
        lead_type=request.lead_type,
        budget=request.budget,
        area=request.area,
        interest=request.interest,
        urgency=request.urgency,
        phone=request.phone,
        email=request.email,
        tags=request.tags,
        status="new",
        score=0.0,
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return LeadResponse(**lead.to_dict())


@router.put("/{lead_id}", response_model=LeadResponse)
def update_lead(
    lead_id: int,
    request: LeadUpdate,
    user: dict = Depends(require_auth),
    db: Session = Depends(get_db),
) -> dict:
    """Update an existing lead."""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    update_data = request.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(lead, key, value)

    db.commit()
    db.refresh(lead)
    return LeadResponse(**lead.to_dict())


@router.delete("/{lead_id}")
def delete_lead(
    lead_id: int,
    user: dict = Depends(require_auth),
    db: Session = Depends(get_db),
) -> dict:
    """Delete a lead."""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    db.delete(lead)
    db.commit()
    return {"status": "deleted", "id": lead_id}
