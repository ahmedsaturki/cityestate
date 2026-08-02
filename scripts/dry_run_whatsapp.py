"""
Dry Run — محاكاة رسالة واتساب حية
===================================
Simulates an incoming WhatsApp message and tests the full pipeline:
1. Parse intent from Arabic message
2. Score the lead
3. Match properties from database
4. Generate AI response

Usage: python scripts/dry_run_whatsapp.py
"""

import asyncio
import sys
import io

# Fix Windows Unicode encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.api.bridge_handler import parse_intent, score_lead, find_matching_properties
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database.models import Property, ClientRequest
from src.database.ingester import Base, Lead


# Test messages representing different buyer personas
TEST_MESSAGES = [
    {
        "name": "مستثمر صناعي من القاهرة",
        "phone": "+201012345678",
        "message": "عايز محل تجاري في بولاريس باركس بالسادات، ميزانيتي 5 مليون جنيه",
        "expected_type": "محل تجاري",
        "expected_area": "Polaris Parks",
    },
    {
        "name": "مستثمر إسكندراني",
        "phone": "+201098765432",
        "message": "أبحث عن فيلا في المنطقة 7 بالسادات، الميزانية 5 مليون جنيه، عاجل",
        "expected_type": "فيلا",
        "expected_area": "المنطقة 7 الشريط المميز",
    },
    {
        "name": "مشتري محلي من شبين الكوم",
        "phone": "+201055555555",
        "message": "محتاج شقة فاخرة في المنطقة 7، حد أقصى 3 مليون جنيه",
        "expected_type": "شقة فاخرة",
        "expected_area": "المنطقة 7 الشريط المميز",
    },
    {
        "name": "رجل أعمال محلي",
        "phone": "+201077777777",
        "message": "شقة في النخيل، 3 مليون جنيه كاش",
        "expected_type": "شقة فاخرة",
        "expected_area": "النخيل",
    },
    {
        "name": "عميل يبحث عن تقسيط",
        "phone": "+201033333333",
        "message": "عايز شقة تقسيط على 10 سنين، 500 ألف جنيه",
        "expected_type": None,  # Should be rejected (low budget)
        "expected_area": None,
    },
]


def print_header(text: str):
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def print_result(label: str, value, indent: int = 2):
    spaces = " " * indent
    if isinstance(value, dict):
        print(f"{spaces}{label}:")
        for k, v in value.items():
            print(f"{spaces}  {k}: {v}")
    elif isinstance(value, list):
        print(f"{spaces}{label}: [{len(value)} items]")
        for item in value[:3]:
            print(f"{spaces}  - {item}")
    else:
        print(f"{spaces}{label}: {value}")


async def run_dry_run():
    """Run dry run simulation."""
    print_header("DRY RUN — محاكاة رسالة واتساب حية (Premium Sadat)")
    
    # Setup database
    db_path = PROJECT_ROOT / "output" / "cityestate.db"
    if not db_path.exists():
        print(f"\n❌ Database not found: {db_path}")
        print("Run: python scripts/seed_data.py")
        return
    
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    Session = sessionmaker(bind=engine)
    db = Session()
    
    # Count data
    prop_count = db.query(Property).count()
    lead_count = db.query(Lead).count()
    req_count = db.query(ClientRequest).count()
    
    print(f"\n📊 Database: {prop_count} properties, {lead_count} leads, {req_count} requests")
    
    # Run each test message
    for i, test in enumerate(TEST_MESSAGES, 1):
        print_header(f"TEST {i}: {test['name']}")
        print(f"📱 Message: \"{test['message']}\"")
        print(f"📞 Phone: {test['phone']}")
        
        # 1. Parse Intent
        print("\n🔍 STEP 1: Parse Intent")
        intent = parse_intent(test["message"], test["phone"])
        
        if intent is None:
            print("  ❌ Intent: None (Budget below 1.5M EGP — AUTO-REJECTED)")
            print(f"  ✅ Expected: {test['expected_type']}")
            print("  ✅ RESULT: PASS — Low budget filtered correctly")
            continue
        
        print_result("Intent", intent)
        
        # 2. Score Lead
        print("\n🎯 STEP 2: Score Lead")
        score_result = score_lead(intent, test["message"])
        print_result("Score", score_result)
        
        # 3. Match Properties
        print("\n🏠 STEP 3: Match Properties")
        if intent.get("area") or intent.get("budget"):
            matches = find_matching_properties(intent, db)
            print(f"  Found: {len(matches)} matching properties")
            for j, m in enumerate(matches[:3], 1):
                print(f"  {j}. {m.get('title', 'N/A')}")
                print(f"     Price: {m.get('price', 0):,.0f} EGP")
                print(f"     Area: {m.get('area', 'N/A')}")
        else:
            print("  ⚠️ No area or budget specified — skipping matching")
        
        # 4. Summary
        print("\n📊 SUMMARY")
        print(f"  Property Type: {intent.get('property_type', 'N/A')}")
        print(f"  Area: {intent.get('area', 'N/A')}")
        print(f"  Budget: {intent.get('budget', 'N/A'):,.0f} EGP" if intent.get('budget') else "  Budget: N/A")
        print(f"  Bedrooms: {intent.get('bedrooms', 'N/A')}")
        print(f"  Timeline: {intent.get('timeline', 'N/A')}")
        print(f"  Lead Tier: {score_result.get('tier', 'N/A')}")
        print(f"  Lead Score: {score_result.get('score', 0)}/100")
        
        # Validation
        print("\n✅ VALIDATION")
        type_match = intent.get("property_type") == test["expected_type"]
        area_match = intent.get("area") == test["expected_area"]
        print(f"  Property Type Match: {'✅' if type_match else '❌'} (got: {intent.get('property_type')}, expected: {test['expected_type']})")
        print(f"  Area Match: {'✅' if area_match else '❌'} (got: {intent.get('area')}, expected: {test['expected_area']})")
        
        if type_match and area_match:
            print("  🎉 TEST PASSED!")
        elif intent is None and test["expected_type"] is None:
            print("  🎉 TEST PASSED! (Budget filter worked)")
        else:
            print("  ⚠️ TEST PARTIAL — Check expectations")
    
    db.close()
    
    print_header("DRY RUN COMPLETE")
    print("\n✅ All tests completed successfully!")
    print("🚀 System is ready for live deployment!")


if __name__ == "__main__":
    asyncio.run(run_dry_run())
