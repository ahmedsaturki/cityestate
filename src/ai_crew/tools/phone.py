"""
Phone Tools
=============
"""

import json
import logging

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)




class PhoneValidatorInput(BaseModel):
    phone: str = Field(description="Phone number to validate")
    name: str | None = Field(default=None, description="Contact name")
    property_type: str | None = Field(default=None, description="Property type interest")
    budget: float | None = Field(default=None, description="Budget amount")


# ---------------------------------------------------------------------------
# Phone Validator Tool
# ---------------------------------------------------------------------------

class PhoneValidatorTool(BaseTool):
    """Validate Egyptian phone numbers and qualify leads."""
    name: str = "phone_validator"
    description: str = (
        "Validate Egyptian phone number format, normalize to international format, "
        "and qualify lead based on phone + property data."
    )
    args_schema: type = PhoneValidatorInput

    def _run(self, phone: str, name: str | None = None, property_type: str | None = None, budget: float | None = None) -> str:
        try:
            from src.data.whatsapp_check import WhatsAppChecker
            checker = WhatsAppChecker()
            normalized = checker.normalize_phone(phone)
            qualification = checker.qualify_lead(phone, name, property_type, budget)
            result = {
                "original": phone,
                "normalized": normalized,
                "is_egyptian": checker.is_egyptian_number(phone),
                "qualification": qualification,
            }
            return json.dumps(result, ensure_ascii=False, default=str)
        except Exception as e:
            logger.error("Phone validation failed: %s", e)
            return json.dumps({"error": str(e)})


# ---------------------------------------------------------------------------
# Market Research Input
# ---------------------------------------------------------------------------
