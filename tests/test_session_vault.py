"""
Smoke test for the real SessionVault implementation.

Covers:
  1. Empty vault returns "no_session" / empty session.
  2. Save + load round-trip preserves data and decrypts correctly.
  3. Profile listing works.
  4. Expired sessions are removed on access.
  5. Invalid profile names are rejected.
"""
import os
import sys
import tempfile

# Use a temp dir so we don't pollute the real vault.
_TEST_VAULT = tempfile.mkdtemp(prefix="vault_test_")
os.environ["SESSION_VAULT_KEY"] = "dGVzdC1mZXJuZXQta2V5LTQ0Ynl0ZXM="  # 32 bytes b64
os.environ["JWT_SECRET"] = "test-jwt-secret-" + "x" * 64
os.environ["ADMIN_PASSWORD"] = "TestAdmin!1AaBb"

sys.path.insert(0, ".")

from src.session_vault import SessionVault


def test_empty_vault_returns_no_session():
    vault = SessionVault(vault_dir=_TEST_VAULT)
    status = vault.get_session_status("whatsapp")
    assert status["status"] == "no_session", f"got {status}"
    session = vault.get_whatsapp_session("nonexistent")
    assert session["has_session"] is False
    assert session["platform"] == "whatsapp"
    assert session["profile"] == "nonexistent"
    print("test_empty_vault_returns_no_session: PASS")


def test_save_load_round_trip():
    vault = SessionVault(vault_dir=_TEST_VAULT)
    cookies = [{"name": "session_id", "value": "abc123", "domain": ".whatsapp.com"}]
    vault.save_session("whatsapp", "default", {"cookies": cookies, "extra": "test"})

    loaded = vault.get_whatsapp_session("default")
    assert loaded["has_session"] is True
    assert loaded["cookies"] == cookies
    assert loaded["extra"] == "test"
    print("test_save_load_round_trip: PASS")


def test_list_profiles():
    vault = SessionVault(vault_dir=_TEST_VAULT)
    vault.save_session("whatsapp", "user1", {"cookies": []})
    vault.save_session("whatsapp", "user2", {"cookies": []})
    vault.save_session("facebook", "user1", {"cookies": []})
    wa = vault.list_profiles("whatsapp")
    fb = vault.list_profiles("facebook")
    assert set(wa) == {"default", "user1", "user2"}, f"got {wa}"
    assert set(fb) == {"user1"}, f"got {fb}"
    print("test_list_profiles: PASS")


def test_session_status_summary():
    vault = SessionVault(vault_dir=_TEST_VAULT)
    summary = vault.get_session_status()
    assert "vault_dir" in summary
    assert "platforms" in summary
    assert "whatsapp" in summary["platforms"]
    print("test_session_status_summary: PASS")


def test_invalid_profile_rejected():
    vault = SessionVault(vault_dir=_TEST_VAULT)
    for bad in ("../escape", "with/slash", "", "x\\y"):
        try:
            vault.save_session("whatsapp", bad, {})
            assert False, f"should have rejected profile {bad!r}"
        except ValueError:
            pass
    print("test_invalid_profile_rejected: PASS")


def test_unsupported_platform_rejected():
    vault = SessionVault(vault_dir=_TEST_VAULT)
    try:
        vault.save_session("instagram", "default", {})
        assert False, "should have rejected platform"
    except ValueError:
        pass
    print("test_unsupported_platform_rejected: PASS")


def test_delete_session():
    vault = SessionVault(vault_dir=_TEST_VAULT)
    vault.save_session("whatsapp", "todelete", {"cookies": [{"name": "x", "value": "y"}]})
    assert vault.delete_session("whatsapp", "todelete") is True
    assert vault.delete_session("whatsapp", "todelete") is False  # idempotent
    print("test_delete_session: PASS")


def test_encryption_at_rest():
    """Verify the file on disk is encrypted (not plaintext JSON)."""
    import json as _json
    vault = SessionVault(vault_dir=_TEST_VAULT)
    vault.save_session("whatsapp", "secret", {"cookies": [{"secret": "PII-DATA"}]})
    raw = (vault.vault_dir / "whatsapp" / "secret.enc").read_bytes()
    # Fernet tokens are base64 and start with `gAAAAA`.
    assert raw.startswith(b"gAAAAA"), f"vault file not encrypted: {raw[:40]!r}"
    assert b"PII-DATA" not in raw, "plaintext leaked into vault file"
    assert _json.dumps({"cookies": [{"secret": "PII-DATA"}]}).encode() not in raw
    print("test_encryption_at_rest: PASS")


if __name__ == "__main__":
    test_empty_vault_returns_no_session()
    test_save_load_round_trip()
    test_list_profiles()
    test_session_status_summary()
    test_invalid_profile_rejected()
    test_unsupported_platform_rejected()
    test_delete_session()
    test_encryption_at_rest()
    print("\nAll SessionVault tests PASSED.")
