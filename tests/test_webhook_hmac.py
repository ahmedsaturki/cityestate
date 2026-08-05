"""
Smoke test for /webhooks/form HMAC auth.

Covers:
  1. No signature header => 401.
  2. Wrong signature => 401.
  3. Server has no WEBHOOK_SECRET_* env vars => 503.
  4. Right signature => 200, Lead created, ClientRequest enqueued for matching.
"""
import hashlib
import hmac
import json
import os
import pytest


# ---------------------------------------------------------------------------
# Fixtures — do NOT touch DATABASE_URL or ADMIN_PASSWORD; the shared test
# infrastructure in conftest.py manages those.  Only set webhook-specific
# secrets via monkeypatch so the original values are restored after each test.
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _webhook_secrets(monkeypatch):
    """Ensure WEBHOOK_SECRET_TALLY is set for most tests."""
    monkeypatch.setenv("WEBHOOK_SECRET_TALLY", "real-secret-32chars-padding-here")


@pytest.fixture()
def _no_webhook_secrets(monkeypatch):
    """Remove all WEBHOOK_SECRET_* vars (for the 503 test)."""
    for key in [k for k in list(os.environ) if k.startswith("WEBHOOK_SECRET_")]:
        monkeypatch.delenv(key, raising=False)


def _sign(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def test_no_signature_returns_401():
    from fastapi.testclient import TestClient
    from src.api.main import app

    client = TestClient(app)
    resp = client.post(
        "/api/v1/webhooks/form",
        json={"phone": "+201234567890", "name": "Test"},
    )
    assert resp.status_code == 401, f"got {resp.status_code}: {resp.text}"


def test_wrong_signature_returns_401():
    from fastapi.testclient import TestClient
    from src.api.main import app

    client = TestClient(app)
    resp = client.post(
        "/api/v1/webhooks/form",
        json={"phone": "+201234567890"},
        headers={"X-Webhook-Signature": "deadbeef" * 8},
    )
    assert resp.status_code == 401, f"got {resp.status_code}: {resp.text}"


def test_no_secrets_configured_returns_503(_no_webhook_secrets):
    from fastapi.testclient import TestClient
    from src.api.main import app

    client = TestClient(app)
    body = b'{"phone":"+201234567890"}'
    resp = client.post(
        "/api/v1/webhooks/form",
        content=body,
        headers={
            "X-Webhook-Signature": "x",
            "Content-Type": "application/json",
        },
    )
    assert resp.status_code == 503, f"got {resp.status_code}: {resp.text}"


def test_correct_signature_returns_200():
    from fastapi.testclient import TestClient
    from src.api.main import app

    secret = "real-secret-32chars-padding-here"
    client = TestClient(app)
    body_dict = {
        "phone": "+201234567890",
        "name": "Smoke Test",
        "max_budget": 5000000,
    }
    body = json.dumps(body_dict).encode("utf-8")
    sig = _sign(body, secret)
    resp = client.post(
        "/api/v1/webhooks/form",
        content=body,
        headers={
            "X-Webhook-Signature": sig,
            "Content-Type": "application/json",
        },
    )
    assert resp.status_code == 200, f"got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data["status"] == "received"
    assert data["lead_id"] is not None
    assert data["request_id"] is not None
    assert data["matches_found"] == 0  # queued, not run inline


# ---------------------------------------------------------------------------
# Legacy __main__ runner kept for standalone smoke-testing.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    os.environ["WEBHOOK_SECRET_TALLY"] = "real-secret-32chars-padding-here"
    test_no_signature_returns_401()
    print("test_no_signature_returns_401: PASS")
    test_wrong_signature_returns_401()
    print("test_wrong_signature_returns_401: PASS")
    test_no_secrets_configured_returns_503()
    print("test_no_secrets_configured_returns_503: PASS")
    test_correct_signature_returns_200()
    print("test_correct_signature_returns_200: PASS")
    print("\nAll webhook HMAC tests PASSED.")
