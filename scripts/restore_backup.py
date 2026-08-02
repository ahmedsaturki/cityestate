"""
Restore an encrypted backup artifact.

Usage:
    python scripts/restore_backup.py <backup.zip.age> [<destination>]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.backup.encrypted_backup import restore_backup


def main() -> int:
    parser = argparse.ArgumentParser(description="Restore a CityEstate encrypted backup.")
    parser.add_argument("artifact", type=Path, help="Path to backup_*.zip.age")
    parser.add_argument("dest", type=Path, nargs="?", default=Path("./restore_tmp"),
                        help="Destination directory (default: ./restore_tmp)")
    args = parser.parse_args()

    try:
        result = restore_backup(args.artifact, args.dest)
    except (FileNotFoundError, RuntimeError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    print(f"Restored {result['files']} files to {result['restored_to']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
