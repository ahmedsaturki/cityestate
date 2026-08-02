"""
Database Tools
================
"""

import json

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class DatabaseQueryInput(BaseModel):
    query_description: str = Field(description="Natural language description of what to search for")



class DatabaseQueryTool(BaseTool):
    """Query the cityestate database for leads, properties, and requests."""
    name: str = "database_query"
    description: str = (
        "Search the cityestate database. Can query leads, properties, or client requests. "
        "Input should be a natural language description like 'get all leads from Facebook' "
        "or 'find available apartments in Sheikh Zayed'."
    )
    args_schema: type = DatabaseQueryInput

    def _run(self, query_description: str) -> str:
        try:
            from src.api.deps import SessionLocal
            from src.database.ingester import Lead
            from src.database.models import ClientRequest, Property

            db = SessionLocal()
            try:
                query_lower = query_description.lower()

                # Lead queries
                if "lead" in query_lower:
                    leads = db.query(Lead).order_by(Lead.created_at.desc()).limit(20).all()
                    return json.dumps([l.to_dict() for l in leads], ensure_ascii=False, default=str)

                # Property queries
                if "property" in query_lower or "عقار" in query_lower or "شقة" in query_lower:
                    q = db.query(Property).filter(Property.status == "available")
                    if any(w in query_lower for w in ["شقة", "apartment"]):
                        q = q.filter(Property.property_type == "apartment")
                    if any(w in query_lower for w in ["فيلا", "villa"]):
                        q = q.filter(Property.property_type == "villa")
                    props = q.order_by(Property.created_at.desc()).limit(20).all()
                    return json.dumps([p.to_dict() for p in props], ensure_ascii=False, default=str)

                # Request queries
                if "request" in query_lower or "طلب" in query_lower:
                    reqs = db.query(ClientRequest).order_by(ClientRequest.created_at.desc()).limit(20).all()
                    return json.dumps([r.to_dict() for r in reqs], ensure_ascii=False, default=str)

                # Default: return summary stats
                lead_count = db.query(Lead).count()
                prop_count = db.query(Property).filter(Property.status == "available").count()
                req_count = db.query(ClientRequest).filter(ClientRequest.status == "pending").count()
                return json.dumps({
                    "leads": lead_count,
                    "available_properties": prop_count,
                    "pending_requests": req_count,
                })
            finally:
                db.close()
        except Exception as e:
            return json.dumps({"error": str(e)})


# ---------------------------------------------------------------------------
# Property Search Tool
# ---------------------------------------------------------------------------
