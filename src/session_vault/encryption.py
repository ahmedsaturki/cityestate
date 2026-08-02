"""
Encryption Manager — تشفير الجلسات
===================================
Fernet (AES-128-CBC + HMAC SHA256) for session data,
bcrypt for password hashing.

Backward-compatibility note on `PASSWORD_SALT`:
    Earlier code claimed to use `PASSWORD_SALT` to derive password hashes.
    In practice it never did — bcrypt handled its own internal per-hash salt.
    To preserve any existing hash format in production databases, we keep
    bcrypt's own salt generation as the default. If the operator explicitly
    opts in via `USE_LEGACY_SALT=1`, new passwords will be hashed with the
    env salt prepended (legacy format). Existing bcrypt hashes still verify
    because they carry their own salt.
"""

import base64
import json
import logging
import os
from pathlib import Path
from typing import Any

import bcrypt
from cryptography.fernet import Fernet

logger = logging.getLogger("encryption")

# Warn once at import time if SESSION_VAULT_KEY is missing (non-fatal).
if not os.getenv("SESSION_VAULT_KEY"):
    logger.warning(
        "SESSION_VAULT_KEY is not set. Encryption operations will "
        "fail at runtime until SESSION_VAULT_KEY is configured.\n"
        "Generate one with:\n"
        "  python scripts/bootstrap_env.py --rotate SESSION_VAULT_KEY"
    )


class EncryptionManager:
    """
    Production-grade encryption for session data and passwords.

    - Session data: Fernet (AES-128-CBC + HMAC-SHA256), keyed by `SESSION_VAULT_KEY`.
    - Passwords: bcrypt with automatic per-hash salt. `PASSWORD_SALT` is a
      deprecated no-op kept for backward compatibility; set `USE_LEGACY_SALT=1`
      to opt in to the legacy salt-prefixing format.
    """

    _legacy_salt_warned: bool = False

    def __init__(self, master_key: str | None = None):
        if master_key is None:
            master_key = os.getenv("SESSION_VAULT_KEY")
        if not master_key:
            logger.warning(
                "SESSION_VAULT_KEY not configured — "
                "EncryptionManager is unusable until the key is set."
            )
            self._key = None
            return
        self._key = self._derive_fernet_key(master_key)

        # Warn once if PASSWORD_SALT is set but legacy mode is off.
        if os.getenv("PASSWORD_SALT") and os.getenv("USE_LEGACY_SALT") != "1":
            if not EncryptionManager._legacy_salt_warned:
                logger.warning(
                    "PASSWORD_SALT is set but USE_LEGACY_SALT!=1 — bcrypt's own salt is used. "
                    "PASSWORD_SALT is currently a no-op kept for backward compatibility."
                )
                EncryptionManager._legacy_salt_warned = True

    @staticmethod
    def _derive_fernet_key(master_key: str, salt: bytes = b"cityestate-vault-salt-v1") -> bytes:
        """Derive a valid Fernet key from any string using PBKDF2.

        Uses PBKDF2-HMAC-SHA256 with 100,000 iterations for key derivation,
        which is significantly more secure than plain SHA-256.
        """
        import hashlib
        dk = hashlib.pbkdf2_hmac(
            "sha256",
            master_key.encode("utf-8"),
            salt,
            iterations=100_000,
            dklen=32,
        )
        return base64.urlsafe_b64encode(dk)

    def _require_key(self) -> bytes:
        """Return the Fernet key or raise an HTTPException-style error."""
        if self._key is None:
            raise RuntimeError(
                "SESSION_VAULT_KEY is not configured. "
                "Run `python scripts/bootstrap_env.py --rotate SESSION_VAULT_KEY`."
            )
        return self._key

    def encrypt(self, data: Any) -> str:
        """Encrypt any JSON-serializable data to a Fernet token string."""
        key = self._require_key()
        json_bytes = json.dumps(data, ensure_ascii=False).encode("utf-8")
        f = Fernet(key)
        encrypted = f.encrypt(json_bytes)
        return encrypted.decode("ascii")

    def decrypt(self, token: str) -> Any:
        """Decrypt a Fernet token back to original data."""
        key = self._require_key()
        f = Fernet(key)
        decrypted = f.decrypt(token.encode("ascii"))
        return json.loads(decrypted.decode("utf-8"))

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt with automatic salt.

        When `USE_LEGACY_SALT=1` and `PASSWORD_SALT` is set, the salt is
        prepended to the password before bcrypt (legacy format). Otherwise
        bcrypt generates its own per-hash salt.
        """
        password_bytes = password.encode("utf-8")
        legacy_salt = os.getenv("PASSWORD_SALT", "")
        if os.getenv("USE_LEGACY_SALT") == "1" and legacy_salt:
            legacy_salt_bytes = legacy_salt.encode("utf-8")
            salted = legacy_salt_bytes + b":" + password_bytes
            hashed = bcrypt.hashpw(salted, bcrypt.gensalt(rounds=12))
        else:
            hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt(rounds=12))
        return hashed.decode("utf-8")

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """Verify a password against its bcrypt hash.

        Tries the modern format first, then the legacy salt-prefixed format
        so existing users with legacy hashes can still log in.
        """
        try:
            if bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8")):
                return True
        except (ValueError, TypeError):
            pass

        legacy_salt = os.getenv("PASSWORD_SALT", "")
        if legacy_salt:
            try:
                salted = legacy_salt.encode("utf-8") + b":" + password.encode("utf-8")
                if bcrypt.checkpw(salted, hashed.encode("utf-8")):
                    return True
            except (ValueError, TypeError):
                return False
        return False

    def save_encrypted_file(self, path: Path, data: Any) -> None:
        """Save encrypted data to file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        encrypted = self.encrypt(data)
        path.write_text(encrypted, encoding="utf-8")

    def load_encrypted_file(self, path: Path) -> Any:
        """Load and decrypt data from file."""
        if not path.exists():
            return None
        encrypted = path.read_text(encoding="utf-8")
        return self.decrypt(encrypted)
