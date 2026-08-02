"""
Facebook Group Scraper - Expert Agent Version
==============================================
Uses FacebookExpert for intelligent group scraping.

Usage:
    python scripts/facebook_scraper.py --limit 50
    python scripts/facebook_scraper.py --group "https://facebook.com/groups/..."
    python scripts/facebook_scraper.py --dry-run
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.automation.experts import FacebookExpert, LeadClassifierExpert

LOG_DIR = PROJECT_ROOT / "output" / "scraper_logs"
LOG_DIR.mkdir(exist_ok=True)

# Default Egyptian real estate groups
DEFAULT_GROUPS = [
    "https://www.facebook.com/groups/real.estate.egypt",
    "https://www.facebook.com/groups/properties.for.sale.in.egypt",
    "https://www.facebook.com/groups/egypt.real.estate.investors",
    "https://www.facebook.com/groups/new.cairo.properties",
    "https://www.facebook.com/groups/compound.life.egypt",
]


async def main():
    """Main scraper runner using FacebookExpert."""
    import argparse

    parser = argparse.ArgumentParser(description="Facebook Group Scraper (Expert Version)")
    parser.add_argument("--group", action="append", help="Facebook Group URL(s)")
    parser.add_argument("--limit", type=int, default=50, help="Max posts per group")
    parser.add_argument("--dry-run", action="store_true", help="Don't save to DB")
    args = parser.parse_args()

    groups = args.group if args.group else DEFAULT_GROUPS

    print("=" * 60)
    print("FACEBOOK GROUP SCRAPER (Expert Agent)")
    print("=" * 60)
    print(f"Groups: {len(groups)}")
    print(f"Limit: {args.limit} posts per group")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    print()

    # Initialize experts
    facebook = FacebookExpert(
        db_path=str(PROJECT_ROOT / "output" / "cityestate.db"),
        output_dir=str(PROJECT_ROOT / "output"),
    )
    classifier = LeadClassifierExpert()

    if args.dry_run:
        print("[DRY RUN] Would scrape Facebook groups and save to database")
        print("\nGroups to scrape:")
        for i, group in enumerate(groups, 1):
            print(f"  {i}. {group}")
        return

    # Connect to Facebook
    print("[PHASE 1] Connecting to Facebook...")
    connected = await facebook.connect()
    if not connected:
        print("Failed to connect to Facebook!")
        return

    # Scrape groups
    print(f"\n[PHASE 2] Scraping {len(groups)} groups...")
    all_leads = await facebook.scrape_multiple_groups(groups, args.limit)

    # Classify new leads
    print(f"\n[PHASE 3] Classifying {len(all_leads)} leads...")
    classifications = classifier.classify_batch(all_leads)

    # Update stats
    for lead, cls in zip(all_leads, classifications):
        lead["classification"] = cls

    # Show stats
    stats = facebook.get_stats()
    print(f"\n  Scraping Stats: {json.dumps(stats, indent=2)}")

    # Show classification distribution
    type_dist = classifier.get_type_distribution(classifications)
    conf_dist = classifier.get_confidence_distribution(classifications)
    print(f"\n  Type Distribution: {json.dumps(type_dist, indent=2)}")
    print(f"  Confidence Distribution: {json.dumps(conf_dist, indent=2)}")

    # Save log
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = LOG_DIR / f"scrape_{timestamp}.json"
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "groups_scraped": len(groups),
            "total_leads": len(all_leads),
            "stats": stats,
            "type_distribution": type_dist,
            "confidence_distribution": conf_dist,
            "leads": all_leads[:10],  # Save first 10 for reference
        }, f, indent=2, ensure_ascii=False)

    print(f"\n  Log saved to: {log_file}")

    await facebook.disconnect()

    print("\n" + "=" * 60)
    print("SCRAPING COMPLETE")
    print("=" * 60)
    print(f"  Total leads: {len(all_leads)}")
    print(f"  With phone: {stats.get('phones_found', 0)}")
    print(f"  Groups scraped: {stats.get('groups_scraped', 0)}")


if __name__ == "__main__":
    asyncio.run(main())
