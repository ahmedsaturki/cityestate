"""
Session Vault — خزنة الجلسات
============================
Persistent, encrypted storage for browser session cookies / localStorage /
Playwright state. Uses Fernet (AES-128-CBC + HMAC-SHA256) via EncryptionManager
keyed by `SESSION_VAULT_KEY`.

This module replaced the Phase-5 placeholder stub which silently returned
`{"status": "no_session"}` for every call — a no-op that broke WhatsApp
persistence across restarts.

Public surface used elsewhere:
    SessionVault()                  # default vault_dir = data/vault
    SessionVault(vault_dir="...")   # for tests / alternative paths

    vault.get_whatsapp_session(profile="default")  -> dict
    vault.get_facebook_session(profile="default")  -> dict
    vault.get_session_status(platform)             -> dict
    vault.save_session(platform, profile, data)    -> None
    vault.delete_session(platform, profile)        -> bool
    vault.list_profiles(platform)                  -> list[str]
"""
from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Any

from src.session_vault.encryption import EncryptionManager

logger = logging.getLogger("session_vault")

DEFAULT_VAULT_DIR = Path("data") / "vault"
SUPPORTED_PLATFORMS = ("whatsapp", "facebook")
SESSION_TTL_SECONDS = 30 * 24 * 3600  # 30 days


class SessionVault:
    """Encrypted persistent storage for browser sessions."""

    def __init__(self, vault_dir: str | os.PathLike | None = None):
        self.vault_dir = Path(vault_dir) if vault_dir else DEFAULT_VAULT_DIR
        self.vault_dir.mkdir(parents=True, exist_ok=True)
        # Lazy so import-time errors don't break other modules.
        self._enc: EncryptionManager | None = None

    # ------------------------------------------------------------------
    # Encryption access (lazy so missing SESSION_VAULT_KEY is reported on use)
    # ------------------------------------------------------------------
    @property
    def enc(self) -> EncryptionManager:
        """Lazily initialize and return the Fernet encryption manager."""
        if self._enc is None:
            self._enc = EncryptionManager()
        return self._enc

    # ------------------------------------------------------------------
    # Internal layout
    # ------------------------------------------------------------------
    def _session_path(self, platform: str, profile: str) -> Path:
        if platform not in SUPPORTED_PLATFORMS:
            raise ValueError(f"unsupported platform: {platform!r}")
        if not profile or any(ch in profile for ch in ("/", "\\", "..")):
            raise ValueError(f"invalid profile name: {profile!r}")
        return self.vault_dir / platform / f"{profile}.enc"

    @staticmethod
    def _empty_session(platform: str, profile: str) -> dict[str, Any]:
        return {
            "platform": platform,
            "profile": profile,
            "has_session": False,
            "cookies": [],
            "local_storage": {},
            "created_at": None,
            "updated_at": None,
            "expires_at": None,
        }

    def _read(self, platform: str, profile: str) -> dict[str, Any] | None:
        path = self._session_path(platform, profile)
        if not path.exists():
            return None
        try:
            data = self.enc.load_encrypted_file(path)
        except Exception as e:
            logger.warning(
                "Failed to decrypt %s session %r: %s — treating as missing",
                platform, profile, e,
            )
            return None
        if not isinstance(data, dict):
            return None
        # Auto-expire
        expires_at = data.get("expires_at")
        if expires_at and isinstance(expires_at, (int, float)) and expires_at < time.time():
            logger.info("Session %s/%s expired — removing", platform, profile)
            try:
                path.unlink(missing_ok=True)
            except Exception as e:
                logger.debug("Failed to remove expired session file: %s", e)
            return None
        return data

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def get_whatsapp_session(self, profile: str = "default") -> dict[str, Any]:
        """Load a WhatsApp session from disk. Returns empty session if missing."""
        session = self._read("whatsapp", profile)
        if session is None:
            return self._empty_session("whatsapp", profile)
        session.setdefault("platform", "whatsapp")
        session.setdefault("profile", profile)
        session["has_session"] = bool(session.get("cookies") or session.get("local_storage"))
        return session

    def get_facebook_session(self, profile: str = "default") -> dict[str, Any]:
        """Load a Facebook session from disk. Returns empty session if missing."""
        session = self._read("facebook", profile)
        if session is None:
            return self._empty_session("facebook", profile)
        session.setdefault("platform", "facebook")
        session.setdefault("profile", profile)
        session["has_session"] = bool(session.get("cookies") or session.get("local_storage"))
        return session

    def get_session_status(self, platform: str = "") -> dict[str, Any]:
        """Return the status of one or all platform vaults.

        With a `platform` argument, returns the same shape the rest of the
        codebase uses: `{"status": "ok"|"expired"|"no_session", ...}`.
        Without it, returns a summary across all platforms.
        """
        if platform:
            if platform not in SUPPORTED_PLATFORMS:
                return {"status": "error", "message": f"unsupported platform {platform!r}"}
            profiles = self.list_profiles(platform)
            if not profiles:
                return {
                    "status": "no_session",
                    "platform": platform,
                    "vault_dir": str(self.vault_dir),
                }
            # Most recent session
            latest_path = max(
                (self.vault_dir / platform / p for p in profiles),
                key=lambda p: p.stat().st_mtime,
                default=None,
            )
            return {
                "status": "ok",
                "platform": platform,
                "profile_count": len(profiles),
                "vault_dir": str(self.vault_dir),
                "latest_session": str(latest_path.name) if latest_path else None,
            }
        # Summary across all platforms
        return {
            "vault_dir": str(self.vault_dir),
            "platforms": {
                p: {
                    "profile_count": len(self.list_profiles(p)),
                    "profiles": self.list_profiles(p),
                }
                for p in SUPPORTED_PLATFORMS
            },
        }

    def save_session(
        self,
        platform: str,
        profile: str,
        data: dict[str, Any],
    ) -> None:
        """Encrypt and persist a session dict.

        Caller is expected to include cookies / localStorage / playwright state.
        Adds `created_at`, `updated_at`, `expires_at` metadata if missing.
        """
        path = self._session_path(platform, profile)
        now = time.time()
        payload = dict(data)
        payload.setdefault("platform", platform)
        payload.setdefault("profile", profile)
        payload.setdefault("created_at", now)
        payload["updated_at"] = now
        payload["expires_at"] = now + SESSION_TTL_SECONDS
        self.enc.save_encrypted_file(path, payload)
        logger.info("Saved %s/%s session to vault (%d bytes)",
                    platform, profile, path.stat().st_size)

    def delete_session(self, platform: str, profile: str) -> bool:
        """Delete an encrypted session file for the given platform and profile.

        Returns True if the file was found and deleted, False if it did not exist.
        """
        path = self._session_path(platform, profile)
        if not path.exists():
            return False
        path.unlink()
        logger.info("Deleted %s/%s session from vault", platform, profile)
        return True

    def list_profiles(self, platform: str) -> list[str]:
        """List all saved session profile names for the given platform."""
        if platform not in SUPPORTED_PLATFORMS:
            return []
        d = self.vault_dir / platform
        if not d.exists():
            return []
        return sorted(p.stem for p in d.glob("*.enc"))
