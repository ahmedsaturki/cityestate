"""
Properties Routes — مسارات إدارة العقارات
===========================================
CRUD operations for property inventory.
"""


from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.api.deps import get_db, require_auth
from src.api.models import PropertyCreate, PropertyResponse, PropertyUpdate
from src.cache_utils import cache
from src.database.models import Property

router = APIRouter(prefix="/properties", tags=["Properties"])


@router.get("", response_model=list[PropertyResponse])
def list_properties(
    property_type: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
    area: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    bedrooms: int | None = None,
    limit: int = Query(100, le=500),
    offset: int = 0,
    user: dict = Depends(require_auth),
    db: Session = Depends(get_db),
) -> list[dict]:
    """List properties with optional filters. Results are cached for 60 seconds."""
    cache_key = f"properties:{property_type}:{status_filter}:{area}:{min_price}:{max_price}:{bedrooms}:{limit}:{offset}"
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return cached_result

    query = db.query(Property)

    if property_type:
        query = query.filter(Property.property_type == property_type)
    if status_filter:
        query = query.filter(Property.status == status_filter)
    if area:
        query = query.filter(Property.area == area)
    if min_price:
        query = query.filter(Property.price >= min_price)
    if max_price:
        query = query.filter(Property.price <= max_price)
    if bedrooms:
        query = query.filter(Property.bedrooms == bedrooms)

    props = query.order_by(Property.created_at.desc()).offset(offset).limit(limit).all()
    result = [PropertyResponse(**p.to_dict()) for p in props]
    cache.set(cache_key, result, ttl=60)
    return result


@router.get("/stats/summary")
def get_property_stats(
    user: dict = Depends(require_auth),
    db: Session = Depends(get_db),
) -> dict:
    """Get property statistics — uses consolidated queries to avoid N+1."""
    from sqlalchemy import func

    total = db.query(Property).count()

    # Single query for status counts
    status_counts = (
        db.query(Property.status, func.count(Property.id))
        .group_by(Property.status)
        .all()
    )
    by_status = {s: cnt for s, cnt in status_counts if cnt > 0}

    # Single query for type counts
    type_counts = (
        db.query(Property.property_type, func.count(Property.id))
        .group_by(Property.property_type)
        .all()
    )
    by_type = {t: cnt for t, cnt in type_counts if cnt > 0}

    # Price stats — single query
    price_stats = db.query(
        func.min(Property.price),
        func.max(Property.price),
        func.avg(Property.price),
    ).filter(Property.status == "available").first()

    return {
        "total_properties": total,
        "by_status": by_status,
        "by_type": by_type,
        "price_stats": {
            "min": price_stats[0] if price_stats and price_stats[0] else 0,
            "max": price_stats[1] if price_stats and price_stats[1] else 0,
            "avg": round(price_stats[2], 2) if price_stats and price_stats[2] else 0,
        },
    }


@router.get("/{property_id}", response_model=PropertyResponse)
def get_property(
    property_id: int,
    user: dict = Depends(require_auth),
    db: Session = Depends(get_db),
) -> dict:
    """Get a single property by ID."""
    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    return PropertyResponse(**prop.to_dict())


@router.post("", response_model=PropertyResponse, status_code=status.HTTP_201_CREATED)
def create_property(
    request: PropertyCreate,
    user: dict = Depends(require_auth),
    db: Session = Depends(get_db),
) -> dict:
    """Create a new property listing."""
    prop = Property(
        title=request.title,
        description=request.description,
        property_type=request.property_type,
        status=request.status,
        area=request.area,
        city=request.city,
        district=request.district,
        price=request.price,
        price_currency=request.price_currency,
        bedrooms=request.bedrooms,
        bathrooms=request.bathrooms,
        area_sqm=request.area_sqm,
        developer=request.developer,
        project_name=request.project_name,
        delivery_date=request.delivery_date,
        down_payment=request.down_payment,
        monthly_installment=request.monthly_installment,
        installment_years=request.installment_years,
        payment_plan_details=request.payment_plan_details,
        contact_name=request.contact_name,
        contact_phone=request.contact_phone,
        contact_email=request.contact_email,
        source=request.source,
        source_url=request.source_url,
        tags=request.tags,
    )
    db.add(prop)
    db.commit()
    db.refresh(prop)
    return PropertyResponse(**prop.to_dict())


@router.put("/{property_id}", response_model=PropertyResponse)
def update_property(
    property_id: int,
    request: PropertyUpdate,
    user: dict = Depends(require_auth),
    db: Session = Depends(get_db),
) -> dict:
    """Update an existing property."""
    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    update_data = request.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(prop, key, value)

    db.commit()
    db.refresh(prop)
    return PropertyResponse(**prop.to_dict())


@router.delete("/{property_id}")
def delete_property(
    property_id: int,
    user: dict = Depends(require_auth),
    db: Session = Depends(get_db),
) -> dict:
    """Delete a property."""
    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    db.delete(prop)
    db.commit()
    return {"status": "deleted", "id": property_id}
