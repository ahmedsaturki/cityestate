#!/usr/bin/env python3
"""
Test Personalized Outreach Pipeline
====================================
Tests the full flow: CSV → CrewAI Agents → Personalized Messages
"""

import sys
import io
from pathlib import Path

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")


def test_csv_loading():
    """Test loading buyers from CSV."""
    print("\n=== Test 1: CSV Loading ===")
    
    from src.outreach.bulk_sender import BulkMessageSender
    
    sender = BulkMessageSender(dry_run=True)
    csv_path = PROJECT_ROOT / "output" / "buyers.csv"
    
    if not csv_path.exists():
        print(f"[FAIL] CSV file not found: {csv_path}")
        return False
    
    buyers = sender.load_from_csv(str(csv_path))
    
    if not buyers:
        print("[FAIL] No buyers loaded")
        return False
    
    print(f"[OK] Loaded {len(buyers)} buyers from CSV")
    for b in buyers[:3]:
        print(f"   - {b['name']} ({b['phone']}) - {b['city']}")
    
    return True


def test_llm_availability():
    """Test if LLM is available."""
    print("\n=== Test 2: LLM Availability ===")
    
    from src.ai_crew.llm_config import is_llm_available, get_llm_provider
    
    available = is_llm_available()
    provider = get_llm_provider()
    
    if available:
        print(f"[OK] LLM available: {provider}")
    else:
        print("[WARN] No LLM available (will use fallback)")
        print("   Install Ollama: https://ollama.ai")
        print("   Then run: ollama pull llama3.1:8b")
    
    return True  # Continue even without LLM


def test_message_generation():
    """Test generating a personalized message."""
    print("\n=== Test 3: Message Generation ===")
    
    from src.ai_crew.crew import CityEstateCrew
    
    crew = CityEstateCrew()
    
    # Test with a sample buyer
    test_buyer = {
        "name": "أحمد محمد",
        "phone": "201234567890",
        "city": "التجمع الخامس",
        "property_type": "شقة 3 غرف",
        "budget": "3-4 مليون",
        "source": "Facebook",
        "last_contact": "2026-07-15",
        "notes": "يبحث عن مشروع جديد",
    }
    
    print(f"Generating message for: {test_buyer['name']}")
    message = crew.generate_personalized_message(test_buyer)
    
    if message:
        print(f"[OK] Generated message ({len(message)} chars):")
        print(f"   {message[:200]}...")
        return True
    else:
        print("[FAIL] Failed to generate message")
        return False


def test_bulk_generation():
    """Test generating messages for multiple buyers."""
    print("\n=== Test 4: Bulk Generation ===")
    
    from src.ai_crew.crew import CityEstateCrew
    from src.outreach.bulk_sender import BulkMessageSender
    
    crew = CityEstateCrew()
    sender = BulkMessageSender(dry_run=True)
    
    csv_path = PROJECT_ROOT / "output" / "buyers.csv"
    buyers = sender.load_from_csv(str(csv_path))
    
    if not buyers:
        print("[FAIL] No buyers to process")
        return False
    
    # Generate messages for first 3 buyers only (for testing)
    test_buyers = buyers[:3]
    messages = []
    
    for buyer in test_buyers:
        message = crew.generate_personalized_message(buyer)
        messages.append(message)
    
    print(f"[OK] Generated {len(messages)} messages")
    for buyer, msg in zip(test_buyers, messages):
        print(f"\n  {buyer['name']}:")
        print(f"   {msg[:150]}...")
    
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Personalized Outreach Pipeline")
    print("=" * 60)
    
    results = {
        "CSV Loading": test_csv_loading(),
        "LLM Availability": test_llm_availability(),
        "Message Generation": test_message_generation(),
        "Bulk Generation": test_bulk_generation(),
    }
    
    print("\n" + "=" * 60)
    print("Test Results:")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed in results.items():
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {test_name}: {status}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("\n[SUCCESS] All tests passed!")
        print("\nNext steps:")
        print("1. Edit output/buyers.csv with your real buyer data")
        print("2. Run: python main.py --outreach (dry run)")
        print("3. Run: python main.py --outreach --send (to send)")
    else:
        print("\n[WARN] Some tests failed. Check the output above.")
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
