"""
Properties Tools
==================
"""

import json

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class PropertySearchInput(BaseModel):
    area: str | None = Field(default=None, description="Area/location filter")
    min_price: float | None = Field(default=None, description="Minimum price EGP")
    max_price: float | None = Field(default=None, description="Maximum price EGP")
    bedrooms: int | None = Field(default=None, description="Number of bedrooms")
    property_type: str | None = Field(default=None, description="Property type")


# ---------------------------------------------------------------------------
# Database Query Tool
# ---------------------------------------------------------------------------

class PropertySearchTool(BaseTool):
    """Search properties by criteria and return matches."""
    name: str = "property_search"
    description: str = (
        "Search available properties by area, price, bedrooms, or type. "
        "Returns matching properties with details."
    )
    args_schema: type = PropertySearchInput

    def _run(
        self,
        area: str | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        bedrooms: int | None = None,
        property_type: str | None = None,
    ) -> str:
        try:
            from src.api.deps import SessionLocal
            from src.database.models import Property

            db = SessionLocal()
            try:
                q = db.query(Property).filter(Property.status == "available")
                if area:
                    q = q.filter(Property.area.ilike(f"%{area}%"))
                if min_price:
                    q = q.filter(Property.price >= min_price)
                if max_price:
                    q = q.filter(Property.price <= max_price)
                if bedrooms:
                    q = q.filter(Property.bedrooms == bedrooms)
                if property_type:
                    q = q.filter(Property.property_type == property_type)

                props = q.order_by(Property.price).limit(10).all()
                if not props:
                    return json.dumps({"message": "No properties match your criteria", "matches": []})

                results = []
                for p in props:
                    results.append({
                        "id": p.id,
                        "title": p.title,
                        "area": p.area,
                        "price": p.price,
                        "bedrooms": p.bedrooms,
                        "type": p.property_type,
                        "developer": p.developer,
                    })
                return json.dumps({"matches": len(results), "properties": results}, ensure_ascii=False)
            finally:
                db.close()
        except Exception as e:
            return json.dumps({"error": str(e)})


# ---------------------------------------------------------------------------
# WhatsApp Send Tool
# ---------------------------------------------------------------------------
