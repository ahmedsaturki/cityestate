"""
Campaign Orchestrator - Unified Production Pipeline
====================================================
Combines Facebook Scraper → Lead Enrichment → WhatsApp Sender into one pipeline.

Usage:
    python scripts/campaign_orchestrator.py --mode full          # Full pipeline
    python scripts/campaign_orchestrator.py --mode scrape-only   # Just scrape
    python scripts/campaign_orchestrator.py --mode send-only     # Just send
    python scripts/campaign_orchestrator.py --dry-run            # Simulate
    python scripts/campaign_orchestrator.py --schedule           # Run every 6 hours
"""

import argparse
import asyncio
import json
import logging
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.automation.smart_wait import SmartWait, WaitResult
from src.automation.experts import (
    WhatsAppExpert,
    FacebookExpert,
    LeadClassifierExpert,
    MessageWriterExpert,
    PhoneValidatorExpert,
)

logger = logging.getLogger("campaign_orchestrator")

DB_PATH = PROJECT_ROOT / "output" / "cityestate.db"
LOG_DIR = PROJECT_ROOT / "output" / "campaign_logs"
LOG_DIR.mkdir(exist_ok=True)


class CampaignOrchestrator:
    """Unified campaign pipeline: Scrape → Enrich → Send → Log.

    This orchestrator:
    - Runs the full pipeline or individual stages
    - Uses Expert Agents for each stage
    - Validates state at every transition
    - Logs all activity for audit
    - Supports scheduled runs (every 6 hours)
    """

    def __init__(
        self,
        dry_run: bool = True,
        headless: bool = False,
        max_messages_per_run: int = 10,
    ) -> None:
        self.dry_run = dry_run
        self.headless = headless
        self.max_messages_per_run = max_messages_per_run

        # Initialize experts
        self.facebook = FacebookExpert(
            db_path=str(DB_PATH),
            output_dir=str(PROJECT_ROOT / "output"),
            headless=headless,
        )
        self.whatsapp = WhatsAppExpert(
            db_path=str(DB_PATH),
            output_dir=str(PROJECT_ROOT / "output"),
            headless=headless,
        )
        self.classifier = LeadClassifierExpert()
        self.writer = MessageWriterExpert()
        self.phone_validator = PhoneValidatorExpert()

        # Pipeline state
        self._run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._stats = {
            "scraped": 0,
            "classified": 0,
            "enriched": 0,
            "sent": 0,
            "failed": 0,
            "rate_limited": 0,
        }
        self._stage_results: dict[str, dict] = {}

    def _log_stage(self, stage: str, result: dict) -> None:
        """Log stage result."""
        self._stage_results[stage] = {
            "timestamp": datetime.now().isoformat(),
            **result,
        }
        logger.info("Stage %s completed: %s", stage, result)

    async def stage_scrape(self, group_urls: list[str] = None, max_posts: int = 50) -> dict:
        """Stage 1: Scrape Facebook Groups for new leads."""
        print("\n" + "=" * 60)
        print("STAGE 1: SCRAPING FACEBOOK GROUPS")
        print("=" * 60)

        if self.dry_run:
            print("  [DRY RUN] Would scrape Facebook groups")
            result = {"status": "dry_run", "leads_found": 0}
            self._log_stage("scrape", result)
            return result

        # Connect to Facebook
        connected = await self.facebook.connect()
        if not connected:
            result = {"status": "failed", "error": "Facebook connection failed"}
            self._log_stage("scrape", result)
            return result

        # Default groups if none specified
        if not group_urls:
            group_urls = [
                "https://www.facebook.com/groups/real.estate.egypt",
                "https://www.facebook.com/groups/properties.for.sale.in.egypt",
                "https://www.facebook.com/groups/egypt.real.estate.investors",
            ]

        # Scrape
        leads = await self.facebook.scrape_multiple_groups(group_urls, max_posts)
        self._stats["scraped"] = len(leads)

        await self.facebook.disconnect()

        result = {
            "status": "success",
            "leads_found": len(leads),
            "groups_scraped": len(group_urls),
        }
        self._log_stage("scrape", result)
        print(f"\n  Scraped {len(leads)} leads from {len(group_urls)} groups")
        return result

    def stage_enrich(self) -> dict:
        """Stage 2: Enrich and classify leads."""
        print("\n" + "=" * 60)
        print("STAGE 2: ENRICHING & CLASSIFYING LEADS")
        print("=" * 60)

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get unclassified or Unknown leads
        cursor.execute("""
            SELECT id, title, url, source, lead_type, phone, email, score
            FROM leads
            WHERE lead_type = 'Unknown' OR lead_type IS NULL
        """)
        leads = [dict(row) for row in cursor.fetchall()]

        print(f"  Found {len(leads)} unclassified leads")

        classified = 0
        enriched = 0

        for lead in leads:
            # Classify
            result = self.classifier.classify(lead)
            new_type = result["lead_type"]
            confidence = result["confidence"]

            # Validate phone if exists
            phone_valid = True
            if lead.get("phone"):
                phone_result = self.phone_validator.validate(lead["phone"])
                phone_valid = phone_result["is_valid"]
                if phone_result["normalized"] and phone_result["normalized"] != lead["phone"]:
                    # Update to normalized format
                    cursor.execute(
                        "UPDATE leads SET phone = ? WHERE id = ?",
                        (phone_result["normalized"], lead["id"])
                    )
                    enriched += 1

            # Update classification
            if new_type != "Unknown" and confidence in ("high", "medium"):
                cursor.execute(
                    "UPDATE leads SET lead_type = ?, score = ? WHERE id = ?",
                    (new_type, lead.get("score", 50), lead["id"])
                )
                classified += 1
                print(f"    ID={lead['id']:3d} | {lead['lead_type']:12s} -> {new_type:12s} | conf={confidence}")

        conn.commit()
        conn.close()

        self._stats["classified"] = classified
        self._stats["enriched"] = enriched

        result = {
            "status": "success",
            "classified": classified,
            "enriched": enriched,
            "total_processed": len(leads),
        }
        self._log_stage("enrich", result)
        print(f"\n  Classified: {classified}, Enriched: {enriched}")
        return result

    async def stage_send(self, limit: int = None) -> dict:
        """Stage 3: Send messages via WhatsApp."""
        print("\n" + "=" * 60)
        print("STAGE 3: SENDING MESSAGES VIA WHATSAPP")
        print("=" * 60)

        if self.dry_run:
            print("  [DRY RUN] Would send WhatsApp messages")
            result = {"status": "dry_run", "sent": 0}
            self._log_stage("send", result)
            return result

        limit = limit or self.max_messages_per_run

        # Get top leads with phone numbers
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, title, lead_type, phone, email, score, area
            FROM leads
            WHERE phone IS NOT NULL AND phone != '' AND phone != 'None'
            AND (status IS NULL OR status != 'contacted')
            ORDER BY score DESC
            LIMIT ?
        """, (limit,))

        leads = [dict(row) for row in cursor.fetchall()]
        conn.close()

        if not leads:
            print("  No leads with phone numbers to contact")
            result = {"status": "no_leads", "sent": 0}
            self._log_stage("send", result)
            return result

        print(f"  Found {len(leads)} leads to contact")

        # Connect to WhatsApp
        connected = await self.whatsapp.connect()
        if not connected:
            result = {"status": "failed", "error": "WhatsApp connection failed"}
            self._log_stage("send", result)
            return result

        # Send messages
        results = await self.whatsapp.send_batch(leads)

        # Update database with status
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        for i, (lead, result) in enumerate(zip(leads, results)):
            status = "contacted" if result["status"] == "sent" else "failed"
            cursor.execute(
                "UPDATE leads SET status = ? WHERE id = ?",
                (status, lead["id"])
            )
        conn.commit()
        conn.close()

        await self.whatsapp.disconnect()

        sent_count = sum(1 for r in results if r["status"] == "sent")
        failed_count = sum(1 for r in results if r["status"] in ("error", "send_unconfirmed"))

        self._stats["sent"] = sent_count
        self._stats["failed"] = failed_count

        result = {
            "status": "success",
            "sent": sent_count,
            "failed": failed_count,
            "total": len(results),
        }
        self._log_stage("send", result)
        print(f"\n  Sent: {sent_count}, Failed: {failed_count}")
        return result

    async def run_full(self, group_urls: list[str] = None) -> dict:
        """Run the full pipeline: Scrape → Enrich → Send."""
        print("\n" + "=" * 60)
        print("CAMPAIGN ORCHESTRATOR - FULL PIPELINE")
        print(f"Run ID: {self._run_id}")
        print(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE'}")
        print("=" * 60)

        start_time = time.time()

        # Stage 1: Scrape
        scrape_result = await self.stage_scrape(group_urls)

        # Stage 2: Enrich
        enrich_result = self.stage_enrich()

        # Stage 3: Send
        send_result = await self.stage_send()

        # Build summary
        duration = time.time() - start_time
        summary = {
            "run_id": self._run_id,
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": round(duration, 2),
            "mode": "dry_run" if self.dry_run else "live",
            "stats": self._stats.copy(),
            "stages": self._stage_results,
        }

        # Save log
        log_file = LOG_DIR / f"run_{self._run_id}.json"
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        print("\n" + "=" * 60)
        print("PIPELINE COMPLETE")
        print("=" * 60)
        print(f"  Duration: {duration:.1f}s")
        print(f"  Scraped: {self._stats['scraped']}")
        print(f"  Classified: {self._stats['classified']}")
        print(f"  Sent: {self._stats['sent']}")
        print(f"  Failed: {self._stats['failed']}")
        print(f"  Log: {log_file}")

        return summary

    async def run_scrape_only(self, group_urls: list[str] = None) -> dict:
        """Run only the scraping stage."""
        return await self.stage_scrape(group_urls)

    async def run_enrich_only(self) -> dict:
        """Run only the enrichment stage."""
        return self.stage_enrich()

    async def run_send_only(self, limit: int = None) -> dict:
        """Run only the sending stage."""
        return await self.stage_send(limit)


async def schedule_loop(interval_hours: int = 6):
    """Run the orchestrator on a schedule."""
    print(f"\n  [SCHEDULE] Running every {interval_hours} hours")
    print("  Press Ctrl+C to stop\n")

    while True:
        try:
            orchestrator = CampaignOrchestrator(dry_run=False)
            await orchestrator.run_full()
            print(f"\n  [SCHEDULE] Next run in {interval_hours} hours...")
            await asyncio.sleep(interval_hours * 3600)
        except KeyboardInterrupt:
            print("\n  [SCHEDULE] Stopped by user")
            break
        except Exception as e:
            logger.error("Scheduled run failed: %s", e)
            print(f"\n  [ERROR] Run failed: {e}")
            print("  Retrying in 1 hour...")
            await asyncio.sleep(3600)


def main():
    parser = argparse.ArgumentParser(description="Campaign Orchestrator")
    parser.add_argument(
        "--mode",
        choices=["full", "scrape-only", "enrich-only", "send-only"],
        default="full",
        help="Pipeline mode",
    )
    parser.add_argument("--dry-run", action="store_true", help="Simulate without sending")
    parser.add_argument("--live", action="store_true", help="Actually send messages")
    parser.add_argument("--count", type=int, default=10, help="Max messages to send")
    parser.add_argument("--schedule", action="store_true", help="Run on schedule (every 6 hours)")
    parser.add_argument("--interval", type=int, default=6, help="Hours between scheduled runs")
    parser.add_argument("--group", action="append", help="Facebook Group URL(s)")
    args = parser.parse_args()

    dry_run = not args.live

    if args.schedule:
        asyncio.run(schedule_loop(args.interval))
    else:
        orchestrator = CampaignOrchestrator(
            dry_run=dry_run,
            max_messages_per_run=args.count,
        )

        if args.mode == "full":
            asyncio.run(orchestrator.run_full(args.group))
        elif args.mode == "scrape-only":
            asyncio.run(orchestrator.run_scrape_only(args.group))
        elif args.mode == "enrich-only":
            asyncio.run(orchestrator.run_enrich_only())
        elif args.mode == "send-only":
            asyncio.run(orchestrator.run_send_only(args.count))


if __name__ == "__main__":
    main()
