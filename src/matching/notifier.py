"""
Match Notifier — إشعارات المطابقة
===================================
Send notifications when matches are found.
Supports both log-only and live WhatsApp dispatch modes.
"""

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from src.database.models import ClientRequest, MessageLog, Property

logger = logging.getLogger("matching.notifier")

# Minimum match score to trigger live WhatsApp dispatch
LIVE_DISPATCH_THRESHOLD = 0.6


class MatchNotifier:
    """Send match notifications via various channels."""

    def __init__(self, db: Session):
        self.db = db

    def notify_whatsapp(
        self,
        request: ClientRequest,
        property: Property,
        score: float,
        live: bool = False,
    ) -> dict:
        """Send WhatsApp notification for a match.

        Args:
            request: The client request.
            property: The matched property.
            score: Match score (0.0–1.0).
            live: If True and score >= threshold, actually send via WhatsAppExpert.
        """
        message = self._build_message(request, property, score)

        # Always log the message
        log = MessageLog(
            lead_id=None,
            property_id=property.id,
            client_request_id=request.id,
            channel="whatsapp",
            message=message,
            message_type="text",
            status="pending",
            phone=request.phone,
            recipient_name=request.client_name,
            campaign_name="auto_match",
        )
        self.db.add(log)

        send_result = {"status": "logged", "channel": "whatsapp"}

        # Live dispatch
        if live and request.phone and score >= LIVE_DISPATCH_THRESHOLD:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Already inside an async context — schedule as task
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        result = pool.submit(
                            asyncio.run,
                            self._send_live(request.phone, message),
                        ).result(timeout=120)
                else:
                    result = loop.run_until_complete(
                        self._send_live(request.phone, message)
                    )
                send_result = result
            except Exception as e:
                logger.error("Live WhatsApp dispatch failed: %s", e)
                send_result = {"status": "dispatch_error", "error": str(e)}

        # Update request notification status
        request.notified_at = datetime.now(timezone.utc)
        request.notification_channel = "whatsapp"
        request.status = "notified"
        log.status = send_result.get("status", "logged")
        self.db.commit()

        return {
            **send_result,
            "phone": request.phone,
            "message_preview": message[:100] + "...",
            "log_id": log.id,
        }

    async def _send_live(self, phone: str, message: str) -> dict:
        """Send a message via WhatsAppExpert (async)."""
        from src.automation.experts import WhatsAppExpert

        expert = WhatsAppExpert(headless=True)
        try:
            connected = await expert.connect()
            if not connected:
                return {"status": "dispatch_failed", "error": "WhatsApp connection failed"}

            result = await expert.send_message(phone, message)
            await expert.disconnect()
            return result
        except Exception as e:
            try:
                await expert.disconnect()
            except Exception as e2:
                logger.debug("Failed to disconnect expert during cleanup: %s", e2)
            return {"status": "dispatch_error", "error": str(e)}

    def _build_message(self, request: ClientRequest, property: Property, score: float) -> str:
        """Build a notification message in Egyptian Arabic."""
        area = property.area or "غير محدد"
        price = f"{property.price:,.0f}"
        dev = property.developer or ""
        proj = property.project_name or ""

        msg = f"مرحبا {request.client_name}! \n\n"
        msg += f"عقار يناسب طلبك (مطابقة {score*100:.0f}%):\n\n"
        msg += f"📍 المنطقة: {area}\n"
        msg += f"💰 السعر: {price} جنيه\n"

        if dev:
            msg += f"🏢 المطور: {dev}\n"
        if proj:
            msg += f"🏗️ المشروع: {proj}\n"
        if property.bedrooms:
            msg += f"🛏️ غرف: {property.bedrooms}\n"
        if property.area_sqm:
            msg += f"📐 المساحة: {property.area_sqm} م²\n"

        msg += f"\n{property.title}\n"

        if property.payment_plan_details:
            msg += f"\n💳 خطة الدفع: {property.payment_plan_details}\n"

        msg += "\nللتواصل: رد على هذه الرسالة"
        return msg

    def notify_pending_matches(self, live: bool = False) -> dict:
        """Notify all pending matched requests.

        Args:
            live: If True, send actual WhatsApp messages (score >= threshold only).
        """
        pending = self.db.query(ClientRequest).filter(
            ClientRequest.status == "matched",
            ClientRequest.notified_at.is_(None),
        ).all()

        results = []
        for req in pending:
            if req.matched_property_id and req.phone:
                prop = self.db.query(Property).filter(
                    Property.id == req.matched_property_id
                ).first()
                if prop:
                    result = self.notify_whatsapp(req, prop, req.match_score or 0.5, live=live)
                    results.append(result)

        return {
            "total_pending": len(pending),
            "notified": len(results),
            "results": results,
        }
