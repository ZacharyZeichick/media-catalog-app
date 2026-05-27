"""
Import movie and show catalog data from Google Sheets CSV exports.

Usage (from project root):
    python scripts/import_csv.py

Expects these files in the project root:
    "Show and Movie Catalog - Movies.csv"
    "Show and Movie Catalog - Shows.csv"
"""

import csv
import os
import re
import sys
from pathlib import Path

# Make sure the project root is on sys.path so `app` is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from app.database import Base, engine, SessionLocal
from app.models.catalog import (
    Entry, MediaType, Person, MediaPerson, PersonRole, WatchStatus,
)

MOVIES_CSV = PROJECT_ROOT / "Show and Movie Catalog - Movies.csv"
SHOWS_CSV  = PROJECT_ROOT / "Show and Movie Catalog - Shows.csv"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_rt(val: str) -> int | None:
    """'97%' → 97, '' → None."""
    val = val.strip().rstrip("%")
    return int(val) if val else None


def parse_imdb_rating(val: str) -> float | None:
    val = val.strip()
    return float(val) if val else None


def parse_metacritic(val: str) -> int | None:
    val = val.strip()
    return int(val) if val else None


def parse_legacy_rating(val: str) -> int | None:
    val = val.strip()
    return int(val) if val else None


def extract_imdb_id(url: str) -> str | None:
    """'https://www.imdb.com/title/tt0120780/' → 'tt0120780'"""
    if not url:
        return None
    match = re.search(r"(tt\d+)", url)
    return match.group(1) if match else None


def parse_movie_year(val: str) -> int | None:
    val = val.strip()
    return int(val) if val else None


def parse_show_years(val: str) -> tuple[int | None, int | None]:
    """
    '1999–2007' → (1999, 2007)
    '2023–'     → (2023, None)   ongoing
    '2020'      → (2020, None)
    ''          → (None, None)
    """
    val = val.strip()
    if not val:
        return None, None
    # Handle en-dash (–) and regular hyphen (-)
    match = re.match(r"(\d{4})\s*[–-]\s*(\d{4})?", val)
    if match:
        start = int(match.group(1))
        end = int(match.group(2)) if match.group(2) else None
        return start, end
    if val.isdigit():
        return int(val), None
    return None, None


_STATUS_MAP = {
    "watched":      WatchStatus.watched,
    "planned":      WatchStatus.planned,
    "watching":     WatchStatus.watching,
    "caught up":    WatchStatus.caught_up,
    "on hold":      WatchStatus.on_hold,
    "get back to":  WatchStatus.get_back_to,
    "dropped":      WatchStatus.dropped,
}

def normalize_status(val: str) -> WatchStatus:
    return _STATUS_MAP.get(val.strip().lower(), WatchStatus.planned)


def get_or_create_person(session, name: str) -> Person:
    name = name.strip()
    person = session.query(Person).filter_by(name=name).first()
    if not person:
        person = Person(name=name)
        session.add(person)
        session.flush()  # get person.id without full commit
    return person


def attach_people(session, entry: Entry, names_str: str, role: PersonRole):
    """Split a comma-separated names string and link each to the entry."""
    if not names_str or not names_str.strip():
        return
    for raw_name in names_str.split(","):
        name = raw_name.strip()
        if not name:
            continue
        person = get_or_create_person(session, name)
        link = MediaPerson(entry=entry, person=person, role=role)
        session.add(link)


# ---------------------------------------------------------------------------
# Importers
# ---------------------------------------------------------------------------

def import_movies(session) -> int:
    count = 0
    with open(MOVIES_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            title = row.get("Title", "").strip()
            if not title:
                continue

            imdb_link = row.get("IMDb Link", "").strip() or None
            imdb_id   = extract_imdb_id(imdb_link) if imdb_link else None

            entry = Entry(
                media_type    = MediaType.movie,
                title         = title,
                year          = parse_movie_year(row.get("Year", "")),
                year_end      = None,
                imdb_id       = imdb_id,
                imdb_link     = imdb_link,
                genres        = row.get("Genre(s)", "").strip() or None,
                status        = normalize_status(row.get("Status", "")),
                rt_tomatometer = parse_rt(row.get("RT Tomatometer", "")),
                rt_audience   = parse_rt(row.get("RT Audience", "")),
                imdb_rating   = parse_imdb_rating(row.get("IMDb Rating", "")),
                metacritic    = parse_metacritic(row.get("Metacritic", "")),
                legacy_rating = parse_legacy_rating(row.get("My Rating", "")),
                notes_why     = row.get("Notes", "").strip() or None,
            )
            session.add(entry)
            session.flush()

            attach_people(session, entry, row.get("Director", ""), PersonRole.director)
            attach_people(session, entry, row.get("Writer", ""),   PersonRole.writer)

            count += 1

    return count


def import_shows(session) -> int:
    count = 0
    with open(SHOWS_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            title = row.get("Title", "").strip()
            if not title:
                continue

            imdb_link = row.get("IMDb Link", "").strip() or None
            imdb_id   = extract_imdb_id(imdb_link) if imdb_link else None
            year, year_end = parse_show_years(row.get("Year(s)", ""))

            entry = Entry(
                media_type    = MediaType.show,
                title         = title,
                year          = year,
                year_end      = year_end,
                imdb_id       = imdb_id,
                imdb_link     = imdb_link,
                genres        = row.get("Genre(s)", "").strip() or None,
                status        = normalize_status(row.get("Status", "")),
                rt_tomatometer = parse_rt(row.get("RT Tomatometer", "")),
                rt_audience   = parse_rt(row.get("RT Audience", "")),
                imdb_rating   = parse_imdb_rating(row.get("IMDb Rating", "")),
                metacritic    = parse_metacritic(row.get("Metacritic", "")),
                legacy_rating = parse_legacy_rating(row.get("My Rating ", "")),
                notes_why     = row.get("Notes", "").strip() or None,
            )
            session.add(entry)
            count += 1

    return count


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    for path in (MOVIES_CSV, SHOWS_CSV):
        if not path.exists():
            print(f"ERROR: CSV not found: {path}")
            sys.exit(1)

    print("Creating tables...")
    Base.metadata.create_all(bind=engine)

    session = SessionLocal()
    try:
        existing = session.query(Entry).count()
        if existing > 0:
            print(f"WARNING: {existing} entries already exist. Aborting to avoid duplicates.")
            print("Delete catalog.db first if you want to re-import.")
            sys.exit(1)

        print("Importing movies...")
        movie_count = import_movies(session)

        print("Importing shows...")
        show_count = import_shows(session)

        session.commit()

        people_count = session.query(Person).count()
        links_count  = session.query(MediaPerson).count()

        print(f"\nDone.")
        print(f"  {movie_count} movies imported")
        print(f"  {show_count} shows imported")
        print(f"  {people_count} people created")
        print(f"  {links_count} director/writer links created")

    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
