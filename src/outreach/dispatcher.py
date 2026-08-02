"""
Message Dispatcher
==================
Channel-specific message formatting and dispatch with real WhatsApp integration.
Enforces channel constraints and writes audit records.

Architecture:
- Real dispatch via WhatsAppExpert when live_mode=True
- Simulated dispatch in dry_run mode
- Each channel has specific formatting rules and length limits
- All dispatches logged to CampaignLog for audit trail
"""

import logging
from datetime import datetime, timezone
from pathlib import Path

from .campaign_log import CampaignLog

logger = logging.getLogger("outreach.dispatcher")

# Channel constraints
CHANNEL_LIMITS: dict[str, dict[str, int]] = {
    "email": {"subject_max": 200, "body_max": 2000},
    "sms": {"subject_max": 0, "body_max": 160},
    "whatsapp": {"subject_max": 0, "body_max": 500},
}


class Dispatcher:
    """Multi-channel message dispatcher with format enforcement and logging.

    Supports both dry-run mode (simulation) and live mode (real dispatch).
    Integrates with circuit breakers to prevent cascading failures.
    """

    def __init__(
        self,
        output_dir: Path,
        dry_run: bool = True,
        live_mode: bool = False,
        whatsapp_expert=None,
        whatsapp_circuit_breaker=None,
    ) -> None:
        """
        Args:
            output_dir: Directory for campaign logs.
            dry_run: If True, log as dry_run without actual dispatch.
            live_mode: If True, actually send messages via WhatsAppExpert.
            whatsapp_expert: WhatsAppExpert instance for live dispatch.
            whatsapp_circuit_breaker: CircuitBreaker for WhatsApp calls.
        """
        self.output_dir = output_dir
        self.dry_run = dry_run
        self.live_mode = live_mode
        self.whatsapp_expert = whatsapp_expert
        self.whatsapp_circuit_breaker = whatsapp_circuit_breaker
        self.log = CampaignLog(output_dir)
        self._dispatch_count: int = 0
        self._success_count: int = 0
        self._fail_count: int = 0

    def _truncate(self, text: str, max_length: int) -> str:
        """Truncate text to max_length with ellipsis."""
        if len(text) <= max_length:
            return text
        return text[: max_length - 3] + "..."

    def _format_email(self, subject: str, body: str) -> dict[str, str]:
        """Format and enforce email constraints."""
        limits = CHANNEL_LIMITS["email"]
        return {
            "subject": self._truncate(subject or "Real Estate Update", limits["subject_max"]),
            "body": self._truncate(body, limits["body_max"]),
        }

    def _format_sms(self, subject: str, body: str) -> dict[str, str]:
        """Format and enforce SMS constraints (160 chars)."""
        limits = CHANNEL_LIMITS["sms"]
        return {
            "subject": "",
            "body": self._truncate(body, limits["body_max"]),
        }

    def _format_whatsapp(self, subject: str, body: str) -> dict[str, str]:
        """Format and enforce WhatsApp constraints (500 chars)."""
        limits = CHANNEL_LIMITS["whatsapp"]
        return {
            "subject": "",
            "body": self._truncate(body, limits["body_max"]),
        }

    def _format_for_channel(self, channel: str, subject: str, body: str) -> dict[str, str]:
        """Route to channel-specific formatter."""
        formatters = {
            "email": self._format_email,
            "sms": self._format_sms,
            "whatsapp": self._format_whatsapp,
        }
        formatter = formatters.get(channel, self._format_email)
        return formatter(subject, body)

    def dispatch(
        self,
        lead_id: int,
        lead_type: str,
        segment: str,
        channel: str,
        subject: str,
        body: str,
        message_source: str = "template",
        phone: str | None = None,
    ) -> dict:
        """Dispatch a message to a lead via specified channel.

        In dry-run mode, logs the attempt without sending.
        In live mode, actually sends via WhatsAppExpert with circuit breaker protection.

        Args:
            lead_id: Database lead ID.
            lead_type: Lead classification.
            segment: Template segment used.
            channel: Dispatch channel (email, sms, whatsapp).
            subject: Message subject (email only).
            body: Message body.
            message_source: Origin (template or llm).
            phone: Phone number for WhatsApp dispatch.

        Returns:
            Dict with status, channel, timestamp, and formatted preview.
        """
        import asyncio
        
        self._dispatch_count += 1
        timestamp = datetime.now(timezone.utc).isoformat()

        # Format for channel
        formatted = self._format_for_channel(channel, subject, body)

        # Determine status and send if live mode
        if self.dry_run:
            status = "dry_run"
        elif self.live_mode and channel == "whatsapp" and phone and self.whatsapp_expert:
            # Real WhatsApp dispatch with circuit breaker protection
            try:
                if self.whatsapp_circuit_breaker and not self.whatsapp_circuit_breaker.can_execute():
                    status = "circuit_open"
                    self._fail_count += 1
                    logger.warning(
                        "WhatsApp circuit breaker OPEN — skipping dispatch to lead %d",
                        lead_id,
                    )
                else:
                    result = asyncio.run(
                        self.whatsapp_expert.send_message(phone, formatted["body"])
                    )
                    if result.get("status") == "sent":
                        status = "sent"
                        self._success_count += 1
                        if self.whatsapp_circuit_breaker:
                            self.whatsapp_circuit_breaker.record_success()
                    else:
                        status = "failed"
                        self._fail_count += 1
                        if self.whatsapp_circuit_breaker:
                            self.whatsapp_circuit_breaker.record_failure()
                        logger.warning("WhatsApp dispatch failed: %s", result.get("error"))
            except Exception as e:
                status = "failed"
                self._fail_count += 1
                if self.whatsapp_circuit_breaker:
                    self.whatsapp_circuit_breaker.record_failure()
                logger.error("WhatsApp dispatch error: %s", e)
        else:
            # Simulated dispatch (non-WhatsApp or no expert)
            status = "sent"
            self._success_count += 1

        # Log to campaign audit trail
        self.log.log(
            lead_id=lead_id,
            lead_type=lead_type,
            segment=segment,
            channel=channel,
            subject=formatted["subject"],
            body=formatted["body"],
            status=status,
            message_source=message_source,
        )

        if status == "sent":
            logger.info(
                "Dispatched %s to lead %d via %s [%s]",
                channel, lead_id, segment, message_source,
            )
        elif status == "dry_run":
            logger.debug(
                "[DRY RUN] Would dispatch %s to lead %d via %s",
                channel, lead_id, segment,
            )
        elif status == "circuit_open":
            pass  # already logged above
        else:
            logger.warning(
                "Failed to dispatch %s to lead %d via %s",
                channel, lead_id, segment,
            )

        return {
            "status": status,
            "channel": channel,
            "timestamp": timestamp,
            "preview": {
                "subject": formatted["subject"],
                "body_preview": formatted["body"][:100] + "..." if len(formatted["body"]) > 100 else formatted["body"],
            },
        }

    def dispatch_all_channels(
        self,
        lead_id: int,
        lead_type: str,
        segment: str,
        messages: dict[str, dict[str, str]],
        message_source: str = "template",
    ) -> list[dict]:
        """Dispatch messages across all channels for a single lead.

        Args:
            lead_id: Database lead ID.
            lead_type: Lead classification.
            segment: Template segment.
            messages: Dict mapping channel name to {subject, body}.
            message_source: Origin (template or llm).

        Returns:
            List of dispatch result dicts.
        """
        results = []
        for channel, msg in messages.items():
            result = self.dispatch(
                lead_id=lead_id,
                lead_type=lead_type,
                segment=segment,
                channel=channel,
                subject=msg.get("subject", ""),
                body=msg.get("body", ""),
                message_source=message_source,
            )
            results.append(result)
        return results

    @property
    def stats(self) -> dict:
        """Dispatcher usage statistics."""
        return {
            "total_dispatches": self._dispatch_count,
            "successful": self._success_count,
            "failed": self._fail_count,
            "dry_run_mode": self.dry_run,
        }
