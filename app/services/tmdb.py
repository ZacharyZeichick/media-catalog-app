"""TMDB API — search and metadata for posters/backdrops."""

import os
import logging

import httpx
from sqlalchemy.orm import Session

from app.models.catalog import Entry, MediaType

log = logging.getLogger(__name__)

TMDB_BASE = "https://api.themoviedb.org/3"
IMG_BASE = "https://image.tmdb.org/t/p"


def _api_key() -> str:
    return os.getenv("TMDB_API_KEY", "")


def search(query: str, media_type: str = "movie") -> list[dict]:
    """Search TMDB for movies or TV shows. Returns compact results."""
    key = _api_key()
    if not key or not query.strip():
        return []

    tmdb_type = "tv" if media_type == "show" else "movie"
    with httpx.Client() as client:
        resp = client.get(
            f"{TMDB_BASE}/search/{tmdb_type}",
            params={"api_key": key, "query": query, "language": "en-US", "page": 1},
            timeout=10,
        )
        resp.raise_for_status()

    data = resp.json()
    results = []
    for item in data.get("results", [])[:10]:
        title = item.get("title") or item.get("name", "")
        year_str = (item.get("release_date") or item.get("first_air_date") or "")[:4]
        results.append({
            "tmdb_id": item.get("id"),
            "title": title,
            "year": year_str,
            "media_type": media_type,
            "poster_path": item.get("poster_path"),
            "backdrop_path": item.get("backdrop_path"),
            "poster_url": f"{IMG_BASE}/w400{item['poster_path']}" if item.get("poster_path") else None,
        })
    return results


def backfill(db: Session) -> dict:
    """Find TMDB IDs for all entries missing one. Returns match/miss counts."""
    key = _api_key()
    if not key:
        return {"error": "TMDB_API_KEY not set"}

    entries = db.query(Entry).filter(Entry.tmdb_id == None).all()
    matched = 0
    missed = 0

    with httpx.Client() as client:
        for entry in entries:
            tmdb_type = "tv" if entry.media_type == MediaType.show else "movie"
            params = {"api_key": key, "query": entry.title, "language": "en-US", "page": 1}
            if entry.year:
                if tmdb_type == "movie":
                    params["year"] = entry.year
                else:
                    params["first_air_date_year"] = entry.year

            try:
                resp = client.get(
                    f"{TMDB_BASE}/search/{tmdb_type}",
                    params=params,
                    timeout=10,
                )
                resp.raise_for_status()
                results = resp.json().get("results", [])

                if results:
                    top = results[0]
                    entry.tmdb_id = top.get("id")
                    entry.poster_path = top.get("poster_path")
                    entry.backdrop_path = top.get("backdrop_path")
                    matched += 1
                    log.info(f"TMDB match: {entry.title} -> {entry.tmdb_id}")
                else:
                    missed += 1
                    log.warning(f"TMDB miss: {entry.title}")
            except Exception as exc:
                missed += 1
                log.error(f"TMDB error for {entry.title}: {exc}")

    db.commit()
    return {"matched": matched, "missed": missed, "total": len(entries)}


def get_trailer(tmdb_id: int, media_type: str) -> str | None:
    """Get YouTube trailer URL from TMDB. Returns URL or None."""
    key = _api_key()
    if not key or not tmdb_id:
        return None

    tmdb_type = "tv" if media_type == "show" else "movie"
    with httpx.Client() as client:
        resp = client.get(
            f"{TMDB_BASE}/{tmdb_type}/{tmdb_id}/videos",
            params={"api_key": key, "language": "en-US"},
            timeout=10,
        )
        if resp.status_code != 200:
            return None

    videos = resp.json().get("results", [])
    # Prefer official trailers, then any trailer, then any YouTube video
    trailers = [v for v in videos if v.get("site") == "YouTube" and v.get("type") == "Trailer"]
    official = [v for v in trailers if v.get("official")]
    pick = (official or trailers or [v for v in videos if v.get("site") == "YouTube"])
    if not pick:
        return None
    return f"https://www.youtube.com/watch?v={pick[0]['key']}"
