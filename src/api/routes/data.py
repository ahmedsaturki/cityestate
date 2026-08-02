"""
Data System Routes — مسارات نظام البيانات
=========================================
API endpoints for data extraction, quality scoring, market research, and WhatsApp checking.
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.api.deps import require_auth

logger = logging.getLogger("api.routes.data")

router = APIRouter(prefix="/data", tags=["Data System"])


# ---------------------------------------------------------------------------
# Request/Response Models
# ---------------------------------------------------------------------------
class ExtractRequest(BaseModel):
    source: str  # whatsapp, facebook, webpage, json
    text: str
    sender: str | None = None
    url: str | None = None
    post_url: str | None = None


class QualityRequest(BaseModel):
    data: dict[str, Any]
    data_type: str = "property"  # property or lead


class WhatsAppCheckRequest(BaseModel):
    phone: str


# ---------------------------------------------------------------------------
# POST /data/extract
# ---------------------------------------------------------------------------
@router.post("/extract")
def extract_data(req: ExtractRequest, user: dict = Depends(require_auth)) -> dict:
    """Extract structured data from unstructured source."""
    from src.data.extractor import DataExtractor

    extractor = DataExtractor()

    if req.source == "whatsapp":
        result = extractor.extract_from_whatsapp(req.text, sender=req.sender)
    elif req.source == "facebook":
        result = extractor.extract_from_facebook(req.text, post_url=req.post_url)
    elif req.source == "webpage":
        result = extractor.extract_from_webpage(req.text)
    elif req.source == "json":
        try:
            import json
            data = json.loads(req.text)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON text")
        result = extractor.extract_from_json(data)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown source: {req.source}")

    return {"status": "ok", "source": req.source, "data": result, "stats": extractor.stats}


# ---------------------------------------------------------------------------
# POST /data/quality
# ---------------------------------------------------------------------------
@router.post("/quality")
def score_quality(req: QualityRequest, user: dict = Depends(require_auth)) -> dict:
    """Score data quality for property or lead record."""
    from src.data.quality import DataQualityScorer

    scorer = DataQualityScorer()

    if req.data_type == "property":
        result = scorer.score_property(req.data)
    elif req.data_type == "lead":
        result = scorer.score_lead(req.data)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown data_type: {req.data_type}")

    return {"status": "ok", "data_type": req.data_type, "result": result}


# ---------------------------------------------------------------------------
# GET /data/market-research
# ---------------------------------------------------------------------------
@router.get("/market-research")
def market_research(user: dict = Depends(require_auth)) -> dict:
    """Get static market research data for El Sadat City."""
    from src.data.enricher import AREA_METADATA, DEVELOPER_REPUTATION

    research = {
        "area": "مدينة السادات",
        "areas": AREA_METADATA,
        "developers": DEVELOPER_REPUTATION,
        "market_overview": {
            "average_price_per_sqm": 12500,
            "premium_threshold": 1500000,
            "popular_areas": [
                "المنطقة 7 الشريط المميز",
                "المنطقة 9 الشريط المميز",
                "المنطقة 15 الشريط المميز",
            ],
            "property_types": ["فيلا", "شقة فاخرة", "كمبوند", "عمارة تجارية", "مصنع"],
        },
    }

    return {"status": "ok", "data": research}


# ---------------------------------------------------------------------------
# POST /data/whatsapp-check
# ---------------------------------------------------------------------------
@router.post("/whatsapp-check")
def check_whatsapp(req: WhatsAppCheckRequest, user: dict = Depends(require_auth)) -> dict:
    """Check if a phone number is registered on WhatsApp."""
    from src.data.whatsapp_check import WhatsAppChecker

    checker = WhatsAppChecker()
    result = checker.check_whatsapp(req.phone)

    return {"status": "ok", "phone": req.phone, "result": result}
