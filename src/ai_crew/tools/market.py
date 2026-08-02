"""
Market Tools
==============
"""

import json
import logging

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)




class MarketResearchInput(BaseModel):
    area: str | None = Field(default=None, description="El Sadat City area to research")
    property_type: str | None = Field(default=None, description="Property type")


# ---------------------------------------------------------------------------
# Market Research Tool
# ---------------------------------------------------------------------------

class MarketResearchTool(BaseTool):
    """Research El Sadat City real estate market data."""
    name: str = "market_research"
    description: str = (
        "Get market data for El Sadat City areas: average prices, premium scores, "
        "facilities, and investment potential."
    )
    args_schema: type = MarketResearchInput

    def _run(self, area: str | None = None, property_type: str | None = None) -> str:
        try:
            from src.api.bridge_handler import (
                SADAT_COMMERCIAL_ZONES,
                SADAT_PREMIUM_AREAS,
                SADAT_PRICE_RANGES,
            )
            from src.data.enricher import AREA_METADATA, DEVELOPER_REPUTATION

            result = {
                "premium_areas": SADAT_PREMIUM_AREAS,
                "commercial_zones": SADAT_COMMERCIAL_ZONES,
                "price_ranges": SADAT_PRICE_RANGES,
                "area_metadata": AREA_METADATA,
                "developers": DEVELOPER_REPUTATION,
            }

            if area:
                result["filtered_area"] = {area: AREA_METADATA.get(area, {})}
            if property_type:
                result["filtered_type"] = SADAT_PRICE_RANGES.get(property_type, {})

            return json.dumps(result, ensure_ascii=False, default=str)
        except Exception as e:
            logger.error("Market research failed: %s", e)
            return json.dumps({"error": str(e)})

