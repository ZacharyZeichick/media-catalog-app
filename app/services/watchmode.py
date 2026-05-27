"""Watchmode API enrichment — fetch US subscription streaming sources."""

import json
import os

import httpx

from app.models.catalog import Entry

WATCHMODE_URL = "https://api.watchmode.com/v1/title/{imdb_id}/sources/"

# Maps Watchmode source name (lowercase) → canonical display name.
# Only services present in this map are kept.
SERVICE_NAMES: dict[str, str] = {
    "netflix":             "Netflix",
    "max":                 "Max",
    "hulu":                "Hulu",
    "peacock":             "Peacock",
    "appletv+":            "Apple TV+",
    "appletv":             "Apple TV+",
    "apple tv+":           "Apple TV+",
    "apple tv":            "Apple TV+",
    "apple tv plus":       "Apple TV+",
    "prime video":         "Prime Video",
    "amazon prime video":  "Prime Video",
    "paramount+":          "Paramount+",
    "paramount plus":      "Paramount+",
    "disney+":             "Disney+",
    "disney plus":         "Disney+",
}


def enrich_streaming(entry: Entry) -> None:
    """
    Fetch Watchmode US subscription sources and update entry.streaming_sources in-place.
    Caller must db.commit() afterwards.
    """
    key = os.getenv("WATCHMODE_API_KEY", "")
    if not key or not entry.imdb_id:
        return

    url = WATCHMODE_URL.format(imdb_id=entry.imdb_id)
    with httpx.Client() as client:
        resp = client.get(url, params={"apiKey": key}, timeout=15)
        resp.raise_for_status()

    seen:     set[str]       = set()
    services: list[dict]     = []

    for src in resp.json():
        if src.get("region") != "US" or src.get("type") != "sub":
            continue
        canonical = SERVICE_NAMES.get(src.get("name", "").lower())
        if not canonical or canonical in seen:
            continue
        seen.add(canonical)
        services.append({"service": canonical})

    services.sort(key=lambda s: s["service"])
    entry.streaming_sources = json.dumps(services) if services else None
