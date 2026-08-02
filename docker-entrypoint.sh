#!/bin/bash
# CityEstate — Docker Entrypoint
# Copies DB from bind mount to container-local path (avoids Windows file locks)
set -e

SRC="/app/output/cityestate.db"
DST="/app/data/cityestate.db"

# Copy DB if source exists and destination doesn't (or is older)
if [ -f "$SRC" ]; then
    mkdir -p /app/data
    cp -u "$SRC" "$DST"
    # Copy WAL/SHM too if they exist and are non-empty
    [ -f "$SRC-wal" ] && [ -s "$SRC-wal" ] && cp "$SRC-wal" "$DST-wal" 2>/dev/null || true
    [ -f "$SRC-shm" ] && cp "$SRC-shm" "$DST-shm" 2>/dev/null || true
    echo "[entrypoint] DB copied to $DST"
fi

# Override DATABASE_URL to use local copy
export DATABASE_URL="sqlite:///$DST"

exec "$@"
