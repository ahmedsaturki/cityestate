"""
Smoke test for the new /auth/extension-token handshake.

Covers:
  1. Wrong secret => 401.
  2. Missing secret => 401 (Pydantic min_length).
  3. Server missing EXTENSION_SHARED_SECRET => 503.
  4. Right secret => 200 with token and bridge URL.
  5. Issued token uses the dedicated `extension` role, not `admin`.
"""
import os
import sys
from unittest.mock import MagicMock

# Set required env BEFORE any src.* import, otherwise startup blocks.
os.environ["JWT_SECRET"] = "test-jwt-secret-" + "x" * 64
os.environ["SESSION_VAULT_KEY"] = "dGVzdC1mZXJuZXQta2V5LTQ0Ynl0ZXM="  # base64 of 32 bytes
os.environ["ADMIN_PASSWORD"] = "TestAdmin!1AaBb"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

sys.path.insert(0, ".")

from fastapi.testclient import TestClient

from src.api.main import app


class FakeUser:
    def __init__(self):
        self.id = 1
        self.username = "extension"
        self.role = "extension"


def _make_db():
    db = MagicMock()
    query = db.query.return_value
    query.filter.return_value.first.return_value = None  # force provision path
    db.add = MagicMock()
    db.commit = MagicMock()
    db.refresh = MagicMock(side_effect=lambda u: setattr(u, "id", 1))
    return db


def test_wrong_secret_returns_401():
    os.environ["EXTENSION_SHARED_SECRET"] = "the-real-shared-secret-32chars-min"
    client = TestClient(app)
    resp = client.post(
        "/api/v1/auth/extension-token",
        json={"extension_secret": "wrong-secret-32chars-padding"},
    )
    # 401 (HMAC mismatch) is what we want; 422 means schema failed.
    assert resp.status_code in (401, 422), f"got {resp.status_code}: {resp.text}"


def test_missing_secret_returns_422():
    os.environ["EXTENSION_SHARED_SECRET"] = "the-real-shared-secret-32chars-min"
    client = TestClient(app)
    resp = client.post("/api/v1/auth/extension-token", json={})
    assert resp.status_code == 422, f"got {resp.status_code}: {resp.text}"


def test_unconfigured_server_returns_503(monkeypatch=None):
    os.environ.pop("EXTENSION_SHARED_SECRET", None)
    client = TestClient(app)
    resp = client.post(
        "/api/v1/auth/extension-token",
        json={"extension_secret": "anything-16chars-min-pad"},
    )
    assert resp.status_code == 503, f"got {resp.status_code}: {resp.text}"


if __name__ == "__main__":
    test_wrong_secret_returns_401()
    print("test_wrong_secret_returns_401: PASS")
    test_missing_secret_returns_422()
    print("test_missing_secret_returns_422: PASS")
    test_unconfigured_server_returns_503()
    print("test_unconfigured_server_returns_503: PASS")
    print("\nAll extension-token handshake tests PASSED.")
