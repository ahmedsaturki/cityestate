"""
Encrypted backups — create Fernet-encrypted ZIP archives of DB + vault.

Why this module exists:
    The legacy `main.py:run_backup()` copied files with `shutil.copy2`
    and labelled them "encrypted". They were not. Anyone with read access
    to `output/backups/` got the live database, the WhatsApp session
    cookies, and any plaintext `.env` already there. This module fixes that.

Format:
    backups/backup_<UTC-ISO>.zip.age
    A ZIP archive (deflate) containing:
        cityestate.db          — SQLite database file
        vault/                 — encrypted vault directory (already Fernet-encrypted)
        manifest.json          — {created_at, app_version, file_count, sha256_hashes}
    The whole archive is then Fernet-encrypted with `SESSION_VAULT_KEY`.
    The `.age` extension is a hint; the file is base64-armoured Fernet
    ciphertext.

Restore:
    `python -m src.backup.encrypted_restore path/to/backup.zip.age <dest>`
    See scripts/restore_backup.py for a friendly wrapper.
"""

from __future__ import annotations

import hashlib
import io
import json
import logging
import os
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from src.session_vault.encryption import EncryptionManager

logger = logging.getLogger("backup")

BACKUP_VERSION = 1


def _utc_now_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _fernet_from_vault_key() -> Fernet:
    """Build a Fernet instance from SESSION_VAULT_KEY.

    Mirrors EncryptionManager._derive_fernet_key to ensure backups made
    here can be restored by EncryptionManager.decrypt on the same host.
    """
    return Fernet(EncryptionManager._derive_fernet_key(os.environ["SESSION_VAULT_KEY"]))


def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def create_backup(
    *,
    project_root: Path,
    backup_dir: Path,
    db_path: Path,
    vault_dir: Path,
    retain_count: int = 7,
) -> dict:
    """Create an encrypted backup.

    Args:
        project_root: project root (for relative path display only).
        backup_dir: target directory for the `.zip.age` artifact.
        db_path: SQLite database file to include.
        vault_dir: vault directory to include (already encrypted at rest).
        retain_count: number of recent backups to keep after this one
            (the rest are moved to `<backup_dir>/.trash/` rather than
            deleted, so a restore in-flight across containers is never
            destroyed by a concurrent cleanup pass).

    Returns:
        {status, artifact_path, size_bytes, sha256}
    """
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = _utc_now_compact()

    # Guard against same-second collisions across containers (two
    # schedulers, two pods, etc.). If the file already exists, append
    # a counter.  The canonical path is still the timestamp-only one;
    # the collision suffix is only for uniqueness.
    artifact_path = backup_dir / f"backup_{timestamp}.zip.age"
    if artifact_path.exists():
        artifact_path = backup_dir / f"backup_{timestamp}_N{os.getpid()}.zip.age"

    trash_dir = backup_dir / ".trash"
    trash_dir.mkdir(exist_ok=True)

    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "backup_version": BACKUP_VERSION,
        "files": [],
    }

    # Build the ZIP in memory, then Fernet-encrypt the whole blob.
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        if db_path.exists():
            arcname = f"db/{db_path.name}"
            zf.write(db_path, arcname=arcname)
            manifest["files"].append({
                "path": arcname,
                "sha256": _hash_file(db_path),
                "size": db_path.stat().st_size,
            })

        if vault_dir.exists():
            for src in sorted(vault_dir.rglob("*")):
                if src.is_dir():
                    continue
                rel = src.relative_to(vault_dir).as_posix()
                arcname = f"vault/{rel}"
                zf.write(src, arcname=arcname)
                manifest["files"].append({
                    "path": arcname,
                    "sha256": _hash_file(src),
                    "size": src.stat().st_size,
                })

        # Also include the manifest itself (at archive root).
        manifest_bytes = json.dumps(manifest, indent=2).encode("utf-8")
        zf.writestr("manifest.json", manifest_bytes)

    # Encrypt the whole archive.
    fernet = _fernet_from_vault_key()
    ciphertext = fernet.encrypt(buf.getvalue())

    artifact_path.write_bytes(ciphertext)
    sha = hashlib.sha256(ciphertext).hexdigest()

    logger.info(
        "Backup written: %s (%d bytes, %d files, sha256=%s)",
        artifact_path,
        artifact_path.stat().st_size,
        len(manifest["files"]),
        sha[:12],
    )

    # Retention cleanup — move excess to `.trash/` so a concurrent
    # restore (from another container) is never destroyed.
    _cleanup_old(backup_dir, retain=retain_count, trash_dir=trash_dir)

    # Purge trash older than 24h in the same process so the window
    # between move and final deletion stays short.
    _purge_trash(trash_dir, max_age_hours=24.0)

    return {
        "status": "success",
        "artifact_path": str(artifact_path),
        "size_bytes": artifact_path.stat().st_size,
        "files_backed_up": len(manifest["files"]),
        "sha256": sha,
        "timestamp": timestamp,
    }


def _cleanup_old(backup_dir: Path, *, retain: int, trash_dir: Path) -> int:
    """Move excess backups to `.trash/` instead of deleting them.

    Moving (not deleting) protects in-flight restores from race
    conditions where a concurrent cleanup pass discovers a file
    that is mid-restore and removes it.  `restore_backup.py`
    looks in `.trash/` first if the canonical path is missing,
    so restored containers can still recover trashed backups.
    """
    if retain <= 0:
        return 0
    artifacts = sorted(
        (p for p in backup_dir.glob("backup_*.zip.age") if p.is_file() and p.parent == backup_dir),
        key=lambda p: p.name,
        reverse=True,
    )
    moved = 0
    for old in artifacts[retain:]:
        try:
            dest = trash_dir / old.name
            old.replace(dest)  # atomic on same filesystem
            moved += 1
            logger.info("Moved old backup to trash: %s -> %s", old.name, dest)
        except OSError as e:
            logger.warning("Failed to trash old backup %s: %s", old.name, e)
    return moved


def _purge_trash(trash_dir: Path, max_age_hours: float = 24.0) -> int:
    """Delete archived backups in `.trash/` older than `max_age_hours`.

    Must be called from the backup writer (same process), never from
    a concurrent reader, to avoid TOCTOU races.
    """
    if not trash_dir.exists():
        return 0
    cutoff = datetime.now(timezone.utc).timestamp() - (max_age_hours * 3600)
    purged = 0
    for old in trash_dir.glob("backup_*.zip.age"):
        try:
            if old.stat().st_mtime < cutoff:
                old.unlink()
                purged += 1
                logger.info("Purged trashed backup: %s", old.name)
        except OSError as e:
            logger.warning("Failed to purge trashed backup %s: %s", old.name, e)
    return purged


def restore_backup(artifact: Path, dest_dir: Path) -> dict:
    """Restore a backup archive. Returns summary.

    Falls back to `<backup_dir>/.trash/<name>` if the canonical path
    does not exist — useful when a concurrent cleanup run already
    moved the artifact away but the restore target has not.
    """
    if not artifact.exists():
        # Check trash as a fallback for race-safe restores.
        trash_candidate = artifact.parent.parent / ".trash" / artifact.name
        if trash_candidate.exists():
            logger.info(
                "Canonical artifact missing, falling back to trash: %s",
                trash_candidate,
            )
            artifact = trash_candidate
        else:
            raise FileNotFoundError(artifact)
    fernet = _fernet_from_vault_key()
    try:
        plaintext = fernet.decrypt(artifact.read_bytes())
    except InvalidToken as e:
        raise RuntimeError(
            "Cannot decrypt backup — wrong SESSION_VAULT_KEY or corrupted file."
        ) from e

    dest_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(plaintext)) as zf:
        zf.extractall(dest_dir)
        names = zf.namelist()
    return {
        "status": "success",
        "restored_to": str(dest_dir),
        "files": len(names),
    }


def main() -> int:
    """CLI: `python -m src.backup.encrypted_backup` to run a one-shot backup."""
    from src.session_vault.encryption import EncryptionManager

    project_root = Path(os.environ.get("PROJECT_ROOT", ".")).resolve()
    backup_dir = project_root / "output" / "backups"
    db_path = project_root / "output" / "cityestate.db"
    vault_dir = project_root / "output" / "vault"

    try:
        EncryptionManager()  # validates SESSION_VAULT_KEY presence.
    except RuntimeError as e:
        print(f"FATAL: {e}", file=sys.stderr)
        return 2

    result = create_backup(
        project_root=project_root,
        backup_dir=backup_dir,
        db_path=db_path,
        vault_dir=vault_dir,
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
