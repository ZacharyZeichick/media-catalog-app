from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.catalog import Entry, MediaPerson, WatchlistItem
from app.schemas import (
    WatchlistAdd, WatchlistItemOut, WatchlistReorder, WatchlistUpdate,
)

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


def _watchlist_query(db: Session):
    return (
        db.query(WatchlistItem)
        .options(
            joinedload(WatchlistItem.entry)
            .joinedload(Entry.people)
            .joinedload(MediaPerson.person)
        )
    )


@router.get("", response_model=list[WatchlistItemOut])
def get_watchlist(db: Session = Depends(get_db)):
    return _watchlist_query(db).order_by(WatchlistItem.priority).all()


@router.post("", response_model=WatchlistItemOut, status_code=201)
def add_to_watchlist(body: WatchlistAdd, db: Session = Depends(get_db)):
    entry = db.query(Entry).filter(Entry.id == body.entry_id).first()
    if not entry:
        raise HTTPException(404, "Entry not found")

    existing = db.query(WatchlistItem).filter_by(entry_id=body.entry_id).first()
    if existing:
        raise HTTPException(409, "Already on watchlist")

    max_pri = (
        db.query(WatchlistItem.priority)
        .order_by(WatchlistItem.priority.desc())
        .first()
    )
    priority = (max_pri[0] + 1) if max_pri else 0

    item = WatchlistItem(entry_id=body.entry_id, priority=priority, notes=body.notes)
    db.add(item)
    db.commit()
    db.refresh(item)

    return _watchlist_query(db).filter(WatchlistItem.id == item.id).first()


# reorder must be before /{entry_id} so FastAPI doesn't match "reorder" as an int
@router.put("/reorder", response_model=list[WatchlistItemOut])
def reorder_watchlist(body: WatchlistReorder, db: Session = Depends(get_db)):
    items = db.query(WatchlistItem).all()
    by_entry = {it.entry_id: it for it in items}

    for r in body.items:
        item = by_entry.get(r.entry_id)
        if item:
            item.priority = r.priority

    db.commit()
    return _watchlist_query(db).order_by(WatchlistItem.priority).all()


@router.delete("/{entry_id}", status_code=204)
def remove_from_watchlist(entry_id: int, db: Session = Depends(get_db)):
    item = db.query(WatchlistItem).filter_by(entry_id=entry_id).first()
    if not item:
        raise HTTPException(404, "Not on watchlist")
    db.delete(item)
    db.commit()


@router.put("/{entry_id}", response_model=WatchlistItemOut)
def update_watchlist_item(entry_id: int, body: WatchlistUpdate, db: Session = Depends(get_db)):
    item = db.query(WatchlistItem).filter_by(entry_id=entry_id).first()
    if not item:
        raise HTTPException(404, "Not on watchlist")
    if body.notes is not None:
        item.notes = body.notes
    db.commit()
    db.refresh(item)
    return _watchlist_query(db).filter(WatchlistItem.id == item.id).first()
