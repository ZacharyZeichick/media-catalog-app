from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.catalog import Entry, MediaType, WatchStatus
from app.schemas import (
    ConvinceRequest,
    ConvinceResponse,
    DiscoverRequest,
    DiscoverResponse,
    RecommendRequest,
    RecommendResponse,
    Recommendation,
)
from app.services import claude

router = APIRouter(prefix="/recommend", tags=["recommend"])

REWATCH_STATUSES = {WatchStatus.watched, WatchStatus.caught_up}
WATCH_NEXT_STATUSES = {WatchStatus.planned}


@router.get("/presets")
def get_presets():
    """Return available preset names per mode."""
    return claude.PRESET_KEYS


@router.post("", response_model=RecommendResponse)
def recommend(body: RecommendRequest, db: Session = Depends(get_db)):
    if not body.mood and not body.preset:
        raise HTTPException(status_code=400, detail="Provide mood or preset.")

    mood = claude.resolve_mood(body.mode, body.mood, body.preset)

    if body.mode == "rewatch":
        q = db.query(Entry).filter(Entry.status.in_(REWATCH_STATUSES))
    else:
        q = db.query(Entry).filter(Entry.status.in_(WATCH_NEXT_STATUSES))
    if body.media_filter:
        q = q.filter(Entry.media_type == MediaType(body.media_filter))
    entries = q.all()

    if len(entries) < 3:
        raise HTTPException(
            status_code=400,
            detail=f"Need at least 3 entries, but only found {len(entries)}.",
        )

    try:
        picks = claude.get_recommendations(entries, mood, body.mode)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    by_id = {e.id: e for e in entries}
    recommendations = []
    for pick in picks:
        entry = by_id.get(pick["entry_id"])
        if not entry:
            continue
        recommendations.append(
            Recommendation(
                entry_id=entry.id,
                title=entry.title,
                explanation=pick["explanation"],
                poster_url=entry.poster_url,
                genres=entry.genres,
                year=entry.year,
                rating=entry.rating,
                vibe_tags=entry.vibe_tags,
            )
        )

    return RecommendResponse(recommendations=recommendations)


@router.post("/discover", response_model=DiscoverResponse)
def discover(body: DiscoverRequest, db: Session = Depends(get_db)):
    if not body.mood and not body.preset:
        raise HTTPException(status_code=400, detail="Provide mood or preset.")

    mood = claude.resolve_mood("discover", body.mood, body.preset)
    if body.media_filter:
        mood += f" Only suggest {body.media_filter}s, not {'shows' if body.media_filter == 'movie' else 'movies'}."
    entries = db.query(Entry).all()

    if len(entries) < 3:
        raise HTTPException(
            status_code=400,
            detail="Need at least 3 catalog entries for taste analysis.",
        )

    try:
        picks = claude.get_discoveries(entries, mood)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return DiscoverResponse(recommendations=picks)


CONVINCE_STATUSES = {WatchStatus.planned, WatchStatus.on_hold, WatchStatus.get_back_to}


@router.post("/convince", response_model=ConvinceResponse)
def convince(body: ConvinceRequest, db: Session = Depends(get_db)):
    entry = db.query(Entry).filter(Entry.id == body.entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    if entry.status not in CONVINCE_STATUSES:
        raise HTTPException(status_code=400, detail="Entry must be in backlog")

    try:
        pitch = claude.get_convince_pitch(entry)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return ConvinceResponse(pitch=pitch)
