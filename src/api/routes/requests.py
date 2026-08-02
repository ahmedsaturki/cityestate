"""
Client Requests Routes — مسارات طلبات العملاء
===============================================
CRUD operations for client property search requests.
"""


from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.api.deps import get_db, require_auth
from src.api.models import (
    ClientRequestCreate,
    ClientRequestResponse,
    ClientRequestUpdate,
    MatchResponse,
    MatchResult,
)
from src.database.models import ClientRequest
from src.matching.engine import MatchMakingEngine

router = APIRouter(prefix="/requests", tags=["Client Requests"])


@router.get("", response_model=list[ClientRequestResponse])
def list_requests(
    status_filter: str | None = Query(None, alias="status"),
    area: str | None = None,
    priority: str | None = None,
    limit: int = Query(100, le=500),
    offset: int = 0,
    user: dict = Depends(require_auth),
    db: Session = Depends(get_db),
) -> list[dict]:
    """List client requests with optional filters."""
    query = db.query(ClientRequest)

    if status_filter:
        query = query.filter(ClientRequest.status == status_filter)
    if area:
        query = query.filter(ClientRequest.area == area)
    if priority:
        query = query.filter(ClientRequest.priority == priority)

    requests = query.order_by(ClientRequest.created_at.desc()).offset(offset).limit(limit).all()
    return [ClientRequestResponse(**r.to_dict()) for r in requests]


@router.get("/stats/summary")
def get_request_stats(
    user: dict = Depends(require_auth),
    db: Session = Depends(get_db),
) -> dict:
    """Get client request statistics — uses consolidated queries to avoid N+1."""
    from sqlalchemy import func

    total = db.query(ClientRequest).count()

    # Single query for status counts
    status_counts = (
        db.query(ClientRequest.status, func.count(ClientRequest.id))
        .group_by(ClientRequest.status)
        .all()
    )
    by_status = {s: cnt for s, cnt in status_counts if cnt > 0}

    # Single query for priority counts
    priority_counts = (
        db.query(ClientRequest.priority, func.count(ClientRequest.id))
        .group_by(ClientRequest.priority)
        .all()
    )
    by_priority = {p: cnt for p, cnt in priority_counts if cnt > 0}

    return {
        "total_requests": total,
        "by_status": by_status,
        "by_priority": by_priority,
    }


@router.get("/{request_id}", response_model=ClientRequestResponse)
def get_request(
    request_id: int,
    user: dict = Depends(require_auth),
    db: Session = Depends(get_db),
) -> dict:
    """Get a single client request by ID."""
    req = db.query(ClientRequest).filter(ClientRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Client request not found")
    return ClientRequestResponse(**req.to_dict())


@router.post("", response_model=ClientRequestResponse, status_code=status.HTTP_201_CREATED)
def create_request(
    request: ClientRequestCreate,
    user: dict = Depends(require_auth),
    db: Session = Depends(get_db),
) -> dict:
    """Create a new client request."""
    req = ClientRequest(
        client_name=request.client_name,
        phone=request.phone,
        email=request.email,
        notes=request.notes,
        area=request.area,
        property_type=request.property_type,
        min_budget=request.min_budget,
        max_budget=request.max_budget,
        bedrooms=request.bedrooms,
        min_area_sqm=request.min_area_sqm,
        max_area_sqm=request.max_area_sqm,
        prefer_payment_plan=request.prefer_payment_plan,
        priority=request.priority,
        status="pending",
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return ClientRequestResponse(**req.to_dict())


@router.put("/{request_id}", response_model=ClientRequestResponse)
def update_request(
    request_id: int,
    request: ClientRequestUpdate,
    user: dict = Depends(require_auth),
    db: Session = Depends(get_db),
) -> dict:
    """Update a client request."""
    req = db.query(ClientRequest).filter(ClientRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Client request not found")

    update_data = request.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(req, key, value)

    db.commit()
    db.refresh(req)
    return ClientRequestResponse(**req.to_dict())


@router.delete("/{request_id}")
def delete_request(
    request_id: int,
    user: dict = Depends(require_auth),
    db: Session = Depends(get_db),
) -> dict:
    """Delete a client request."""
    req = db.query(ClientRequest).filter(ClientRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Client request not found")
    db.delete(req)
    db.commit()
    return {"status": "deleted", "id": request_id}


@router.post("/{request_id}/match", response_model=MatchResponse)
def match_request(
    request_id: int,
    user: dict = Depends(require_auth),
    db: Session = Depends(get_db),
) -> dict:
    """Find matching properties for a client request."""
    from datetime import datetime, timezone

    req = db.query(ClientRequest).filter(ClientRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Client request not found")

    # Use the unified MatchMakingEngine (replaces duplicate scoring logic)
    engine = MatchMakingEngine(db)
    result = engine.match_request(request_id)

    # Convert to response format
    matches = []
    for m in result.get("matches", []):
        matches.append(MatchResult(
            request_id=request_id,
            property_id=m["property_id"],
            match_score=round(m["score"], 2),
            matched_at=datetime.now(timezone.utc).isoformat(),
            property_title=m["property_title"],
            property_area=m["property_area"],
            property_price=m["property_price"],
        ))

    return MatchResponse(
        status=result.get("status", "no_matches"),
        matches=matches[:10],
        total_matches=result.get("total_matches", 0),
    )
