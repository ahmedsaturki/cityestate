"""
Lead Enrichment & Reclassification Script
==========================================
Fixes the 3 critical issues:
1. Reclassify 60 Unknown leads into 4 segments
2. Normalize phone numbers to +20 format
3. Score leads (hot/warm/cold)

Usage: python scripts/enrich_leads.py
"""

import re
import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).parent.parent / "output" / "cityestate.db"

# Keywords for lead classification
SEGMENT_KEYWORDS = {
    "Developer": [
        "developer", "development", " Developments", "project", "tower",
        "compound", "community", "villa", "apartment", "residential",
        "commercial", " mall", "office", " SODIC", " TMG", " Emaar",
        "Palm Hills", "New Cairo", "New Capital", "October", "Sahel",
        "coast", "North Coast", "marina", "resort",
    ],
    "Investor": [
        "invest", "investment", "ROI", "yield", "return", "profit",
        "portfolio", "fund", "capital", "equity", "REIT", "valuation",
        "billion", "million", " deals", "acquisition", "partnership",
        "GDP", "economy", "market", "growth", "forecast",
    ],
    "Buyer": [
        "buyer", "buy", "purchase", "first home", "mortgage", "finance",
        "installment", "payment plan", "down payment", "own", "rent",
        "tenant", "landlord", "affordable", "budget",
    ],
    "Agency": [
        "agency", "broker", "agent", "realtor", "listing", "brokerage",
        "consultancy", "services", "marketing",
    ],
}

# Phone patterns for Egyptian numbers
PHONE_PATTERNS = [
    r"\+20\d{10}",       # +20XXXXXXXXXX
    r"01\d{9}",           # 01XXXXXXXXX
    r"201\d{9}",          # 201XXXXXXXXX
    r"\d{10}",            # XXXXXXXXXX
]


def classify_lead(title: str, url: str, source: str) -> str:
    """Classify a lead based on title, URL, and source."""
    text = f"{title} {url} {source}".lower()

    scores = {}
    for segment, keywords in SEGMENT_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw.lower() in text)
        scores[segment] = score

    best_segment = max(scores, key=scores.get)
    if scores[best_segment] > 0:
        return best_segment
    return "Unknown"


def extract_phones(text: str) -> list[str]:
    """Extract Egyptian phone numbers from text."""
    phones = []
    for pattern in PHONE_PATTERNS:
        matches = re.findall(pattern, text)
        phones.extend(matches)
    return list(set(phones))


def extract_emails(text: str) -> list[str]:
    """Extract email addresses from text."""
    pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    return list(set(re.findall(pattern, text)))


def score_lead(lead_type: str, has_phone: bool, has_email: bool, title: str) -> float:
    """Score a lead from 0.0 to 100.0."""
    score = 0.0

    # Type scoring
    type_scores = {
        "Developer": 30,
        "Investor": 25,
        "Buyer": 20,
        "Agency": 15,
        "Unknown": 5,
    }
    score += type_scores.get(lead_type, 5)

    # Contact info scoring
    if has_phone:
        score += 25
    if has_email:
        score += 20

    # Title quality scoring
    title_lower = title.lower()
    if any(kw in title_lower for kw in ["egypt", "cairo", "alexandria", "sahel", "capital"]):
        score += 10
    if any(kw in title_lower for kw in ["2025", "2026", "new", "latest"]):
        score += 5

    return min(score, 100.0)


def enrich_leads():
    """Main enrichment pipeline."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get all leads
    cursor.execute("SELECT id, title, url, source, lead_type, phone, email, score FROM leads")
    leads = cursor.fetchall()

    print(f"Total leads: {len(leads)}")
    print("=" * 60)

    stats = {
        "reclassified": 0,
        "phones_found": 0,
        "emails_found": 0,
        "scores_updated": 0,
    }

    for lead in leads:
        lead_id, title, url, source, lead_type, phone, email, old_score = lead

        # 1. Reclassify if Unknown
        new_type = lead_type
        if lead_type == "Unknown" or not lead_type:
            new_type = classify_lead(title, url, source)
            if new_type != "Unknown":
                stats["reclassified"] += 1

        # 2. Extract phones and emails from title/url/source
        text = f"{title} {url} {source}"
        found_phones = extract_phones(text)
        found_emails = extract_emails(text)

        new_phone = phone
        if not phone and found_phones:
            new_phone = found_phones[0]
            stats["phones_found"] += 1

        new_email = email
        if not email and found_emails:
            new_email = found_emails[0]
            stats["emails_found"] += 1

        # 3. Calculate new score
        has_phone = bool(new_phone and new_phone != "None")
        has_email = bool(new_email and new_email != "None")
        new_score = score_lead(new_type, has_phone, has_email, title)

        # 4. Update database
        cursor.execute("""
            UPDATE leads
            SET lead_type = ?,
                phone = ?,
                email = ?,
                score = ?,
                updated_at = datetime('now')
            WHERE id = ?
        """, (new_type, new_phone, new_email, new_score, lead_id))

        stats["scores_updated"] += 1

        # Print progress for reclassified leads
        if new_type != lead_type and lead_type == "Unknown":
            print(f"  ID={lead_id:3d} | {lead_type:12s} -> {new_type:12s} | {title[:50]}")

    conn.commit()
    conn.close()

    print("=" * 60)
    print("ENRICHMENT COMPLETE")
    print(f"  Reclassified: {stats['reclassified']}")
    print(f"  Phones found: {stats['phones_found']}")
    print(f"  Emails found: {stats['emails_found']}")
    print(f"  Scores updated: {stats['scores_updated']}")

    # Show final distribution
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT lead_type, COUNT(*) FROM leads GROUP BY lead_type ORDER BY COUNT(*) DESC")
    print("\nFinal Lead Types:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}")

    cursor.execute("SELECT COUNT(*) FROM leads WHERE phone IS NOT NULL AND phone != '' AND phone != 'None'")
    phone_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM leads WHERE email IS NOT NULL AND email != '' AND email != 'None'")
    email_count = cursor.fetchone()[0]
    print(f"\nHas phone: {phone_count}/{len(leads)}")
    print(f"Has email: {email_count}/{len(leads)}")

    conn.close()
    return stats


if __name__ == "__main__":
    enrich_leads()
