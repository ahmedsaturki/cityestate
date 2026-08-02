"""
Campaign Log
============
Append-only CSV audit trail for outreach campaigns.
Tracks every message dispatched with full metadata.

Architecture Decision:
- Append-only CSV for simplicity and portability (no DB dependency for logs)
- Timestamped records for temporal analysis
- Separate from database to avoid I/O contention during high-throughput dispatch
"""

import csv
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("outreach.campaign_log")

# CSV column schema
LOG_FIELDS = [
    "lead_id",
    "lead_type",
    "segment",
    "channel",
    "subject",
    "body_preview",
    "status",
    "timestamp",
    "message_source",
]


class CampaignLog:
    """Append-only CSV writer for outreach campaign records.

    Each record captures: who was contacted, via which channel, with what message,
    and whether it succeeded. Enables post-campaign analytics without database queries.
    """

    def __init__(self, output_dir: Path) -> None:
        """
        Args:
            output_dir: Directory for outreach_log.csv (created if absent).
        """
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.output_dir / "outreach_log.csv"
        self._ensure_header()
        self._record_count: int = 0

    def _ensure_header(self) -> None:
        """Write CSV header if file doesn't exist or is empty."""
        if not self.log_path.exists() or self.log_path.stat().st_size == 0:
            with open(self.log_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=LOG_FIELDS)
                writer.writeheader()
            logger.debug("Created campaign log: %s", self.log_path)

    def log(
        self,
        lead_id: int,
        lead_type: str,
        segment: str,
        channel: str,
        subject: str,
        body: str,
        status: str,
        message_source: str = "template",
    ) -> None:
        """Append a campaign record to the log.

        Args:
            lead_id: Database lead ID.
            lead_type: Lead classification (Developer, Investor, etc.).
            segment: Template segment used (diaspora, investor, etc.).
            channel: Dispatch channel (email, sms, whatsapp).
            subject: Message subject line (email) or empty string.
            body: Full message body (truncated to 500 chars for preview).
            status: Dispatch status (sent, dry_run, failed).
            message_source: Message origin (template or llm).
        """
        # Truncate body for CSV readability
        body_preview = body[:500] + "..." if len(body) > 500 else body
        # Strip newlines from body for CSV compatibility
        body_preview = body_preview.replace("\n", " ").replace("\r", "")

        record = {
            "lead_id": lead_id,
            "lead_type": lead_type or "Unknown",
            "segment": segment,
            "channel": channel,
            "subject": (subject or "").replace("\n", " ").replace("\r", ""),
            "body_preview": body_preview,
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message_source": message_source,
        }

        try:
            with open(self.log_path, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=LOG_FIELDS)
                writer.writerow(record)
            self._record_count += 1
        except OSError as e:
            logger.error("Failed to write campaign log: %s", e)

    def get_stats(self) -> dict:
        """Read the log file and compute summary statistics.

        Returns:
            Dict with counts by segment, channel, status, and message_source.
        """
        stats: dict = {
            "total_records": 0,
            "by_segment": {},
            "by_channel": {},
            "by_status": {},
            "by_source": {},
        }

        if not self.log_path.exists():
            return stats

        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    stats["total_records"] += 1

                    segment = row.get("segment", "unknown")
                    stats["by_segment"][segment] = stats["by_segment"].get(segment, 0) + 1

                    channel = row.get("channel", "unknown")
                    stats["by_channel"][channel] = stats["by_channel"].get(channel, 0) + 1

                    status = row.get("status", "unknown")
                    stats["by_status"][status] = stats["by_status"].get(status, 0) + 1

                    source = row.get("message_source", "unknown")
                    stats["by_source"][source] = stats["by_source"].get(source, 0) + 1

        except (OSError, csv.Error) as e:
            logger.error("Failed to read campaign log: %s", e)

        return stats

    def get_records(
        self,
        lead_id: int | None = None,
        segment: str | None = None,
        channel: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """Query log records with optional filters.

        Args:
            lead_id: Filter by lead ID.
            segment: Filter by segment.
            channel: Filter by channel.
            limit: Maximum records to return.

        Returns:
            List of matching record dicts.
        """
        records: list[dict] = []

        if not self.log_path.exists():
            return records

        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if lead_id is not None and row.get("lead_id") != str(lead_id):
                        continue
                    if segment and row.get("segment") != segment:
                        continue
                    if channel and row.get("channel") != channel:
                        continue

                    records.append(row)
                    if len(records) >= limit:
                        break

        except (OSError, csv.Error) as e:
            logger.error("Failed to query campaign log: %s", e)

        return records
