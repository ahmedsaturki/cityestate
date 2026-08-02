"""
Content API — صانع المحتوى التلقائي
====================================
REST endpoints for generating marketing content for properties.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.api.deps import require_auth
from src.database.models import Property, init_database
from src.outreach.content_generator import ContentGenerator

logger = logging.getLogger("api.content")

router = APIRouter(prefix="/content", tags=["Content Generator"])
generator = ContentGenerator()


class ContentRequest(BaseModel):
    property_id: int
    channel: str = Field(default="all", pattern="^(facebook|instagram|whatsapp|all)$")


class ContentResponse(BaseModel):
    property_id: int
    property_title: str
    content: dict


# ------------------------------------------------------------------
# POST /api/v1/content/generate
# ------------------------------------------------------------------
@router.post("/generate", response_model=ContentResponse)
def generate_content(
    req: ContentRequest,
    user: dict = Depends(require_auth),
) -> dict:
    """Generate marketing content for a property."""
    db = init_database()
    try:
        prop = db.query(Property).filter(Property.id == req.property_id).first()
        if not prop:
            raise HTTPException(status_code=404, detail=f"Property #{req.property_id} not found")

        prop_data = {
            "id": prop.id,
            "title": prop.title,
            "description": prop.description or "",
            "property_type": prop.property_type,
            "status": prop.status,
            "area": prop.area,
            "city": prop.city,
            "district": prop.district,
            "price": prop.price,
            "price_currency": prop.price_currency,
            "bedrooms": prop.bedrooms,
            "bathrooms": prop.bathrooms,
            "area_sqm": prop.area_sqm,
            "developer": prop.developer,
            "project_name": prop.project_name,
            "delivery_date": prop.delivery_date,
            "down_payment": prop.down_payment,
            "monthly_installment": prop.monthly_installment,
            "installment_years": prop.installment_years,
            "payment_plan_details": prop.payment_plan_details,
        }

        result = generator.generate(prop_data, channel=req.channel)
        return ContentResponse(**result)

    finally:
        db.close()


# ------------------------------------------------------------------
# GET /api/v1/content/preview/{property_id}
# ------------------------------------------------------------------
@router.get("/preview/{property_id}")
def preview_content(
    property_id: int,
    channel: str = "all",
    user: dict = Depends(require_auth),
) -> dict:
    """Quick preview of generated content for a property."""
    db = init_database()
    try:
        prop = db.query(Property).filter(Property.id == property_id).first()
        if not prop:
            raise HTTPException(status_code=404, detail=f"Property #{property_id} not found")

        prop_data = {
            "id": prop.id,
            "title": prop.title,
            "description": prop.description or "",
            "property_type": prop.property_type,
            "area": prop.area,
            "price": prop.price,
            "bedrooms": prop.bedrooms,
            "bathrooms": prop.bathrooms,
            "area_sqm": prop.area_sqm,
            "developer": prop.developer,
            "project_name": prop.project_name,
            "delivery_date": prop.delivery_date,
            "down_payment": prop.down_payment,
            "monthly_installment": prop.monthly_installment,
            "installment_years": prop.installment_years,
            "payment_plan_details": prop.payment_plan_details,
        }

        return generator.generate(prop_data, channel=channel)

    finally:
        db.close()
