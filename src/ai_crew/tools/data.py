"""
Data Tools
============
"""

import json
import logging

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)




class DataExtractionInput(BaseModel):
    source: str = Field(description="Data source: 'whatsapp', 'facebook', 'web', 'json'")
    text: str = Field(description="Raw text/message to extract data from")
    sender: str | None = Field(default=None, description="Sender name or phone")
    url: str | None = Field(default=None, description="Source URL (for web)")


# ---------------------------------------------------------------------------
# Data Extraction Tool
# ---------------------------------------------------------------------------

class DataExtractionTool(BaseTool):
    """Extract structured property data from unstructured text."""
    name: str = "data_extraction"
    description: str = (
        "Extract property data (type, area, budget, bedrooms, phone) from "
        "WhatsApp messages, Facebook posts, or web page content. "
        "Input: source type and raw text."
    )
    args_schema: type = DataExtractionInput

    def _run(self, source: str, text: str, sender: str | None = None, url: str | None = None) -> str:
        try:
            from src.data.extractor import DataExtractor
            extractor = DataExtractor()

            if source == "whatsapp":
                result = extractor.extract_from_whatsapp(text, sender)
            elif source == "facebook":
                result = extractor.extract_from_facebook(text, sender, url)
            elif source == "web":
                result = extractor.extract_from_webpage(text, url)
            elif source == "json":
                result = extractor.extract_from_json(json.loads(text))
            else:
                return json.dumps({"error": f"Unknown source: {source}"})

            return json.dumps(result, ensure_ascii=False, default=str)
        except Exception as e:
            logger.error("Data extraction failed: %s", e)
            return json.dumps({"error": str(e)})


# ---------------------------------------------------------------------------
# Web Crawler Input
# ---------------------------------------------------------------------------

class DataEnrichmentInput(BaseModel):
    property_data: str = Field(description="JSON string of property data to enrich")


# ---------------------------------------------------------------------------
# Data Enrichment Tool
# ---------------------------------------------------------------------------

class DataEnrichmentTool(BaseTool):
    """Enrich property data with area metadata and market comparison."""
    name: str = "data_enrichment"
    description: str = (
        "Enrich property data with price per sqm, area premium score, "
        "developer reputation, market comparison, and data completeness."
    )
    args_schema: type = DataEnrichmentInput

    def _run(self, property_data: str) -> str:
        try:
            from src.data.enricher import DataEnricher
            enricher = DataEnricher()
            data = json.loads(property_data)
            result = enricher.enrich(data)
            return json.dumps(result, ensure_ascii=False, default=str)
        except Exception as e:
            logger.error("Data enrichment failed: %s", e)
            return json.dumps({"error": str(e)})


# ---------------------------------------------------------------------------
# WhatsApp Check Input
# ---------------------------------------------------------------------------

class DataQualityInput(BaseModel):
    data: str = Field(description="JSON string of property or lead data to score")
    data_type: str = Field(default="property", description="'property' or 'lead'")


# ---------------------------------------------------------------------------
# Data Quality Scoring Tool
# ---------------------------------------------------------------------------

class DataQualityTool(BaseTool):
    """Score data quality for property listings or lead records."""
    name: str = "data_quality"
    description: str = (
        "Score data quality (completeness, freshness, consistency) for "
        "property listings or lead records. Returns score, tier, and issues."
    )
    args_schema: type = DataQualityInput

    def _run(self, data: str, data_type: str = "property") -> str:
        try:
            from src.data.quality import DataQualityScorer
            scorer = DataQualityScorer()
            item = json.loads(data)
            if data_type == "property":
                result = scorer.score_property(item)
            else:
                result = scorer.score_lead(item)
            return json.dumps(result, ensure_ascii=False, default=str)
        except Exception as e:
            logger.error("Quality scoring failed: %s", e)
            return json.dumps({"error": str(e)})


# ---------------------------------------------------------------------------
# Phone Validator Input
# ---------------------------------------------------------------------------
