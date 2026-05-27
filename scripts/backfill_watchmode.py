"""
Backfill streaming_sources for all entries with an imdb_id, using the Watchmode API.

Usage (from project root):
    python scripts/backfill_watchmode.py

Safe to re-run — overwrites existing streaming_sources values with fresh data.
Only processes entries where imdb_id IS NOT NULL.
"""

import io
import json
import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

import httpx
from sqlalchemy import text

from app.database import SessionLocal, engine
from app.models.catalog import Entry

WATCHMODE_URL = "https://api.watchmode.com/v1/title/{imdb_id}/sources/"
API_KEY       = os.getenv("WATCHMODE_API_KEY", "")
SLEEP_S       = 0.2

# Watchmode API name → canonical display name.
# Only services in this map will be kept.
SERVICE_NAMES = {
    "netflix":             "Netflix",
    "max":                 "Max",
    "hulu":                "Hulu",
    "peacock":             "Peacock",
    "appletv+":            "Apple TV+",
    "appletv":             "Apple TV+",
    "apple tv+":           "Apple TV+",
    "apple tv":            "Apple TV+",
    "prime video":         "Prime Video",
    "amazon prime video":  "Prime Video",
    "paramount+":          "Paramount+",
    "paramount plus":      "Paramount+",
}


def migrate(conn):
    """Add streaming_sources column if it doesn't exist yet."""
    try:
        conn.execute(text("ALTER TABLE entries ADD COLUMN streaming_sources TEXT"))
        conn.commit()
        print("Added streaming_sources column.\n")
    except Exception:
        pass  # Column already exists


def fetch_sources(client: httpx.Client, imdb_id: str) -> list[dict]:
    """Return deduplicated, normalized US subscription sources for the title."""
    url  = WATCHMODE_URL.format(imdb_id=imdb_id)
    resp = client.get(url, params={"apiKey": API_KEY}, timeout=15)
    resp.raise_for_status()

    seen     = set()
    services = []

    for src in resp.json():
        if src.get("region") != "US":
            continue
        if src.get("type") != "sub":
            continue
        canonical = SERVICE_NAMES.get(src.get("name", "").lower())
        if not canonical:
            continue
        if canonical in seen:
            continue
        seen.add(canonical)
        services.append({"service": canonical})

    return sorted(services, key=lambda s: s["service"])


def main():
    if not API_KEY:
        print("ERROR: WATCHMODE_API_KEY is not set in .env")
        sys.exit(1)

    with engine.connect() as conn:
        migrate(conn)

    db = SessionLocal()
    try:
        entries = (
            db.query(Entry)
            .filter(Entry.imdb_id.isnot(None), Entry.streaming_sources.is_(None))
            .order_by(Entry.media_type, Entry.title)
            .all()
        )
    except Exception:
        db.close()
        raise

    total    = len(entries)
    found    = 0
    empty    = 0
    errors   = 0

    print(f"Processing {total} entries\n")

    with httpx.Client() as client:
        for i, entry in enumerate(entries, 1):
            prefix = f"[{i:>3}/{total}]"
            try:
                services = fetch_sources(client, entry.imdb_id)
            except httpx.HTTPError as exc:
                print(f"{prefix} ✗  {entry.title!r}  (network error: {exc})")
                errors += 1
                time.sleep(SLEEP_S)
                continue

            if services:
                entry.streaming_sources = json.dumps(services)
                names = ", ".join(s["service"] for s in services)
                print(f"{prefix} ✓  {entry.title!r}  →  {names}")
                found += 1
            else:
                entry.streaming_sources = None
                print(f"{prefix} –  {entry.title!r}  (not on tracked services)")
                empty += 1

            db.commit()
            time.sleep(SLEEP_S)

    db.close()

    print(f"\n{'─' * 52}")
    print(f"  Streaming found: {found}")
    print(f"  Not streaming:   {empty}")
    print(f"  Errors:          {errors}")
    print(f"  Total:           {total}")


if __name__ == "__main__":
    main()
