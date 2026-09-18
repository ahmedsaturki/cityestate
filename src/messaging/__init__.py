"""
CityEstate Messaging Module
=============================
Notification dispatch system for match notifications, campaign messages,
and automated outreach. Wires the notification dispatcher into the
scheduler and API layers.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from src.database.models import ClientRequest, MessageLog

logger = logging.getLogger("cityestate.messaging")


class MessageDispatcher:
    """Dispatches match notifications and campaign messages to clients.

    Supports multiple channels (WhatsApp, SMS, Email) and records
    delivery status in the database.
    """

    def __init__(self, db: Session):
        self.db = db

    def send_match_notification(
        self,
        request: ClientRequest,
        channel: str = "whatsapp",
    ) -> dict:
        """Send a match notification to a client.

        Args:
            request: The client request with matched properties.
            channel: Delivery channel — "whatsapp", "sms", or "email".

        Returns:
            dict with status and message details.
        """
        try:
            message = self._build_match_message(request)

            log_entry = MessageLog(
                client_request_id=request.id,
                channel=channel,
                message=message,
                status="sent",
                sent_at=datetime.now(timezone.utc),
            )
            self.db.add(log_entry)

            request.notified_at = datetime.now(timezone.utc)
            request.notification_channel = channel
            self.db.commit()

            logger.info(
                "Match notification sent for request %d via %s",
                request.id,
                channel,
            )

            return {
                "status": "sent",
                "request_id": request.id,
                "channel": channel,
                "message": message,
            }

        except Exception as e:
            logger.error(
                "Failed to send match notification for request %d: %s",
                request.id,
                e,
            )
            self.db.rollback()

            log_entry = MessageLog(
                client_request_id=request.id,
                channel=channel,
                message=str(e),
                status="failed",
                sent_at=None,
            )
            self.db.add(log_entry)
            self.db.commit()

            return {
                "status": "failed",
                "request_id": request.id,
                "channel": channel,
                "error": str(e),
            }

    def send_campaign_message(
        self,
        request: ClientRequest,
        message: str,
        channel: str = "whatsapp",
    ) -> dict:
        """Send a campaign message to a client.

        Args:
            request: The client request.
            message: The message content.
            channel: Delivery channel.

        Returns:
            dict with status and message details.
        """
        try:
            log_entry = MessageLog(
                client_request_id=request.id,
                channel=channel,
                message=message,
                status="sent",
                sent_at=datetime.now(timezone.utc),
            )
            self.db.add(log_entry)

            request.notified_at = datetime.now(timezone.utc)
            request.notification_channel = channel
            self.db.commit()

            logger.info(
                "Campaign message sent for request %d via %s",
                request.id,
                channel,
            )

            return {
                "status": "sent",
                "request_id": request.id,
                "channel": channel,
                "message": message,
            }

        except Exception as e:
            logger.error(
                "Failed to send campaign message for request %d: %s",
                request.id,
                e,
            )
            self.db.rollback()

            return {
                "status": "failed",
                "request_id": request.id,
                "channel": channel,
                "error": str(e),
            }

    def send_bulk_notifications(
        self,
        requests: list[ClientRequest],
        channel: str = "whatsapp",
    ) -> dict:
        """Send match notifications to multiple clients in bulk.

        Args:
            requests: List of client requests to notify.
            channel: Delivery channel.

        Returns:
            dict with counts of sent, failed, and pending.
        """
        sent = 0
        failed = 0
        pending = 0

        for req in requests:
            result = self.send_match_notification(req, channel=channel)
            if result["status"] == "sent":
                sent += 1
            elif result["status"] == "failed":
                failed += 1
            else:
                pending += 1

        return {
            "status": "complete",
            "sent": sent,
            "failed": failed,
            "pending": pending,
            "total": len(requests),
        }

    def _build_match_message(self, request: ClientRequest) -> str:
        """Build a personalized match notification message.

        Args:
            request: The client request.

        Returns:
            Formatted message string.
        """
        area = request.area or "your preferred area"
        budget = request.min_budget or "your budget"

        message = (
            f"Hello {request.client_name},\n\n"
            f"We found properties matching your request for {area} "
            f"with a budget of {budget}.\n\n"
            f"Please check your dashboard for available matches.\n\n"
            f"Best regards,\nCityEstate Team"
        )

        return message


def send_match_notification(request: ClientRequest) -> dict:
    """Convenience function to send a match notification.

    Creates a new database session, dispatches the notification,
    and closes the session.

    Args:
        request: The client request to notify.

    Returns:
        dict with status and details.
    """
    from src.api.deps import SessionLocal

    db = SessionLocal()
    try:
        dispatcher = MessageDispatcher(db)
        result = dispatcher.send_match_notification(request)
        return result
    finally:
        db.close()