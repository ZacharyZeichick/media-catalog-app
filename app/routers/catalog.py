from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import asc, desc, nulls_last
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.catalog import Entry, MediaPerson, MediaType, WatchStatus, WatchlistItem
from app.schemas import EntryCreate, EntryOut, EntryUpdate
from app.services import mdblist, omdb, tmdb, watchmode

router = APIRouter(prefix="/media", tags=["media"])


@router.get("/omdb-search")
def omdb_search(q: str = Query(min_length=2)):
    return omdb.search_omdb(q)


@router.get("/tmdb-search")
def tmdb_search(q: str = Query(min_length=2), type: str = Query(default="movie")):
    return tmdb.search(q, media_type=type)


@router.post("/tmdb-backfill")
def tmdb_backfill(db: Session = Depends(get_db)):
    return tmdb.backfill(db)


# Search must be registered before /{id} so FastAPI doesn't treat "search" as an id
@router.get("/search", response_model=list[EntryOut])
def search_media(q: str = Query(min_length=1), db: Session = Depends(get_db)):
    return (
        db.query(Entry)
        .options(joinedload(Entry.people).joinedload(MediaPerson.person))
        .filter(Entry.title.ilike(f"%{q}%"))
        .order_by(Entry.title)
        .all()
    )


_SORT_COLS = {
    "title": Entry.title,
    "rating": Entry.rating,
    "year": Entry.year,
    "date_added": Entry.date_added,
}


@router.get("", response_model=list[EntryOut])
def list_media(
    q: str | None = Query(default=None, description="Title search"),
    media_type: MediaType | None = Query(default=None, alias="type"),
    status: WatchStatus | None = None,
    genre: str | None = None,
    vibe_tag: str | None = None,
    min_rating: float | None = Query(default=None, ge=1, le=10),
    year: int | None = None,
    sort_by: Literal["title", "rating", "year", "date_added", "watchlist_priority"] = Query(default="title"),
    sort_dir: Literal["asc", "desc"] = Query(default="asc"),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(Entry).options(
        joinedload(Entry.people).joinedload(MediaPerson.person)
    )

    if q:
        query = query.filter(Entry.title.ilike(f"%{q}%"))
    if media_type is not None:
        query = query.filter(Entry.media_type == media_type)
    if status is not None:
        query = query.filter(Entry.status == status)
    if genre is not None:
        query = query.filter(Entry.genres.ilike(f"%{genre}%"))
    if vibe_tag is not None:
        query = query.filter(Entry.vibe_tags.ilike(f"%{vibe_tag}%"))
    if min_rating is not None:
        query = query.filter(Entry.rating >= min_rating)
    if year is not None:
        query = query.filter(Entry.year == year)

    sort_fn = asc if sort_dir == "asc" else desc
    if sort_by == "watchlist_priority":
        query = query.outerjoin(Entry.watchlist_item)
        query = query.order_by(nulls_last(sort_fn(WatchlistItem.priority)))
    else:
        query = query.order_by(sort_fn(_SORT_COLS[sort_by]))

    return query.offset(offset).limit(limit).all()


@router.get("/{entry_id}", response_model=EntryOut)
def get_media(entry_id: int, db: Session = Depends(get_db)):
    entry = (
        db.query(Entry)
        .options(joinedload(Entry.people).joinedload(MediaPerson.person))
        .filter(Entry.id == entry_id)
        .first()
    )
    if entry is None:
        raise HTTPException(status_code=404, detail="Not found")
    return entry


@router.post("", response_model=EntryOut, status_code=201)
def create_media(body: EntryCreate, db: Session = Depends(get_db)):
    entry = Entry(**body.model_dump())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    # Re-fetch with people loaded (empty for new entries, but keeps response shape consistent)
    return (
        db.query(Entry)
        .options(joinedload(Entry.people).joinedload(MediaPerson.person))
        .filter(Entry.id == entry.id)
        .first()
    )


@router.put("/{entry_id}", response_model=EntryOut)
def update_media(entry_id: int, body: EntryUpdate, db: Session = Depends(get_db)):
    entry = db.query(Entry).filter(Entry.id == entry_id).first()
    if entry is None:
        raise HTTPException(status_code=404, detail="Not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(entry, field, value)
    db.commit()
    db.refresh(entry)
    return (
        db.query(Entry)
        .options(joinedload(Entry.people).joinedload(MediaPerson.person))
        .filter(Entry.id == entry.id)
        .first()
    )


@router.post("/{entry_id}/enrich", response_model=EntryOut)
def enrich_media(entry_id: int, db: Session = Depends(get_db)):
    entry = db.query(Entry).filter(Entry.id == entry_id).first()
    if entry is None:
        raise HTTPException(status_code=404, detail="Not found")
    omdb.enrich_from_omdb(db, entry)
    # Fill any rating gaps from MDBList
    if entry.imdb_rating is None or entry.rt_tomatometer is None or entry.metacritic is None:
        mdblist.enrich_ratings(entry)
    watchmode.enrich_streaming(entry)
    db.commit()
    return (
        db.query(Entry)
        .options(joinedload(Entry.people).joinedload(MediaPerson.person))
        .filter(Entry.id == entry_id)
        .first()
    )


@router.get("/{entry_id}/trailer")
def get_trailer(entry_id: int, db: Session = Depends(get_db)):
    entry = db.query(Entry).filter(Entry.id == entry_id).first()
    if entry is None:
        raise HTTPException(status_code=404, detail="Not found")
    url = tmdb.get_trailer(entry.tmdb_id, entry.media_type.value)
    if not url:
        raise HTTPException(status_code=404, detail="No trailer found")
    return {"url": url}


@router.delete("/{entry_id}", status_code=204)
def delete_media(entry_id: int, db: Session = Depends(get_db)):
    entry = db.query(Entry).filter(Entry.id == entry_id).first()
    if entry is None:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(entry)
    db.commit()
