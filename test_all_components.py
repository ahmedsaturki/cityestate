"""
Test Suite
==========
Comprehensive tests for all new components.
"""

import io
import os
import sys
from pathlib import Path

# Fix Windows encoding
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")


def test_session_vault():
    """Test Session Vault components."""
    print("\n[TEST] Session Vault...")
    try:
        from src.session_vault import SessionVault, EncryptionManager, CookieManager, BrowserProfile

        # Test encryption
        enc = EncryptionManager("test-key")
        data = {"cookies": [{"name": "test", "value": "123"}]}
        encrypted = enc.encrypt(data)
        decrypted = enc.decrypt(encrypted)
        assert decrypted == data, "Encryption/decryption failed"
        print("  ✓ Encryption/Decryption")

        # Test password hashing
        hashed = enc.hash_password("test123")
        assert enc.verify_password("test123", hashed), "Password verification failed"
        assert not enc.verify_password("wrong", hashed), "Wrong password should fail"
        print("  ✓ Password Hashing")

        # Test vault
        vault = SessionVault(vault_dir="test_vault")
        session = vault.get_whatsapp_session("test")
        assert session["platform"] == "whatsapp"
        assert session["profile"] == "test"
        print("  ✓ WhatsApp Session")

        session = vault.get_facebook_session("test")
        assert session["platform"] == "facebook"
        print("  ✓ Facebook Session")

        # Test status
        status = vault.get_session_status()
        assert "vault_dir" in status
        print("  ✓ Session Status")

        # Cleanup
        import shutil
        shutil.rmtree("test_vault", ignore_errors=True)

        print("  ✓ All Session Vault tests passed!")
        return True
    except Exception as e:
        print(f"  ✗ Session Vault test failed: {e}")
        return False


def test_database_models():
    """Test Database Models."""
    print("\n[TEST] Database Models...")
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from src.database.ingester import Base, Lead
        from src.database.models import User, Property, ClientRequest, MessageLog
        from src.session_vault.encryption import EncryptionManager

        # Create test database
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        db = Session()

        # Test Lead
        lead = Lead(
            title="Test Lead",
            url="https://test.com/lead",
            source="test",
            lead_type="Developer",
            status="new",
        )
        db.add(lead)
        db.commit()
        assert lead.id is not None
        print("  ✓ Lead Model")

        # Test User
        enc = EncryptionManager("test")
        user = User(
            username="testuser",
            password_hash=enc.hash_password("test123"),
            role="admin",
        )
        db.add(user)
        db.commit()
        assert user.id is not None
        print("  ✓ User Model")

        # Test Property
        prop = Property(
            title="Test Property",
            area="New Cairo",
            price=5000000,
            property_type="primary",
            status="available",
        )
        db.add(prop)
        db.commit()
        assert prop.id is not None
        print("  ✓ Property Model")

        # Test ClientRequest
        req = ClientRequest(
            client_name="Test Client",
            area="New Cairo",
            min_budget=3000000,
            max_budget=7000000,
            property_type="primary",
        )
        db.add(req)
        db.commit()
        assert req.id is not None
        print("  ✓ ClientRequest Model")

        # Test MessageLog
        msg = MessageLog(
            channel="whatsapp",
            message="Test message",
            status="sent",
            phone="+201234567890",
        )
        db.add(msg)
        db.commit()
        assert msg.id is not None
        print("  ✓ MessageLog Model")

        # Test to_dict
        assert "id" in lead.to_dict()
        assert "title" in prop.to_dict()
        assert "client_name" in req.to_dict()
        print("  ✓ Serialization")

        db.close()
        print("  ✓ All Database Model tests passed!")
        return True
    except Exception as e:
        print(f"  ✗ Database Model test failed: {e}")
        return False


def test_match_making():
    """Test Match-Making Engine."""
    print("\n[TEST] Match-Making Engine...")
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from src.database.ingester import Base
        from src.database.models import Property, ClientRequest
        from src.matching.engine import MatchMakingEngine, MatchScorer

        # Create test database
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        db = Session()

        # Add test properties
        props = [
            Property(title="Property 1", area="New Cairo", price=5000000, property_type="primary", status="available"),
            Property(title="Property 2", area="6th October", price=3000000, property_type="resale", status="available"),
            Property(title="Property 3", area="New Cairo", price=4000000, property_type="primary", status="available", bedrooms=3),
            Property(title="Property 4", area="Sheraton", price=8000000, property_type="primary", status="available"),
        ]
        for p in props:
            db.add(p)
        db.commit()

        # Add test request
        req = ClientRequest(
            client_name="Test Client",
            area="New Cairo",
            min_budget=3000000,
            max_budget=6000000,
            property_type="primary",
        )
        db.add(req)
        db.commit()

        # Test matching
        engine_obj = MatchMakingEngine(db)
        result = engine_obj.match_request(req.id)

        assert result["status"] == "matched"
        assert result["total_matches"] > 0
        assert result["matches"][0]["score"] > 0
        print(f"  ✓ Found {result['total_matches']} matches")

        # Test scoring
        scorer = MatchScorer()
        score = scorer.score(req, props[0])
        assert 0 <= score <= 1
        print(f"  ✓ Scoring works (score={score:.2f})")

        # Test statistics
        stats = engine_obj.get_match_statistics()
        assert "total_requests" in stats
        print("  ✓ Statistics")

        db.close()
        print("  ✓ All Match-Making tests passed!")
        return True
    except Exception as e:
        print(f"  ✗ Match-Making test failed: {e}")
        return False


def test_api_models():
    """Test API Pydantic Models."""
    print("\n[TEST] API Models...")
    try:
        from src.api.models import (
            LoginRequest,
            TokenResponse,
            LeadCreate,
            LeadResponse,
            PropertyCreate,
            PropertyResponse,
            ClientRequestCreate,
            ClientRequestResponse,
            DashboardStats,
        )

        # Test LoginRequest
        login = LoginRequest(username="admin", password="admin123")
        assert login.username == "admin"
        print("  ✓ LoginRequest")

        # Test LeadCreate
        lead = LeadCreate(
            title="Test Lead",
            url="https://test.com",
            source="test",
        )
        assert lead.title == "Test Lead"
        print("  ✓ LeadCreate")

        # Test PropertyCreate
        prop = PropertyCreate(
            title="Test Property",
            area="New Cairo",
            price=5000000,
        )
        assert prop.price == 5000000
        print("  ✓ PropertyCreate")

        # Test ClientRequestCreate
        req = ClientRequestCreate(
            client_name="Test Client",
            area="New Cairo",
        )
        assert req.client_name == "Test Client"
        print("  ✓ ClientRequestCreate")

        print("  ✓ All API Model tests passed!")
        return True
    except Exception as e:
        print(f"  ✗ API Model test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("CityEstate — Comprehensive Test Suite")
    print("=" * 60)

    results = {}
    results["Session Vault"] = test_session_vault()
    results["Database Models"] = test_database_models()
    results["Match-Making"] = test_match_making()
    results["API Models"] = test_api_models()

    # Summary
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, result in results.items():
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"  {name}: {status}")

    print(f"\n  Total: {passed}/{total} passed")

    if passed == total:
        print("\n  🎉 All tests passed!")
        return 0
    else:
        print("\n  ⚠️ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
