"""Test configuration and shared fixtures."""
import hashlib
import hmac
import os
import warnings

# Set required environment variables for tests before any imports
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-key-not-for-production")
os.environ.setdefault("SESSION_VAULT_KEY", "test-session-vault-key-not-for-production")
os.environ.setdefault("WEBHOOK_SECRET_TEST", "test-webhook-secret-not-for-production")

# Suppress deprecation warnings from external libraries
warnings.filterwarnings("ignore", category=DeprecationWarning, module="starlette")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="sqlalchemy")
warnings.filterwarnings("ignore", message=".*pytest.mark.asyncio.*")
