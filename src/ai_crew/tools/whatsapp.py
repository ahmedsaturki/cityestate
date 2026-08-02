"""
Whatsapp Tools
================
"""

import json
import logging

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)




class WhatsAppSendInput(BaseModel):
    phone: str = Field(description="Recipient phone number")
    message: str = Field(description="Message body")



class WhatsAppSendTool(BaseTool):
    """Send a WhatsApp message to a phone number."""
    name: str = "whatsapp_send"
    description: str = (
        "Send a WhatsApp message. Input: phone number and message text. "
        "Use for sending property details, follow-ups, or responses to inquiries."
    )
    args_schema: type = WhatsAppSendInput

    def _run(self, phone: str, message: str) -> str:
        try:
            from src.services.mcp_service import get_mcp_service
            mcp = get_mcp_service()
            result = mcp.send_whatsapp(phone, message, dry_run=False)
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"status": "error", "error": str(e)})


# ---------------------------------------------------------------------------
# Web Search Tool
# ---------------------------------------------------------------------------

class WhatsAppCheckInput(BaseModel):
    phone: str = Field(description="Phone number to check")


# ---------------------------------------------------------------------------
# WhatsApp Check Tool
# ---------------------------------------------------------------------------

class WhatsAppCheckTool(BaseTool):
    """Check if a phone number is registered on WhatsApp."""
    name: str = "whatsapp_check"
    description: str = (
        "Check if a phone number is registered on WhatsApp and normalize it. "
        "Also qualifies leads based on phone validity and data completeness."
    )
    args_schema: type = WhatsAppCheckInput

    def _run(self, phone: str) -> str:
        try:
            from src.data.whatsapp_check import WhatsAppChecker
            checker = WhatsAppChecker()
            check_result = checker.check_whatsapp(phone)
            qualification = checker.qualify_lead(phone)
            result = {
                "whatsapp_check": check_result,
                "qualification": qualification,
            }
            return json.dumps(result, ensure_ascii=False, default=str)
        except Exception as e:
            logger.error("WhatsApp check failed: %s", e)
            return json.dumps({"error": str(e)})


# ---------------------------------------------------------------------------
# Data Quality Input
# ---------------------------------------------------------------------------
