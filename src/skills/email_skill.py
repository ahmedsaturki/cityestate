"""
Email Skill — إرسال واستقبال الإيميلات
======================================
Email management: send, receive, parse, and draft emails.
Supports Gmail API and SMTP fallback.
"""

import json
import logging
import smtplib
import ssl
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

logger = logging.getLogger("skills.email")


class EmailSkill:
    """Email management skill."""

    def __init__(self, smtp_host: str = "smtp.gmail.com", smtp_port: int = 587):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port

    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        from_name: str = "CityEstate",
        attachments: list[str] | None = None,
        is_html: bool = False,
    ) -> dict:
        """Send an email via SMTP."""
        try:
            import os

            smtp_user = os.getenv("SMTP_USERNAME", "")
            smtp_pass = os.getenv("SMTP_PASSWORD", "")

            if not smtp_user or not smtp_pass:
                return {
                    "status": "error",
                    "error": "SMTP credentials not configured. Set SMTP_USERNAME and SMTP_PASSWORD.",
                }

            msg = MIMEMultipart()
            msg["From"] = f"{from_name} <{smtp_user}>"
            msg["To"] = to
            msg["Subject"] = subject

            content_type = "html" if is_html else "plain"
            msg.attach(MIMEText(body, content_type, "utf-8"))

            if attachments:
                for filepath in attachments:
                    path = Path(filepath)
                    if path.exists():
                        with open(path, "rb") as f:
                            part = MIMEBase("application", "octet-stream")
                            part.set_payload(f.read())
                        encoders.encode_base64(part)
                        part.add_header(
                            "Content-Disposition",
                            f"attachment; filename={path.name}",
                        )
                        msg.attach(part)

            context = ssl.create_default_context()
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)

            return {
                "status": "sent",
                "to": to,
                "subject": subject,
                "attachments": len(attachments) if attachments else 0,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def send_bulk(
        self,
        recipients: list[str],
        subject: str,
        body: str,
        from_name: str = "CityEstate",
    ) -> dict:
        """Send email to multiple recipients."""
        results = []
        for recipient in recipients:
            result = await self.send_email(recipient, subject, body, from_name)
            results.append({"recipient": recipient, **result})

        sent = sum(1 for r in results if r["status"] == "sent")
        failed = sum(1 for r in results if r["status"] == "error")

        return {
            "status": "completed",
            "total": len(recipients),
            "sent": sent,
            "failed": failed,
            "results": results,
        }

    async def draft_property_inquiry(self, property_info: dict) -> dict:
        """Draft an email for a property inquiry."""
        template = f"""
Dear {property_info.get('agent_name', 'Agent')},

I am writing to express my interest in the property listed at:
{property_info.get('address', 'N/A')}

Property Details:
- Price: {property_info.get('price', 'N/A')}
- Area: {property_info.get('area', 'N/A')} sqm
- Bedrooms: {property_info.get('bedrooms', 'N/A')}
- Bathrooms: {property_info.get('bathrooms', 'N/A')}

I would like to schedule a viewing at your earliest convenience.
Please let me know available time slots.

Best regards,
{property_info.get('sender_name', 'CityEstate User')}
"""
        return {
            "status": "drafted",
            "subject": f"Property Inquiry - {property_info.get('address', 'N/A')}",
            "body": template.strip(),
            "recipient": property_info.get("agent_email", ""),
        }

    async def draft_price_negotiation(self, property_info: dict, offer_price: str) -> dict:
        """Draft a price negotiation email."""
        template = f"""
Dear {property_info.get('agent_name', 'Agent')},

Thank you for providing the details for the property at:
{property_info.get('address', 'N/A')}

After careful consideration, I would like to propose an offer of {offer_price}
for this property, compared to the listed price of {property_info.get('price', 'N/A')}.

I believe this offer reflects the current market conditions and the condition
of the property. I am ready to proceed with the transaction promptly.

Looking forward to your response.

Best regards,
{property_info.get('sender_name', 'CityEstate User')}
"""
        return {
            "status": "drafted",
            "subject": f"Offer Submission - {property_info.get('address', 'N/A')}",
            "body": template.strip(),
            "recipient": property_info.get("agent_email", ""),
            "offer_price": offer_price,
        }

    async def parse_email(self, raw_email: str) -> dict:
        """Parse a raw email into structured data."""
        from email import message_from_string

        msg = message_from_string(raw_email)

        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode("utf-8", errors="replace")
                    break
        else:
            body = msg.get_payload(decode=True).decode("utf-8", errors="replace")

        return {
            "from": msg["From"],
            "to": msg["To"],
            "subject": msg["Subject"],
            "date": msg["Date"],
            "body": body[:5000],
        }


def get_email_tools():
    """Return CrewAI-compatible tools for email."""
    from crewai.tools import BaseTool
    from pydantic import BaseModel, Field

    class SendEmailInput(BaseModel):
        to: str = Field(description="Recipient email address")
        subject: str = Field(description="Email subject")
        body: str = Field(description="Email body text")
        is_html: bool = Field(default=False, description="Whether body is HTML")

    class SendEmailTool(BaseTool):
        name: str = "send_email"
        description: str = "Send an email to a recipient with subject and body."
        args_schema: type = SendEmailInput

        def _run(self, to: str, subject: str, body: str, is_html: bool = False) -> str:
            import asyncio
            skill = EmailSkill()
            result = asyncio.run(skill.send_email(to, subject, body, is_html=is_html))
            return json.dumps(result, ensure_ascii=False)

    class DraftInquiryInput(BaseModel):
        address: str = Field(description="Property address")
        price: str = Field(default="N/A", description="Property price")
        agent_name: str = Field(default="Agent", description="Agent name")
        agent_email: str = Field(description="Agent email")

    class DraftInquiryTool(BaseTool):
        name: str = "draft_property_inquiry"
        description: str = "Draft an email to inquire about a property."
        args_schema: type = DraftInquiryInput

        def _run(self, address: str, price: str = "N/A", agent_name: str = "Agent", agent_email: str = "") -> str:
            import asyncio
            skill = EmailSkill()
            result = asyncio.run(skill.draft_property_inquiry({
                "address": address, "price": price,
                "agent_name": agent_name, "agent_email": agent_email,
            }))
            return json.dumps(result, ensure_ascii=False)

    return [SendEmailTool(), DraftInquiryTool()]
