"""
Browser Profile — إدارة ملفات المتصفح
=======================================
Persistent browser user-data-dir profiles for session reuse.
"""

import time
from pathlib import Path
from typing import Any

from src.session_vault.encryption import EncryptionManager


class BrowserProfile:
    """Manages isolated browser profiles for multi-account support."""

    # Platform-specific launch args
    PLATFORM_ARGS = {
        "whatsapp": [
            "--disable-blink-features=AutomationControlled",
            "--no-first-run",
            "--disable-extensions",
        ],
        "facebook": [
            "--disable-blink-features=AutomationControlled",
            "--no-first-run",
            "--disable-extensions",
            "--disable-popup-blocking",
        ],
    }

    def __init__(self, vault_dir: Path, encryption: EncryptionManager):
        self.vault_dir = vault_dir
        self.encryption = encryption
        self.profiles_dir = vault_dir / "profiles"
        self.profiles_dir.mkdir(parents=True, exist_ok=True)

    def create_profile(self, name: str, platform: str) -> Path:
        """
        Create a new browser profile directory.

        Args:
            name: profile name (e.g., 'sidra', 'lara')
            platform: 'whatsapp', 'facebook', etc.
        Returns:
            Path to the user-data-dir
        """
        profile_dir = self.profiles_dir / f"{platform}_{name}"
        profile_dir.mkdir(parents=True, exist_ok=True)

        meta_file = profile_dir / "profile.json"
        meta = {
            "name": name,
            "platform": platform,
            "created_at": time.time(),
            "last_used": None,
            "launch_count": 0,
            "is_authenticated": False,
        }
        self.encryption.save_encrypted_file(meta_file, meta)
        return profile_dir

    def get_profile(self, name: str, platform: str) -> Path | None:
        """Get existing profile directory."""
        profile_dir = self.profiles_dir / f"{platform}_{name}"
        if profile_dir.exists():
            return profile_dir
        return None

    def update_meta(self, name: str, platform: str, updates: dict) -> None:
        """Update profile metadata."""
        profile_dir = self.profiles_dir / f"{platform}_{name}"
        meta_file = profile_dir / "profile.json"
        meta = self.encryption.load_encrypted_file(meta_file) or {}
        meta.update(updates)
        meta["last_used"] = time.time()
        meta["launch_count"] = meta.get("launch_count", 0) + 1
        self.encryption.save_encrypted_file(meta_file, meta)

    def get_launch_args(self, platform: str, profile: str) -> list[str]:
        """Get Chromium launch arguments for a platform profile."""
        profile_dir = self.get_profile(profile, platform)
        if not profile_dir:
            profile_dir = self.create_profile(profile, platform)
        args = self.PLATFORM_ARGS.get(platform, [])
        return [
            f"--user-data-dir={profile_dir}",
            *args,
        ]

    def list_profiles(self) -> list[dict[str, Any]]:
        """List all profiles with metadata."""
        profiles = []
        for d in self.profiles_dir.iterdir():
            if d.is_dir():
                meta_file = d / "profile.json"
                meta = self.encryption.load_encrypted_file(meta_file) or {}
                profiles.append({
                    "dir": str(d),
                    "name": meta.get("name", "unknown"),
                    "platform": meta.get("platform", "unknown"),
                    "created_at": meta.get("created_at"),
                    "last_used": meta.get("last_used"),
                    "launch_count": meta.get("launch_count", 0),
                    "is_authenticated": meta.get("is_authenticated", False),
                })
        return profiles

    def delete_profile(self, name: str, platform: str) -> bool:
        """Delete a profile and all its data."""
        import shutil
        profile_dir = self.get_profile(name, platform)
        if profile_dir and profile_dir.exists():
            shutil.rmtree(profile_dir)
            return True
        return False
