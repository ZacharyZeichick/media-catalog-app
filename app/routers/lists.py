from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.catalog import Entry, List, ListEntry, MediaPerson
from app.schemas import (
    ListCreate, ListDetail, ListEntryAdd, ListEntryOut,
    ListSummary, ListUpdate, ReorderRequest,
)

router = APIRouter(prefix="/lists", tags=["lists"])


@router.get("", response_model=list[ListSummary])
def get_lists(db: Session = Depends(get_db)):
    lists = db.query(List).order_by(List.updated_at.desc()).all()
    results = []
    for lst in lists:
        items = (
            db.query(ListEntry)
            .filter(ListEntry.list_id == lst.id)
            .order_by(ListEntry.position)
            .all()
        )
        entry_ids = [it.entry_id for it in items[:4]]
        posters = []
        if entry_ids:
            entries = db.query(Entry).filter(Entry.id.in_(entry_ids)).all()
            by_id = {e.id: e for e in entries}
            posters = [by_id[eid].poster_path for eid in entry_ids if eid in by_id]

        results.append(ListSummary(
            id=lst.id,
            name=lst.name,
            description=lst.description,
            entry_count=len(items),
            poster_paths=posters,
            created_at=lst.created_at,
            updated_at=lst.updated_at,
        ))
    return results


@router.post("", response_model=ListSummary, status_code=201)
def create_list(body: ListCreate, db: Session = Depends(get_db)):
    lst = List(name=body.name, description=body.description)
    db.add(lst)
    db.commit()
    db.refresh(lst)
    return ListSummary(
        id=lst.id, name=lst.name, description=lst.description,
        entry_count=0, poster_paths=[],
        created_at=lst.created_at, updated_at=lst.updated_at,
    )


@router.get("/{list_id}", response_model=ListDetail)
def get_list(list_id: int, db: Session = Depends(get_db)):
    lst = db.query(List).filter(List.id == list_id).first()
    if not lst:
        raise HTTPException(404, "List not found")

    items = (
        db.query(ListEntry)
        .filter(ListEntry.list_id == list_id)
        .options(
            joinedload(ListEntry.entry)
            .joinedload(Entry.people)
            .joinedload(MediaPerson.person)
        )
        .order_by(ListEntry.position)
        .all()
    )

    return ListDetail(
        id=lst.id, name=lst.name, description=lst.description,
        created_at=lst.created_at, updated_at=lst.updated_at,
        entries=[
            ListEntryOut(
                id=it.id, position=it.position, added_at=it.added_at,
                entry=it.entry,
            )
            for it in items
        ],
    )


@router.put("/{list_id}", response_model=ListSummary)
def update_list(list_id: int, body: ListUpdate, db: Session = Depends(get_db)):
    lst = db.query(List).filter(List.id == list_id).first()
    if not lst:
        raise HTTPException(404, "List not found")
    if body.name is not None:
        lst.name = body.name
    if body.description is not None:
        lst.description = body.description
    db.commit()
    db.refresh(lst)

    count = db.query(ListEntry).filter(ListEntry.list_id == list_id).count()
    return ListSummary(
        id=lst.id, name=lst.name, description=lst.description,
        entry_count=count, poster_paths=[],
        created_at=lst.created_at, updated_at=lst.updated_at,
    )


@router.delete("/{list_id}", status_code=204)
def delete_list(list_id: int, db: Session = Depends(get_db)):
    lst = db.query(List).filter(List.id == list_id).first()
    if not lst:
        raise HTTPException(404, "List not found")
    db.delete(lst)
    db.commit()


@router.post("/{list_id}/entries", response_model=ListEntryOut, status_code=201)
def add_to_list(list_id: int, body: ListEntryAdd, db: Session = Depends(get_db)):
    lst = db.query(List).filter(List.id == list_id).first()
    if not lst:
        raise HTTPException(404, "List not found")

    existing = db.query(ListEntry).filter_by(list_id=list_id, entry_id=body.entry_id).first()
    if existing:
        raise HTTPException(409, "Entry already in list")

    entry = db.query(Entry).options(
        joinedload(Entry.people).joinedload(MediaPerson.person)
    ).filter(Entry.id == body.entry_id).first()
    if not entry:
        raise HTTPException(404, "Entry not found")

    if body.position is not None:
        pos = body.position
    else:
        max_pos = db.query(ListEntry.position).filter_by(list_id=list_id).order_by(ListEntry.position.desc()).first()
        pos = (max_pos[0] + 1) if max_pos else 0

    item = ListEntry(list_id=list_id, entry_id=body.entry_id, position=pos)
    db.add(item)
    db.commit()
    db.refresh(item)

    return ListEntryOut(id=item.id, position=item.position, added_at=item.added_at, entry=entry)


@router.delete("/{list_id}/entries/{entry_id}", status_code=204)
def remove_from_list(list_id: int, entry_id: int, db: Session = Depends(get_db)):
    item = db.query(ListEntry).filter_by(list_id=list_id, entry_id=entry_id).first()
    if not item:
        raise HTTPException(404, "Entry not in list")
    db.delete(item)
    db.commit()


@router.put("/{list_id}/entries/reorder")
def reorder_list(list_id: int, body: ReorderRequest, db: Session = Depends(get_db)):
    items = db.query(ListEntry).filter_by(list_id=list_id).all()
    by_entry = {it.entry_id: it for it in items}

    for r in body.items:
        item = by_entry.get(r.entry_id)
        if item:
            item.position = r.position

    db.commit()
    return {"ok": True}


# Also: endpoint to get which lists an entry belongs to
@router.get("/for-entry/{entry_id}")
def lists_for_entry(entry_id: int, db: Session = Depends(get_db)):
    items = db.query(ListEntry).filter_by(entry_id=entry_id).all()
    return [{"list_id": it.list_id, "position": it.position} for it in items]
