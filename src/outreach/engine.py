"""
Outreach Engine
===============
Orchestrator that ties together LLM generation, templates, dispatch, rate limiting,
and campaign logging into a single run/preview pipeline.

Architecture:
  load leads → generate or template messages → dispatch with logging
  All simulated (no real emails/SMS/WhatsApp sent)
"""

import logging
from pathlib import Path

from .campaign_log import CampaignLog
from .dispatcher import Dispatcher
from .llm_generator import LLMGenerator
from .rate_limiter import TokenBucket
from .templates import get_template, inject_variables

logger = logging.getLogger("outreach.engine")

# Segment mapping: DB lead_type → template segment
SEGMENT_MAP: dict[str, str] = {
    "investor": "investor",
    "buyer": "buyer",
    "developer": "developer",
    "diaspora": "diaspora",
    "unknown": "unknown",
}


class OutreachEngine:
    """Multi-channel outreach orchestrator.

    Pipeline:
    1. Load leads from database
    2. Generate messages (LLM-first, template fallback)
    3. Dispatch to channels with rate limiting
    4. Log all activity to campaign audit trail
    """

    def __init__(
        self,
        db_path: str = "output/cityestate.db",
        output_dir: str = "output",
        use_llm: bool = True,
        dry_run: bool = True,
        api_key: str | None = None,
        model: str = "google/gemini-2.0-flash-exp:free",
        rate_limit_per_minute: int = 10,
    ) -> None:
        self.db_path = db_path
        self.output_dir = Path(output_dir)
        self.dry_run = dry_run
        self.use_llm = use_llm

        # Components
        self.llm = LLMGenerator(api_key=api_key, model=model) if use_llm else None
        self.dispatcher = Dispatcher(self.output_dir, dry_run=dry_run)
        self.rate_limiter = TokenBucket(max_tokens=rate_limit_per_minute, refill_rate=rate_limit_per_minute / 60.0)
        self.log = CampaignLog(self.output_dir)

        self._run_count = 0
        self._total_dispatched = 0
        self._total_templates = 0
        self._total_llm = 0

    def _load_leads(self) -> list[dict]:
        """Load leads from SQLite database."""
        import sqlite3
        db = Path(self.db_path)
        if not db.exists():
            logger.warning("Database not found: %s", self.db_path)
            return []

        try:
            conn = sqlite3.connect(str(db))
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT id, title, area, budget, interest, url, lead_type "
                "FROM leads WHERE id IS NOT NULL ORDER BY id"
            )
            leads = [dict(row) for row in cursor.fetchall()]
            conn.close()
            logger.info("Loaded %d leads from %s", len(leads), self.db_path)
            return leads
        except Exception as e:
            logger.error("Failed to load leads: %s", e)
            return []

    def _select_segment(self, lead: dict) -> str:
        """Map DB lead_type to template segment."""
        lead_type = str(lead.get("lead_type", "unknown")).lower().strip()
        return SEGMENT_MAP.get(lead_type, "unknown")

    def _generate_messages(self, lead: dict, segment: str) -> dict[str, dict[str, str]]:
        """Generate messages for all channels, using LLM or templates.

        Returns dict mapping channel to {subject, body}.
        """
        channels = ["email", "sms", "whatsapp"]
        messages = {}

        for channel in channels:
            if self.llm:
                # LLM-first
                result = self.llm.generate(lead, channel, segment)
                if result:
                    messages[channel] = result
                    self._total_llm += 1
                    continue

            # Template fallback
            template = get_template(segment, channel)
            if template:
                injected = inject_variables(template, lead)
                messages[channel] = injected
                self._total_templates += 1
            else:
                # Last resort: generic message
                messages[channel] = {
                    "subject": "Real Estate Update",
                    "body": f"Check out {lead.get('title', 'this opportunity')} in {lead.get('area', 'Cairo')}.",
                }
                self._total_templates += 1

        return messages

    def run(self, channels: list[str] | None = None, limit: int | None = None) -> dict:
        """Execute full outreach pipeline.

        Args:
            channels: Limit to specific channels (default: all three).
            limit: Maximum number of leads to process.

        Returns:
            Summary dict with counts and stats.
        """
        leads = self._load_leads()
        if not leads:
            return {"error": "No leads found in database"}

        if limit:
            leads = leads[:limit]

        segments_used: dict[str, int] = {}
        leads_processed = 0

        for lead in leads:
            segment = self._select_segment(lead)
            segments_used[segment] = segments_used.get(segment, 0) + 1

            # Rate limiting
            self.rate_limiter.acquire()

            # Generate messages
            messages = self._generate_messages(lead, segment)

            # Filter channels if specified
            if channels:
                messages = {ch: msg for ch, msg in messages.items() if ch in channels}

            # Dispatch
            for channel, msg in messages.items():
                self.dispatcher.dispatch(
                    lead_id=lead.get("id", 0),
                    lead_type=lead.get("lead_type", "unknown"),
                    segment=segment,
                    channel=channel,
                    subject=msg.get("subject", ""),
                    body=msg.get("body", ""),
                    message_source="llm" if self.llm and channel in messages else "template",
                )
                self._total_dispatched += 1

            leads_processed += 1
            self._run_count += 1

        return self._build_summary(leads_processed, segments_used)

    def _build_summary(self, leads_processed: int, segments_used: dict) -> dict:
        """Build run summary dict."""
        return {
            "leads_processed": leads_processed,
            "total_dispatched": self._total_dispatched,
            "llm_messages": self._total_llm,
            "template_messages": self._total_templates,
            "segments_used": segments_used,
            "dispatcher_stats": self.dispatcher.stats,
            "llm_stats": self.llm.stats if self.llm else {"requests": 0, "errors": 0},
            "dry_run": self.dry_run,
        }

    def preview(self, lead_index: int = 0, channel: str = "email") -> dict:
        """Preview message generation for a single lead without dispatching.

        Args:
            lead_index: Index of lead to preview (default: first lead).
            channel: Channel to preview (default: email).

        Returns:
            Dict with lead info, segment, and generated/template message.
        """
        leads = self._load_leads()
        if not leads:
            return {"error": "No leads found in database"}

        if lead_index >= len(leads):
            lead_index = 0

        lead = leads[lead_index]
        segment = self._select_segment(lead)
        messages = self._generate_messages(lead, segment)

        return {
            "lead": lead,
            "segment": segment,
            "channel": channel,
            "message": messages.get(channel, {"subject": "", "body": "No message generated"}),
            "available_channels": list(messages.keys()),
        }

    @property
    def stats(self) -> dict:
        """Engine-level statistics."""
        return {
            "total_runs": self._run_count,
            "total_dispatched": self._total_dispatched,
            "total_llm": self._total_llm,
            "total_templates": self._total_templates,
            "dry_run": self.dry_run,
        }
