"""
Backfill imdb_id for entries that are missing it, using the OMDb API.

Usage (from project root):
    python scripts/backfill_imdb.py

Safe to re-run — only touches rows where imdb_id IS NULL.
"""

import io
import os
import sys
import time

# Ensure UTF-8 output on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

import httpx

from app.database import SessionLocal
from app.models.catalog import Entry, MediaType

OMDB_URL = "http://www.omdbapi.com/"
API_KEY  = os.getenv("OMDB_API_KEY", "")
SLEEP_S  = 0.1


def lookup(client: httpx.Client, title: str, year: int | None, media_type: MediaType) -> str | None:
    omdb_type = "movie" if media_type == MediaType.movie else "series"
    params = {"t": title, "type": omdb_type, "apikey": API_KEY}
    if year:
        params["y"] = year

    resp = client.get(OMDB_URL, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    if data.get("Response") == "True":
        return data.get("imdbID")
    return None


def main():
    if not API_KEY:
        print("ERROR: OMDB_API_KEY is not set in .env")
        sys.exit(1)

    db = SessionLocal()
    try:
        entries = (
            db.query(Entry)
            .filter(Entry.imdb_id.is_(None))
            .order_by(Entry.media_type, Entry.title)
            .all()
        )
    except Exception:
        db.close()
        raise

    total   = len(entries)
    filled  = 0
    missing = 0

    print(f"Found {total} entries without imdb_id\n")

    with httpx.Client() as client:
        for i, entry in enumerate(entries, 1):
            prefix = f"[{i:>3}/{total}]"
            try:
                imdb_id = lookup(client, entry.title, entry.year, entry.media_type)
            except httpx.HTTPError as exc:
                print(f"{prefix} ✗  {entry.title!r}  (network error: {exc})")
                missing += 1
                time.sleep(SLEEP_S)
                continue

            if imdb_id:
                entry.imdb_id = imdb_id
                db.commit()
                filled += 1
                print(f"{prefix} ✓  {entry.title!r}  →  {imdb_id}")
            else:
                missing += 1
                print(f"{prefix} ✗  {entry.title!r}  (not found)")

            time.sleep(SLEEP_S)

    db.close()

    print(f"\n{'─' * 48}")
    print(f"  Filled:       {filled}")
    print(f"  Still missing:{missing}")
    print(f"  Total:        {total}")


if __name__ == "__main__":
    main()
