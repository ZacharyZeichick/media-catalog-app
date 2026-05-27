"""MDBList API — fallback ratings source when OMDb has gaps."""

import os

import httpx

from app.models.catalog import Entry, MediaType

MDBLIST_URL = "https://api.mdblist.com/imdb/{media_type}/{imdb_id}"


def _api_key() -> str:
    return os.getenv("MDBLIST_API_KEY", "")


def enrich_ratings(entry: Entry) -> bool:
    """
    Fetch ratings from MDBList and fill any blanks on the entry.
    Only overwrites fields that are currently None.
    Caller must db.commit() afterwards.
    Returns True if the API returned data, False otherwise.
    """
    key = _api_key()
    if not key or not entry.imdb_id:
        return False

    media_type = "show" if entry.media_type == MediaType.show else "movie"
    url = MDBLIST_URL.format(media_type=media_type, imdb_id=entry.imdb_id)

    with httpx.Client() as client:
        resp = client.get(url, params={"apikey": key}, timeout=10)
        if resp.status_code != 200:
            return False

    data = resp.json()
    if not data or "ratings" not in data:
        return False

    # Build a lookup: source -> rating object
    by_source = {r["source"]: r for r in data.get("ratings", [])}

    # IMDb rating (native scale, e.g. 8.1)
    if entry.imdb_rating is None:
        imdb = by_source.get("imdb", {})
        if imdb.get("value") is not None:
            entry.imdb_rating = float(imdb["value"])

    # RT Tomatometer (0-100 score)
    if entry.rt_tomatometer is None:
        rt = by_source.get("tomatoes", {})
        if rt.get("score") is not None:
            entry.rt_tomatometer = int(rt["score"])

    # Metacritic (0-100 score)
    if entry.metacritic is None:
        mc = by_source.get("metacritic", {})
        if mc.get("score") is not None:
            entry.metacritic = int(mc["score"])

    return True
