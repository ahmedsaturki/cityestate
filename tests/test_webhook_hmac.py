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
import os
import sys
import tempfile

# Use a shared file-based sqlite so the request thread sees the same tables.
_TEST_DB = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB}"
os.environ["JWT_SECRET"] = "test-jwt-secret-" + "x" * 64
os.environ["SESSION_VAULT_KEY"] = "dGVzdC1mZXJuZXQta2V5LTQ0Ynl0ZXM="
os.environ["ADMIN_PASSWORD"] = "TestAdmin!1AaBb"

sys.path.insert(0, ".")

from fastapi.testclient import TestClient

from src.api.main import app
from src.database.models import Base
from src.api.deps import engine

# Initialise the schema on the already-configured engine.
Base.metadata.create_all(engine)


def _sign(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_no_signature_returns_401():
    os.environ.pop("WEBHOOK_SECRET_TALLY", None)
    os.environ["WEBHOOK_SECRET_TALLY"] = "real-secret-32chars-padding-here"
    client = TestClient(app)
    resp = client.post(
        "/api/v1/webhooks/form",
        json={"phone": "+201234567890", "name": "Test"},
    )
    assert resp.status_code == 401, f"got {resp.status_code}: {resp.text}"


def test_wrong_signature_returns_401():
    os.environ["WEBHOOK_SECRET_TALLY"] = "real-secret-32chars-padding-here"
    client = TestClient(app)
    resp = client.post(
        "/api/v1/webhooks/form",
        json={"phone": "+201234567890"},
        headers={"X-Webhook-Signature": "deadbeef" * 8},
    )
    assert resp.status_code == 401, f"got {resp.status_code}: {resp.text}"


def test_no_secrets_configured_returns_503():
    for k in [k for k in os.environ if k.startswith("WEBHOOK_SECRET_")]:
        del os.environ[k]
    client = TestClient(app)
    body = b'{"phone":"+201234567890"}'
    resp = client.post(
        "/api/v1/webhooks/form",
        content=body,
        headers={"X-Webhook-Signature": "x", "Content-Type": "application/json"},
    )
    assert resp.status_code == 503, f"got {resp.status_code}: {resp.text}"


def test_correct_signature_returns_200():
    secret = "real-secret-32chars-padding-here"
    os.environ["WEBHOOK_SECRET_TALLY"] = secret
    client = TestClient(app)
    import json
    body_dict = {"phone": "+201234567890", "name": "Smoke Test", "max_budget": 5000000}
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


if __name__ == "__main__":
    test_no_signature_returns_401()
    print("test_no_signature_returns_401: PASS")
    test_wrong_signature_returns_401()
    print("test_wrong_signature_returns_401: PASS")
    test_no_secrets_configured_returns_503()
    print("test_no_secrets_configured_returns_503: PASS")
    test_correct_signature_returns_200()
    print("test_correct_signature_returns_200: PASS")
    print("\nAll webhook HMAC tests PASSED.")
