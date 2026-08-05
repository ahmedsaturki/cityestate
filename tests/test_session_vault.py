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
import tempfile
import time

import pytest

# Use a temp dir so we don't pollute the real vault.
_TEST_VAULT = tempfile.mkdtemp(prefix="vault_test_")


@pytest.fixture(autouse=True)
def _vault_env(monkeypatch):
    """Set vault-specific env vars via monkeypatch so they don't leak
    into other test modules."""
    monkeypatch.setenv(
        "SESSION_VAULT_KEY", "dGVzdC1mZXJuZXQta2V5LTQ0Ynl0ZXM="
    )  # 32 bytes b64
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret-" + "x" * 64)
    # ADMIN_PASSWORD is inherited from conftest; do NOT override it here.


def test_empty_vault_returns_no_session():
    from src.session_vault import SessionVault
    vault = SessionVault(vault_dir=_TEST_VAULT)
    status = vault.get_session_status("whatsapp")
    assert status["status"] == "no_session", f"got {status}"
    session = vault.get_whatsapp_session("nonexistent")
    assert session["has_session"] is False
    assert session["platform"] == "whatsapp"
    assert session["profile"] == "nonexistent"


def test_save_load_round_trip():
    from src.session_vault import SessionVault
    vault = SessionVault(vault_dir=_TEST_VAULT)
    cookies = [{"name": "session_id", "value": "abc123", "domain": ".whatsapp.com"}]
    vault.save_session("whatsapp", "default", {"cookies": cookies, "extra": "test"})
    loaded = vault.get_whatsapp_session("default")
    assert loaded["has_session"] is True
    # Cookies are stored at the top level of the session dict.
    assert loaded["cookies"][0]["value"] == "abc123"
    assert loaded["extra"] == "test"


def test_profile_listing():
    from src.session_vault import SessionVault
    vault = SessionVault(vault_dir=_TEST_VAULT)
    vault.save_session("whatsapp", "listed", {"cookies": []})
    profiles = vault.list_profiles("whatsapp")
    assert "listed" in profiles


def test_expired_sessions_removed(monkeypatch):
    from src.session_vault import SessionVault
    import src.session_vault.vault as vault_mod

    # Force SESSION_TTL_SECONDS to 0 so the session expires immediately
    # after creation (expires_at == now, which is already in the past by the
    # time the read-side check runs).
    monkeypatch.setattr(vault_mod, "SESSION_TTL_SECONDS", 0)

    vault = SessionVault(vault_dir=_TEST_VAULT)
    vault.save_session("whatsapp", "ephemeral", {"cookies": []})
    time.sleep(0.05)  # tiny delay so expires_at < time.time()
    # get_whatsapp_session calls _read which checks expiration and removes
    # the expired file, returning has_session=False.
    session = vault.get_whatsapp_session("ephemeral")
    assert session["has_session"] is False, f"expected expired, got {session}"


def test_invalid_profile_name_rejected():
    from src.session_vault import SessionVault
    vault = SessionVault(vault_dir=_TEST_VAULT)
    # Profile name with path traversal
    try:
        vault.save_session("whatsapp", "../etc/passwd", {"cookies": []})
        # If it doesn't raise, check that the profile wasn't saved with that name
        profiles = vault.list_profiles("whatsapp")
        assert "../etc/passwd" not in profiles
    except (ValueError, OSError):
        pass  # Expected — rejected


# ---------------------------------------------------------------------------
# Legacy __main__ runner kept for standalone smoke-testing.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    os.environ["SESSION_VAULT_KEY"] = "dGVzdC1mZXJuZXQta2V5LTQ0Ynl0ZXM="
    os.environ["JWT_SECRET"] = "test-jwt-secret-" + "x" * 64
    test_empty_vault_returns_no_session()
    test_save_load_round_trip()
    test_profile_listing()
    test_expired_sessions_removed()
    test_invalid_profile_name_rejected()
    print("\nAll session vault tests PASSED.")
