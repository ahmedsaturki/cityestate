"""
Cookie Manager — إدارة الكوكيز
================================
Save, load, and inject cookies for Facebook, WhatsApp, and other platforms.
"""

import time
from pathlib import Path
from typing import Any

from src.session_vault.encryption import EncryptionManager


class CookieManager:
    """Manages browser cookies with encryption and expiration tracking."""

    def __init__(self, vault_dir: Path, encryption: EncryptionManager):
        self.vault_dir = vault_dir
        self.encryption = encryption
        self.cookies_dir = vault_dir / "cookies"
        self.cookies_dir.mkdir(parents=True, exist_ok=True)

    def save_cookies(self, platform: str, profile: str, cookies: list[dict]) -> Path:
        """
        Save cookies for a platform+profile combo.

        Args:
            platform: 'facebook', 'whatsapp', etc.
            profile: profile name (e.g., 'sidra', 'lara')
            cookies: list of cookie dicts from browser
        """
        cookie_file = self.cookies_dir / f"{platform}_{profile}.enc"
        cookie_data = {
            "platform": platform,
            "profile": profile,
            "cookies": cookies,
            "saved_at": time.time(),
            "expires_at": time.time() + (30 * 24 * 3600),  # 30 days
            "count": len(cookies),
        }
        self.encryption.save_encrypted_file(cookie_file, cookie_data)
        return cookie_file

    def load_cookies(self, platform: str, profile: str) -> list[dict]:
        """Load cookies for a platform+profile. Returns empty list if expired/missing."""
        cookie_file = self.cookies_dir / f"{platform}_{profile}.enc"
        data = self.encryption.load_encrypted_file(cookie_file)
        if data is None:
            return []
        if time.time() > data.get("expires_at", 0):
            self.clear_cookies(platform, profile)
            return []
        return data.get("cookies", [])

    def has_cookies(self, platform: str, profile: str) -> bool:
        """Check if valid cookies exist."""
        return len(self.load_cookies(platform, profile)) > 0

    def clear_cookies(self, platform: str, profile: str) -> None:
        """Delete cookies for a platform+profile."""
        cookie_file = self.cookies_dir / f"{platform}_{profile}.enc"
        if cookie_file.exists():
            cookie_file.unlink()

    def get_all_profiles(self) -> dict[str, list[str]]:
        """Get all saved platform+profile combos."""
        result: dict[str, list[str]] = {}
        for f in self.cookies_dir.glob("*.enc"):
            parts = f.stem.split("_", 1)
            if len(parts) == 2:
                platform, profile = parts
                result.setdefault(platform, []).append(profile)
        return result

    def get_cookie_stats(self) -> dict[str, Any]:
        """Get statistics about saved cookies."""
        stats = {"total_files": 0, "platforms": {}, "total_cookies": 0}
        for f in self.cookies_dir.glob("*.enc"):
            data = self.encryption.load_encrypted_file(f)
            if data:
                stats["total_files"] += 1
                stats["total_cookies"] += data.get("count", 0)
                platform = data.get("platform", "unknown")
                stats["platforms"].setdefault(platform, {"profiles": 0, "cookies": 0})
                stats["platforms"][platform]["profiles"] += 1
                stats["platforms"][platform]["cookies"] += data.get("count", 0)
        return stats
