"""Test configuration and shared fixtures."""
import hashlib
import hmac
import os
import warnings
from pathlib import Path

import pytest
from fastapi.testclient import TestClient as _OriginalTestClient

# ---------------------------------------------------------------------------
# Auto-lifespan TestClient
# ---------------------------------------------------------------------------
# FastAPI ≥ 0.110 / Starlette ≥ 0.33 no longer starts the app lifespan when
# ``TestClient(app)`` is created — the caller must use a ``with`` block.
# Almost every test file in this project creates ``TestClient(app)`` directly
# without a context manager, so tables are never created and admin is never
# seeded.  Patching TestClient here ensures every TestClient instance
# auto-enters its lifespan on creation, keeping the test suite working
# without rewriting every test file.
# ---------------------------------------------------------------------------

class _AutoLifespanTestClient(_OriginalTestClient):
    """TestClient that automatically enters/exits the app lifespan."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Start the lifespan (creates tables, seeds admin, etc.)
        self.__enter__()
        self._lifespan_active = True

    def close(self):
        if getattr(self, "_lifespan_active", False):
            self.__exit__(None, None, None)
            self._lifespan_active = False
        super().close()


# Replace FastAPI's TestClient globally so all test modules use our version.
import fastapi.testclient
fastapi.testclient.TestClient = _AutoLifespanTestClient
# Also patch starlette.testclient since that's the actual implementation
import starlette.testclient
starlette.testclient.TestClient = _AutoLifespanTestClient

# ---------------------------------------------------------------------------
# Environment — set BEFORE any src.* imports (deps.py reads DATABASE_URL
# at import time).
# ---------------------------------------------------------------------------
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-key-not-for-production")
os.environ.setdefault("SESSION_VAULT_KEY", "test-session-vault-key-not-for-production")
os.environ.setdefault("WEBHOOK_SECRET_TEST", "test-webhook-secret-not-for-production")
os.environ.setdefault("ADMIN_PASSWORD", "C1ty3st@t3_S3cur3_2024!")

# Dedicated test database — never touch the development DB.
_TEST_DB = Path(__file__).parent.parent / "output" / "test_cityestate.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB.as_posix()}"

# Suppress noisy warnings from external libraries
warnings.filterwarnings("ignore", category=DeprecationWarning, module="starlette")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="sqlalchemy")
warnings.filterwarnings("ignore", message=".*pytest.mark.asyncio.*")


@pytest.fixture(autouse=True, scope="session")
def _clear_rate_limiter():
    """Reset the in-memory login rate limiter before the test suite runs.

    The rate limiter in ``src.api.auth._login_attempts`` persists across
    test modules within the same process.  Intentionally-failed logins
    (``test_login_invalid``) in one module can lock out subsequent modules.
    Clearing the dict at session start prevents false 429s.
    """
    try:
        from src.api.auth import _login_attempts
        _login_attempts.clear()
    except ImportError:
        pass
