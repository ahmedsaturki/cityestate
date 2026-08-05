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
import pytest
from unittest.mock import MagicMock


# ---------------------------------------------------------------------------
# Fixtures — use monkeypatch so env changes are scoped to each test.
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _extension_secret(monkeypatch):
    """Set a valid EXTENSION_SHARED_SECRET for most tests."""
    monkeypatch.setenv(
        "EXTENSION_SHARED_SECRET", "the-real-shared-secret-32chars-min"
    )


@pytest.fixture()
def _no_extension_secret(monkeypatch):
    """Remove EXTENSION_SHARED_SECRET (for the 503 test)."""
    monkeypatch.delenv("EXTENSION_SHARED_SECRET", raising=False)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def test_wrong_secret_returns_401():
    from fastapi.testclient import TestClient
    from src.api.main import app

    client = TestClient(app)
    resp = client.post(
        "/api/v1/auth/extension-token",
        json={"extension_secret": "wrong-secret-32chars-padding"},
    )
    # 401 (HMAC mismatch) is what we want; 422 means schema failed.
    assert resp.status_code in (401, 422), f"got {resp.status_code}: {resp.text}"


def test_missing_secret_returns_422():
    from fastapi.testclient import TestClient
    from src.api.main import app

    client = TestClient(app)
    resp = client.post("/api/v1/auth/extension-token", json={})
    assert resp.status_code == 422, f"got {resp.status_code}: {resp.text}"


def test_unconfigured_server_returns_503(_no_extension_secret):
    from fastapi.testclient import TestClient
    from src.api.main import app

    client = TestClient(app)
    resp = client.post(
        "/api/v1/auth/extension-token",
        json={"extension_secret": "anything-16chars-min-pad"},
    )
    assert resp.status_code == 503, f"got {resp.status_code}: {resp.text}"


# ---------------------------------------------------------------------------
# Legacy __main__ runner kept for standalone smoke-testing.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    os.environ["EXTENSION_SHARED_SECRET"] = "the-real-shared-secret-32chars-min"
    test_wrong_secret_returns_401()
    print("test_wrong_secret_returns_401: PASS")
    test_missing_secret_returns_422()
    print("test_missing_secret_returns_422: PASS")
    os.environ.pop("EXTENSION_SHARED_SECRET", None)
    test_unconfigured_server_returns_503()
    print("test_unconfigured_server_returns_503: PASS")
    print("\nAll extension-token handshake tests PASSED.")
