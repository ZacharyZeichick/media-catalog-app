"""
Backfill poster_url for entries that have imdb_id but no poster_url.

Usage (from project root):
    python scripts/backfill_posters.py

Safe to re-run — only touches rows where poster_url IS NULL and imdb_id IS NOT NULL.
"""

import io
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

from app.database import SessionLocal
from app.models.catalog import Entry

OMDB_URL = "http://www.omdbapi.com/"
API_KEY  = os.getenv("OMDB_API_KEY", "")
SLEEP_S  = 0.1


def fetch_poster(client: httpx.Client, imdb_id: str) -> str | None:
    resp = client.get(OMDB_URL, params={"i": imdb_id, "apikey": API_KEY}, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if data.get("Response") == "True":
        poster = data.get("Poster", "")
        if poster and poster != "N/A":
            return poster
    return None


def main():
    if not API_KEY:
        print("ERROR: OMDB_API_KEY is not set in .env")
        sys.exit(1)

    db = SessionLocal()
    try:
        entries = (
            db.query(Entry)
            .filter(Entry.poster_url.is_(None), Entry.imdb_id.isnot(None))
            .order_by(Entry.media_type, Entry.title)
            .all()
        )
    except Exception:
        db.close()
        raise

    total    = len(entries)
    filled   = 0
    no_poster = 0

    print(f"Found {total} entries to check\n")

    with httpx.Client() as client:
        for i, entry in enumerate(entries, 1):
            prefix = f"[{i:>3}/{total}]"
            try:
                poster_url = fetch_poster(client, entry.imdb_id)
            except httpx.HTTPError as exc:
                print(f"{prefix} ✗  {entry.title!r}  (network error: {exc})")
                no_poster += 1
                time.sleep(SLEEP_S)
                continue

            if poster_url:
                entry.poster_url = poster_url
                db.commit()
                filled += 1
                print(f"{prefix} ✓  {entry.title!r}")
            else:
                no_poster += 1
                print(f"{prefix} –  {entry.title!r}  (no poster available)")

            time.sleep(SLEEP_S)

    db.close()

    print(f"\n{'─' * 48}")
    print(f"  Posters saved:   {filled}")
    print(f"  No poster found: {no_poster}")
    print(f"  Total checked:   {total}")


if __name__ == "__main__":
    main()
