"""
WhatsApp RPA Pilot - Expert Agent Version
==========================================
Uses WhatsAppExpert for intelligent browser automation.

Usage:
    python scripts/whatsapp_pilot.py --dry-run --count 5
    python scripts/whatsapp_pilot.py --live --count 5
"""

import asyncio
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.automation.experts import WhatsAppExpert, PhoneValidatorExpert, MessageWriterExpert

DB_PATH = PROJECT_ROOT / "output" / "cityestate.db"
LOG_DIR = PROJECT_ROOT / "output" / "pilot_logs"
LOG_DIR.mkdir(exist_ok=True)


def get_leads(count: int = 5) -> list[dict]:
    """Get top leads by score from database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, title, lead_type, phone, email, score, source, area
        FROM leads
        WHERE phone IS NOT NULL AND phone != '' AND phone != 'None'
        ORDER BY score DESC
        LIMIT ?
    """, (count,))

    leads = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return leads


def log_results(results: list[dict], run_id: str):
    """Log pilot results to file."""
    log_file = LOG_DIR / f"pilot_{run_id}.json"

    log_data = {
        "run_id": run_id,
        "timestamp": datetime.now().isoformat(),
        "total_messages": len(results),
        "sent": sum(1 for r in results if r["status"] == "sent"),
        "dry_run": sum(1 for r in results if r["status"] == "dry_run"),
        "failed": sum(1 for r in results if r["status"] in ("error", "send_unconfirmed")),
        "rate_limited": sum(1 for r in results if r["status"] == "rate_limited"),
        "results": results,
    }

    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(log_data, f, indent=2, ensure_ascii=False)

    print(f"\n  Results logged to: {log_file}")
    return log_data


async def main():
    """Main pilot runner using WhatsAppExpert."""
    import argparse

    parser = argparse.ArgumentParser(description="WhatsApp RPA Pilot (Expert Version)")
    parser.add_argument("--dry-run", action="store_true", default=True,
                        help="Simulate sending without actually sending")
    parser.add_argument("--live", action="store_true",
                        help="Actually send messages (requires QR scan)")
    parser.add_argument("--count", type=int, default=5,
                        help="Number of leads to contact")
    args = parser.parse_args()

    dry_run = not args.live
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    print("=" * 60)
    print("WHATSAPP RPA PILOT (Expert Agent)")
    print("=" * 60)
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print(f"Count: {args.count}")
    print()

    # Get leads
    leads = get_leads(args.count)
    if not leads:
        print("No leads with phone numbers found!")
        print("Run data enrichment first: python scripts/enrich_leads.py")
        return

    print(f"Found {len(leads)} leads with phone numbers")

    # Initialize experts
    phone_validator = PhoneValidatorExpert()
    message_writer = MessageWriterExpert()

    # Validate phones first
    print("\n[PHASE 1] Validating phone numbers...")
    valid_leads = []
    for lead in leads:
        phone = lead.get("phone", "")
        validation = phone_validator.validate(phone)
        if validation["is_valid"]:
            lead["phone_normalized"] = validation["normalized"]
            lead["phone_carrier"] = validation["carrier"]
            valid_leads.append(lead)
            print(f"  ✓ {phone} → {validation['normalized']} ({validation['carrier']})")
        else:
            print(f"  ✗ {phone} — Invalid: {validation['issues']}")

    if not valid_leads:
        print("\nNo valid phone numbers found!")
        return

    print(f"\n{len(valid_leads)}/{len(leads)} phones are valid")

    # Generate messages
    print("\n[PHASE 2] Generating personalized messages...")
    for lead in valid_leads:
        variants = message_writer.generate_variants(lead, channel="whatsapp", lang="ar", count=1)
        lead["message"] = variants[0]["body"] if variants else ""

    if dry_run:
        # Dry run: just show what would be sent
        print("\n[DRY RUN] Messages that would be sent:")
        for i, lead in enumerate(valid_leads, 1):
            print(f"\n  [{i}] To: {lead['phone_normalized']} ({lead.get('lead_type', 'Unknown')})")
            print(f"      Message: {lead['message'][:100]}...")

        # Save dry run log
        results = [
            {
                "phone": lead["phone_normalized"],
                "status": "dry_run",
                "message_preview": lead["message"][:100],
                "segment": lead.get("lead_type", "Unknown"),
            }
            for lead in valid_leads
        ]
        log_results(results, run_id)
    else:
        # Live: use WhatsAppExpert
        print("\n[PHASE 3] Sending via WhatsAppExpert...")
        whatsapp = WhatsAppExpert(
            db_path=str(DB_PATH),
            output_dir=str(PROJECT_ROOT / "output"),
        )

        connected = await whatsapp.connect()
        if not connected:
            print("Failed to connect to WhatsApp!")
            return

        # Prepare leads for expert (with normalized phones)
        expert_leads = []
        for lead in valid_leads:
            expert_lead = lead.copy()
            expert_lead["phone"] = lead["phone_normalized"]
            expert_leads.append(expert_lead)

        # Send batch
        results = await whatsapp.send_batch(expert_leads)

        # Log results
        log_results(results, run_id)

        # Show stats
        stats = whatsapp.get_stats()
        print(f"\n  Stats: {json.dumps(stats, indent=2)}")

        await whatsapp.disconnect()

    print("\n" + "=" * 60)
    print("PILOT COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
