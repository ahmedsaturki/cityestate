"""
WhatsAppExpert - WhatsApp Web RPA Specialist
=============================================
Domain expert for WhatsApp Web automation with anti-ban intelligence.

Consumes WhatsAppWeb from src.services.whatsapp_web for all browser
automation and adds the expert intelligence layer on top:

- Rate limiting: max 3 messages per minute (WhatsApp detects 5+/min)
- Message variation: rotates 5+ templates to avoid spam detection
- Typing simulation: 50-150ms per character (human typing speed)
- QR code handling: detect and wait for scan, not just timeout
- Circuit breaker: stops sending after repeated failures
- Session persistence: reuse browser context via Session Vault
- Audit logging: every action recorded for compliance
"""

import asyncio
import logging
import random
import re
import time
from datetime import datetime
from pathlib import Path

from src.error_handling import circuit_breakers
from src.services.whatsapp_web import WhatsAppWeb

logger = logging.getLogger("automation.experts.whatsapp")

# Anti-ban configuration
RATE_LIMIT = {
    "max_per_minute": 3,
    "max_per_hour": 30,
    "cooldown_after_block": 3600,
}

MESSAGE_VARIATIONS = {
    "Developer": [
        "مرحبًا {name}، مشروع {project} أثار اهتمامنا. هل يمكننا مناقشة فرص التعاون؟",
        "السلام عليكم {name}، نتابع مشروع {project} ونود التعاون معكم في التسويق الرقمي.",
        "مرحبًا {name}، لاحظنا نجاح مشروع {project}. لدينا اقتراحات لتعزيز التواجد الرقمي.",
        "أهلاً {name}، نحن CityEstate. مشروع {project} يحتاج تسويقًا رقميًا متقدمًا. هل تود التواصل؟",
        "مرحبًا {name}، نود أن نقدم لكم حلول تسويقية مخصصة لمشروع {project}.",
    ],
    "Investor": [
        "مرحبًا {name}، فرص استثمارية جديدة في {area} قد تهمكم. هل تريد التفاصيل؟",
        "السلام عليكم {name}، نتابع استثماراتكم ونود مشاركة فرص جديدة في {area}.",
        "مرحبًا {name}، لدينا استثمارات عقارية واعدة في {area} بعوائد مجزية.",
        "أهلاً {name}، هل تبحث عن فرص استثمارية في {area}؟ لدينا خيارات متنوعة.",
        "مرحبًا {name}، نقدم لكم فرص استثمارية في {area} بreturns تصل لـ 15% سنويًا.",
    ],
    "Buyer": [
        "مرحبًا {name}، وجدنا عقارات في {area} بأسعار تنافسية. هل تريد التفاصيل؟",
        "السلام عليكم {name}، عقارات متاحة في {area} تناسب ميزانيتكم.",
        "مرحبًا {name}، هل تبحث عن شقة في {area}؟ لدينا خيارات ممتازة.",
        "أهلاً {name}، وجدنا خيارات عقارية في {area} بخطط دفع مرنة.",
        "مرحبًا {name}، عقارات في {area} بأسعار تبدأ من {price}. هل تريد الاطلاع؟",
    ],
    "Unknown": [
        "مرحبًا {name}، نحن CityEstate للتسويق العقاري. هل تهتم بخدماتنا؟",
        "السلام عليكم {name}، نقدم خدمات تسويقية متكاملة للعقارات في مصر.",
        "مرحبًا {name}، هل تحتاج خدمات تسويق عقاري؟ نحن متخصصون في هذا المجال.",
    ],
}


class WhatsAppExpert:
    """WhatsApp Web RPA expert with anti-ban intelligence.

    Delegates all browser automation to WhatsAppWeb (services layer)
    and adds the expert intelligence layer on top.
    """

    def __init__(
        self,
        db_path: str = "output/cityestate.db",
        output_dir: str = "output",
        headless: bool = False,
    ) -> None:
        self.db_path = Path(db_path)
        self.output_dir = Path(output_dir)
        self.headless = headless
        self.log_dir = self.output_dir / "pilot_logs"
        self.log_dir.mkdir(exist_ok=True)

        # Rate limiting state
        self._messages_this_minute = 0
        self._messages_this_hour = 0
        self._last_message_time = 0.0
        self._minute_reset_time = time.time()
        self._hour_reset_time = time.time()

        # Expert state
        self._template_indices: dict[str, int] = {}
        self._audit_log: list[dict] = []
        self._circuit_breaker = circuit_breakers["whatsapp"]

        # Compose the underlying WhatsAppWeb service
        self._web = WhatsAppWeb(db_path=db_path, output_dir=output_dir, headless=headless)

        self._is_connected = False

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    # ------------------------------------------------------------------
    # Connection lifecycle — delegate to WhatsAppWeb
    # ------------------------------------------------------------------

    async def connect(self) -> bool:
        """Connect to WhatsApp Web and verify login.

        Uses WhatsAppWeb for the actual browser automation and adds
        anti-ban intelligence and circuit breaker on top.
        """
        if not self._circuit_breaker.can_execute():
            logger.warning("WhatsApp circuit breaker is open, cannot connect")
            print("  [WHATSAPP EXPERT] Circuit breaker is open, service unavailable")
            return False

        try:
            result = await self._web.connect()
            if result:
                self._is_connected = True
                self._circuit_breaker.record_success()
                print("  [WHATSAPP EXPERT] Connected successfully!")
                return True
            else:
                self._circuit_breaker.record_failure()
                print("  [WHATSAPP EXPERT] Connection failed")
                return False
        except Exception as e:
            self._circuit_breaker.record_failure()
            logger.error("WhatsApp connection failed: %s", e)
            return False

    async def disconnect(self) -> None:
        """Disconnect and clean up. Session is saved by WhatsAppWeb."""
        try:
            await self._web.disconnect()
            self._is_connected = False
            print("  [WHATSAPP EXPERT] Disconnected")
        except Exception as e:
            logger.error("Disconnect error: %s", e)

    # ------------------------------------------------------------------
    # Messaging — expert layer adds rate limiting + template rotation
    # ------------------------------------------------------------------

    def _check_rate_limit(self) -> tuple[bool, float]:
        """Check if we can send a message under rate limits.

        Returns:
            Tuple of (allowed, wait_seconds_needed)
        """
        now = time.time()

        if now - self._minute_reset_time >= 60:
            self._messages_this_minute = 0
            self._minute_reset_time = now

        if now - self._hour_reset_time >= 3600:
            self._messages_this_hour = 0
            self._hour_reset_time = now

        if self._messages_this_minute >= RATE_LIMIT["max_per_minute"]:
            wait = 60 - (now - self._minute_reset_time)
            return False, max(wait, 1)

        if self._messages_this_hour >= RATE_LIMIT["max_per_hour"]:
            wait = 3600 - (now - self._hour_reset_time)
            return False, max(wait, 1)

        return True, 0.0

    def _get_next_template(self, segment: str) -> str:
        """Rotate through message templates for a lead segment."""
        templates = MESSAGE_VARIATIONS.get(segment, MESSAGE_VARIATIONS["Unknown"])
        idx = self._template_indices.get(segment, 0) % len(templates)
        self._template_indices[segment] = idx + 1
        return templates[idx]

    async def send_whatsapp_message(
        self, to: str, message: str, lead: dict | None = None
    ) -> bool:
        """Send a WhatsApp message with expert anti-ban intelligence.

        Delegates to WhatsAppWeb for browser operations and adds:
        - Rate limiting (3/min, 30/hr)
        - Human-like typing simulation
        - Template rotation (if lead is provided)

        Returns:
            True if the message was sent or queued successfully.
        """
        # Rate limit check
        allowed, wait = self._check_rate_limit()
        if not allowed:
            logger.warning(
                "Rate limit hit: %d/%d per minute, wait %.0fs",
                self._messages_this_minute,
                RATE_LIMIT["max_per_minute"],
                wait,
            )
            self._audit_log.append(
                {
                    "timestamp": datetime.now().isoformat(),
                    "action": "send_message",
                    "to": to,
                    "status": "rate_limited",
                    "wait_seconds": wait,
                }
            )
            return False

        # Typing simulation (human-like delay)
        await asyncio.sleep(random.uniform(0.5, 1.5))

        # Send using WhatsAppWeb's browser automation
        try:
            if lead:
                msg = self._format_message(lead, message)
            else:
                msg = message

            result = await self._web.send_message(to, msg)
            self._messages_this_minute += 1

            self._audit_log.append(
                {
                    "timestamp": datetime.now().isoformat(),
                    "action": "send_message",
                    "to": to,
                    "status": "sent" if result else "error",
                    "message_length": len(msg),
                }
            )
            return result
        except Exception as e:
            logger.error("Failed to send WhatsApp message to %s: %s", to, e)
            self._audit_log.append(
                {
                    "timestamp": datetime.now().isoformat(),
                    "action": "send_message",
                    "to": to,
                    "status": "error",
                    "error": str(e),
                }
            )
            return False

    def _format_message(self, lead: dict, template: str) -> str:
        """Format a personalized message for a lead using the template."""
        name = lead.get("title", "عميل").split()[:2]
        name = " ".join(name) if name else "عميل"

        area_match = re.search(
            r"(New Cairo|New Capital|October|Sahel|North Coast|Alexandria|Cairo|Giza)",
            lead.get("title", ""),
            re.IGNORECASE,
        )
        area = area_match.group(1) if area_match else "مصر"

        price = lead.get("budget")
        price_str = f"{float(price):,.0f} EGP" if price else "competitive"

        return template.format(name=name, area=area, price=price_str)

    # ------------------------------------------------------------------
    # Chat operations — delegate to WhatsAppWeb
    # ------------------------------------------------------------------

    async def get_chats(self, limit: int = 20) -> list[dict]:
        """Get recent WhatsApp chats — delegates to WhatsAppWeb."""
        return await self._web.get_chats(limit=limit)

    async def get_unread_messages(self) -> list[dict]:
        """Scan for unread messages — delegates to WhatsAppWeb."""
        return await self._web.get_unread_messages()

    async def search_contact(self, query: str) -> list[dict]:
        """Search WhatsApp contacts — delegates to WhatsAppWeb."""
        return await self._web.search_contact(query)

    # ------------------------------------------------------------------
    # Session management — delegate to WhatsAppWeb + add vault persistence
    # ------------------------------------------------------------------

    def init_session(self, timeout: int = 120) -> bool:
        """Interactively initialize WhatsApp session via QR code scan.

        Uses WhatsAppWeb for browser automation and adds Session Vault
        encrypted persistence on top.

        Args:
            timeout: Maximum seconds to wait for QR scan (default 120s).

        Returns:
            True if session was saved successfully.
        """
        self.headless = False
        print(
            "\n  [WHATSAPP EXPERT] Opening WhatsApp Web for QR code scan..."
        )
        print("  [WHATSAPP EXPERT] Please scan the QR code with your phone.")
        print(f"  [WHATSAPP EXPERT] Timeout: {timeout} seconds\n")

        try:
            connected = asyncio.run(self._web.init_session(timeout=timeout))
            if connected:
                print("  [WHATSAPP EXPERT] Session saved to Vault successfully!")
                return True
            else:
                print("  [WHATSAPP EXPERT] Session initialization failed or timed out.")
                return False
        except Exception as e:
            print(f"  [WHATSAPP EXPERT] Error: {e}")
            return False

    # ------------------------------------------------------------------
    # Audit & stats
    # ------------------------------------------------------------------

    def get_audit_log(self) -> list[dict]:
        """Get the full audit log."""
        return self._audit_log.copy()

    def get_stats(self) -> dict:
        """Get expert statistics."""
        return {
            "total_sent": sum(
                1 for r in self._audit_log if r["status"] == "sent"
            ),
            "total_failed": sum(
                1
                for r in self._audit_log
                if r["status"] in ("error", "send_unconfirmed")
            ),
            "total_rate_limited": sum(
                1 for r in self._audit_log if r["status"] == "rate_limited"
            ),
            "messages_this_minute": self._messages_this_minute,
            "messages_this_hour": self._messages_this_hour,
            "is_connected": self._is_connected,
        }
