from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.catalog import Entry, MediaPerson, MediaType, WatchStatus
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


@router.get("", response_model=list[EntryOut])
def list_media(
    media_type: MediaType | None = Query(default=None, alias="type"),
    status: WatchStatus | None = None,
    genre: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Entry).options(
        joinedload(Entry.people).joinedload(MediaPerson.person)
    )
    if media_type is not None:
        query = query.filter(Entry.media_type == media_type)
    if status is not None:
        query = query.filter(Entry.status == status)
    if genre is not None:
        query = query.filter(Entry.genres.ilike(f"%{genre}%"))
    return query.order_by(Entry.title).all()


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
