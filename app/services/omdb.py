"""OMDb API — search + enrichment."""

import os

import httpx
from sqlalchemy.orm import Session

from app.models.catalog import Entry, MediaPerson, MediaType, Person, PersonRole

OMDB_URL = "http://www.omdbapi.com/"


def _api_key() -> str:
    return os.getenv("OMDB_API_KEY", "")


def search_omdb(query: str) -> list[dict]:
    """Search OMDb by title string.  Returns a list of compact result dicts."""
    key = _api_key()
    if not key or not query.strip():
        return []

    with httpx.Client() as client:
        resp = client.get(OMDB_URL, params={"s": query, "apikey": key}, timeout=10)
        resp.raise_for_status()

    data = resp.json()
    if data.get("Response") != "True":
        return []

    results = []
    for item in data.get("Search", []):
        omdb_type = item.get("Type", "")
        if omdb_type not in ("movie", "series"):
            continue
        poster = item.get("Poster", "")
        results.append({
            "imdb_id":    item.get("imdbID"),
            "title":      item.get("Title"),
            "year":       item.get("Year"),
            "media_type": "show" if omdb_type == "series" else "movie",
            "poster_url": poster if poster and poster != "N/A" else None,
        })
    return results


def _get_or_create_person(db: Session, name: str) -> Person:
    name = name.strip()
    person = db.query(Person).filter_by(name=name).first()
    if not person:
        person = Person(name=name)
        db.add(person)
        db.flush()
    return person


def enrich_from_omdb(db: Session, entry: Entry) -> bool:
    """
    Look up entry by title on OMDb and update fields in-place.
    Caller must db.commit() afterwards.
    Returns True if OMDb found the title, False otherwise.
    """
    key = _api_key()
    if not key:
        return False

    # Prefer lookup by IMDb ID (exact); fall back to title search
    if entry.imdb_id:
        params: dict = {"i": entry.imdb_id, "apikey": key}
    else:
        omdb_type = "movie" if entry.media_type == MediaType.movie else "series"
        params: dict = {"t": entry.title, "type": omdb_type, "apikey": key}
        if entry.year:
            params["y"] = entry.year

    with httpx.Client() as client:
        resp = client.get(OMDB_URL, params=params, timeout=10)
        resp.raise_for_status()

    data = resp.json()
    if data.get("Response") != "True":
        return False

    # Identity — use OMDb's canonical title
    entry.title   = data.get("Title")  or entry.title
    entry.imdb_id = data.get("imdbID") or entry.imdb_id
    entry.genres  = data.get("Genre")  or entry.genres
    if entry.imdb_id:
        entry.imdb_link = f"https://www.imdb.com/title/{entry.imdb_id}/"

    # Year — only update movies; shows use the imported year range
    if entry.media_type == MediaType.movie:
        y = data.get("Year", "")
        if y and y.isdigit():
            entry.year = int(y)

    # Plot → notes_what (only if not already set)
    plot = data.get("Plot", "")
    if plot and plot != "N/A" and not entry.notes_what:
        entry.notes_what = plot

    # Poster — request higher resolution than OMDb's default SX300
    poster = data.get("Poster", "")
    if poster and poster != "N/A":
        entry.poster_url = poster.replace("SX300", "SX600")

    # IMDb rating
    imdb_str = data.get("imdbRating", "")
    if imdb_str and imdb_str != "N/A":
        try:
            entry.imdb_rating = float(imdb_str)
        except ValueError:
            pass

    # RT and Metacritic from Ratings array
    for r in data.get("Ratings", []):
        src, val = r.get("Source", ""), r.get("Value", "")
        if src == "Rotten Tomatoes":
            v = val.rstrip("%")
            if v.isdigit():
                entry.rt_tomatometer = int(v)
        elif src == "Metacritic":
            v = val.split("/")[0]
            if v.isdigit():
                entry.metacritic = int(v)

    # People — clear existing records then recreate
    db.query(MediaPerson).filter(MediaPerson.entry_id == entry.id).delete()

    for raw, role in [
        (data.get("Director", ""), PersonRole.director),
        (data.get("Writer",   ""), PersonRole.writer),
    ]:
        if not raw or raw == "N/A":
            continue
        for name in raw.split(","):
            # OMDb writer strings include credits like "(screenplay by)" — strip them
            name = name.split("(")[0].strip()
            if not name:
                continue
            person = _get_or_create_person(db, name)
            db.add(MediaPerson(entry=entry, person=person, role=role))

    return True
