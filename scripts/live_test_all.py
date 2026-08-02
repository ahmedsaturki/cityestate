"""
Live Test Suite — اختبار مباشر شامل
====================================
Tests all API endpoints with authentication.
Simulates real WhatsApp messages and webhook submissions.

Usage: python scripts/live_test_all.py
"""

import sys
import io
import json
import asyncio
from pathlib import Path

# Fix Windows Unicode encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import requests

BASE_URL = "http://localhost:8000"
ADMIN_USER = "admin"
ADMIN_PASS = "C1ty3st@t3_S3cur3_2024!"


def print_header(text: str):
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def print_result(label: str, value, indent: int = 2):
    spaces = " " * indent
    if isinstance(value, (dict, list)):
        print(f"{spaces}{label}: {json.dumps(value, indent=indent+2, ensure_ascii=False)}")
    else:
        print(f"{spaces}{label}: {value}")


def test_health():
    """Test health endpoint (public)."""
    print_header("TEST 1: Health Endpoint (Public)")
    resp = requests.get(f"{BASE_URL}/health")
    print(f"  Status: {resp.status_code}")
    data = resp.json()
    print_result("Response", data)
    return resp.status_code == 200


def test_login():
    """Test login and get JWT token."""
    print_header("TEST 2: Login Authentication")
    resp = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
        "username": ADMIN_USER,
        "password": ADMIN_PASS
    })
    print(f"  Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        token = data.get("access_token")
        user = data.get("user", {})
        print(f"  ✅ Login successful!")
        print(f"  Token: {token[:50]}...")
        print(f"  User: {user.get('username')} ({user.get('role')})")
        return token
    else:
        print(f"  ❌ Login failed: {resp.text}")
        return None


def test_auth_me(token: str):
    """Test /auth/me endpoint."""
    print_header("TEST 3: Get Current User")
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(f"{BASE_URL}/api/v1/auth/me", headers=headers)
    print(f"  Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print_result("User", data)
        return True
    return False


def test_properties(token: str):
    """Test properties endpoint."""
    print_header("TEST 4: List Properties")
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(f"{BASE_URL}/api/v1/properties", headers=headers)
    print(f"  Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        props = data.get("properties", data) if isinstance(data, dict) else data
        count = len(props) if isinstance(props, list) else 0
        print(f"  ✅ Found {count} properties")
        if count > 0:
            for i, p in enumerate(props[:3], 1):
                print(f"  {i}. {p.get('title', 'N/A')}")
                print(f"     Price: {p.get('price', 0):,.0f} EGP")
        return True
    return False


def test_leads(token: str):
    """Test leads endpoint."""
    print_header("TEST 5: List Leads")
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(f"{BASE_URL}/api/v1/leads", headers=headers)
    print(f"  Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        leads = data.get("leads", data) if isinstance(data, dict) else data
        count = len(leads) if isinstance(leads, list) else 0
        print(f"  ✅ Found {count} leads")
        if count > 0:
            for i, l in enumerate(leads[:3], 1):
                print(f"  {i}. {l.get('title', 'N/A')} - {l.get('lead_type', 'N/A')}")
        return True
    return False


def test_dashboard(token: str):
    """Test dashboard stats endpoint."""
    print_header("TEST 6: Dashboard Stats")
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(f"{BASE_URL}/api/v1/dashboard/stats", headers=headers)
    print(f"  Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print_result("Stats", data)
        return True
    return False


def test_webhook_whatsapp():
    """Test WhatsApp webhook endpoint (simulates incoming message)."""
    print_header("TEST 7: WhatsApp Webhook (Simulated)")
    
    # Simulate a WhatsApp form submission
    payload = {
        "name": "د. أحمد رشدي",
        "phone": "+201012345678",
        "message": "عايز فيلا في الفردوس بالسادات، الميزانية 5 مليون جنيه",
        "area": "الفردوس",
        "min_budget": 5000000,
        "max_budget": 5000000,
        "bedrooms": 4,
        "property_type": "فيلا"
    }
    
    print(f"  Sending: {json.dumps(payload, ensure_ascii=False, indent=4)}")
    
    resp = requests.post(f"{BASE_URL}/api/v1/webhooks/form", json=payload)
    print(f"  Status: {resp.status_code}")
    
    if resp.status_code in [200, 201]:
        data = resp.json()
        print_result("Response", data)
        print(f"  ✅ Webhook processed successfully!")
        return True
    else:
        print(f"  ❌ Webhook failed: {resp.text}")
        return False


def test_webhook_facebook():
    """Test Facebook webhook endpoint."""
    print_header("TEST 8: Facebook Webhook (Simulated)")
    
    payload = {
        "name": "م. محمدῡ",
        "phone": "+201098765432",
        "message": "محل تجاري في Polaris Parks، 8 مليون جنيه كاش",
        "area": "Polaris Parks",
        "min_budget": 8000000,
        "max_budget": 8000000,
        "property_type": "محل تجاري"
    }
    
    print(f"  Sending: {json.dumps(payload, ensure_ascii=False, indent=4)}")
    
    resp = requests.post(f"{BASE_URL}/api/v1/webhooks/form", json=payload)
    print(f"  Status: {resp.status_code}")
    
    if resp.status_code in [200, 201]:
        data = resp.json()
        print_result("Response", data)
        print(f"  ✅ Facebook webhook processed!")
        return True
    else:
        print(f"  ❌ Facebook webhook failed: {resp.text}")
        return False


def test_bridge_handler():
    """Test bridge handler directly (dry run)."""
    print_header("TEST 9: Bridge Handler Direct Test")
    
    sys.path.insert(0, str(Path.cwd()))
    from src.api.bridge_handler import parse_intent, score_lead
    
    test_messages = [
        ("عايز شقة فاخرة في النخيل، 3 مليون جنيه", "شقة فاخرة", "النخيل"),
        ("محل تجاري في المنطقة الصناعية، 5 مليون", "محل تجاري", "المنطقة الصناعية الأولى"),
        ("فيلا دوبلكس في الشريط المميز، 8 مليون", "فيلا", "المنطقة 7 الشريط المميز"),
    ]
    
    all_passed = True
    for msg, expected_type, expected_area in test_messages:
        intent = parse_intent(msg, "+201055555555")
        score = score_lead(intent, msg)
        
        type_match = intent.get("property_type") == expected_type
        area_match = intent.get("area") == expected_area
        
        status = "✅" if (type_match and area_match) else "❌"
        print(f"  {status} \"{msg[:40]}...\"")
        print(f"     Type: {intent.get('property_type')} (expected: {expected_type})")
        print(f"     Area: {intent.get('area')} (expected: {expected_area})")
        print(f"     Score: {score.get('score')}/100 ({score.get('tier')})")
        
        if not (type_match and area_match):
            all_passed = False
    
    return all_passed


def test_match_properties():
    """Test property matching from database."""
    print_header("TEST 10: Property Matching from Database")
    
    sys.path.insert(0, str(Path.cwd()))
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from src.database.models import Property
    from src.api.bridge_handler import parse_intent, find_matching_properties
    
    db_path = Path("output/cityestate.db")
    if not db_path.exists():
        print("  ❌ Database not found")
        return False
    
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    Session = sessionmaker(bind=engine)
    db = Session()
    
    test_cases = [
        ("عايز شقة في المنطقة 7، 3 مليون", "شقة فاخرة", "المنطقة 7 الشريط المميز"),
        ("محل في بولاريس، 5 مليون", "محل تجاري", "Polaris Parks"),
    ]
    
    all_passed = True
    for msg, expected_type, expected_area in test_cases:
        intent = parse_intent(msg, "+201077777777")
        matches = find_matching_properties(intent, db)
        
        has_matches = len(matches) > 0
        status = "✅" if has_matches else "❌"
        print(f"  {status} \"{msg[:40]}...\"")
        print(f"     Intent: {intent.get('property_type')} in {intent.get('area')}")
        print(f"     Matches: {len(matches)} properties")
        
        if has_matches:
            for m in matches[:2]:
                print(f"       - {m.get('title')} ({m.get('price', 0):,.0f} EGP)")
        else:
            all_passed = False
    
    db.close()
    return all_passed


def main():
    """Run all tests."""
    print_header("CITYESTATE LIVE TEST SUITE — اختبار مباشر شامل")
    print(f"  Server: {BASE_URL}")
    print(f"  Admin: {ADMIN_USER}")
    
    results = {}
    
    # Test 1: Health (public)
    results["health"] = test_health()
    
    # Test 2: Login
    token = test_login()
    results["login"] = token is not None
    
    if not token:
        print("\n❌ Cannot continue without authentication token")
        return
    
    # Test 3: Auth Me
    results["auth_me"] = test_auth_me(token)
    
    # Test 4: Properties
    results["properties"] = test_properties(token)
    
    # Test 5: Leads
    results["leads"] = test_leads(token)
    
    # Test 6: Dashboard
    results["dashboard"] = test_dashboard(token)
    
    # Test 7: WhatsApp Webhook
    results["webhook_whatsapp"] = test_webhook_whatsapp()
    
    # Test 8: Facebook Webhook
    results["webhook_facebook"] = test_webhook_facebook()
    
    # Test 9: Bridge Handler
    results["bridge_handler"] = test_bridge_handler()
    
    # Test 10: Property Matching
    results["match_properties"] = test_match_properties()
    
    # Summary
    print_header("TEST RESULTS SUMMARY")
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} — {test_name}")
    
    print(f"\n  Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n  🎉 ALL TESTS PASSED! System is production-ready!")
    else:
        print(f"\n  ⚠️ {total - passed} test(s) failed. Check logs above.")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
