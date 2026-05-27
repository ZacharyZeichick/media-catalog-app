import enum
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Text, DateTime,
    Enum as SAEnum, ForeignKey, CheckConstraint, UniqueConstraint,
)
from sqlalchemy.orm import relationship
from app.database import Base


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class MediaType(str, enum.Enum):
    movie = "movie"
    show = "show"


class VibeTag(str, enum.Enum):
    funny = "Funny"
    dark = "Dark"
    intense = "Intense"
    heartfelt = "Heartfelt"
    cozy = "Cozy"
    creepy = "Creepy"
    hype = "Hype"
    easy_watch = "Easy Watch"
    mind_bending = "Mind-Bending"
    emotional_ride = "Emotional Ride"
    slow_burn = "Slow Burn"
    bingeable = "Bingeable"


class RewatchTag(str, enum.Enum):
    never = "Never"
    rarely = "Rarely"
    sometimes = "Sometimes"
    anytime = "Anytime"


class WatchStatus(str, enum.Enum):
    planned = "Planned"
    watching = "Watching"       # currently in progress
    caught_up = "Caught Up"     # up to date on an ongoing show
    watched = "Watched"
    on_hold = "On Hold"
    get_back_to = "Get Back To"
    dropped = "Dropped"


class PersonRole(str, enum.Enum):
    director = "director"
    writer = "writer"


# ---------------------------------------------------------------------------
# Entry — one row per movie or show
# ---------------------------------------------------------------------------

class Entry(Base):
    __tablename__ = "entries"
    __table_args__ = (
        CheckConstraint(
            "rating IS NULL OR (rating >= 1 AND rating <= 10)",
            name="ck_rating",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    # --- Identity ---
    title = Column(String(255), nullable=False, index=True)
    media_type = Column(SAEnum(MediaType), nullable=False)
    year = Column(Integer)
    year_end = Column(Integer)                  # shows only; None = ongoing or movie
    imdb_id = Column(String(20), unique=True, index=True, nullable=True)
    imdb_link = Column(String(512), nullable=True)

    # --- TMDB ---
    tmdb_id = Column(Integer, nullable=True, index=True)
    poster_path = Column(Text, nullable=True)       # e.g. /abc123.jpg
    backdrop_path = Column(Text, nullable=True)      # e.g. /xyz789.jpg
    hero_eligible = Column(Integer, nullable=False, default=1)  # 1=yes, 0=no

    # --- External metadata ---
    poster_url = Column(String(512))                 # legacy OMDb poster, fallback
    genres = Column(String(255))                # comma-separated e.g. "Drama, Thriller"
    rt_tomatometer = Column(Integer)            # 0–100, stripped of %
    rt_audience = Column(Integer)               # 0–100, stripped of %
    imdb_rating = Column(Float)                 # e.g. 8.3
    metacritic = Column(Integer)                # 0–100
    streaming_sources = Column(Text)            # JSON: [{"service": "Netflix"}, ...]

    # --- User scores (nullable until rated) ---
    rating = Column(Float)                      # 1–10, how much I liked it
    legacy_rating = Column(Integer)             # old single 0–100 score from Google Sheet
    vibe_tags = Column(String(255))             # comma-separated, e.g. "Funny, Dark, Easy Watch"
    rewatch_tag = Column(SAEnum(RewatchTag))

    # --- User notes ---
    notes_what = Column(Text)                   # what it's about (1–2 sentences)
    notes_why = Column(Text)                    # why I scored it that way
    notes_recommend = Column(Text)              # who I'd recommend it to

    # --- Workflow ---
    status = Column(SAEnum(WatchStatus), nullable=False, default=WatchStatus.planned)
    date_watched = Column(DateTime)
    date_added = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_on = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # --- Relationships ---
    people = relationship("MediaPerson", back_populates="entry", cascade="all, delete-orphan")
    watchlist_item = relationship("WatchlistItem", back_populates="entry", uselist=False, cascade="all, delete-orphan")

    def is_scored(self) -> bool:
        return self.rating is not None


# ---------------------------------------------------------------------------
# Person + MediaPerson — directors and writers
# ---------------------------------------------------------------------------

class Person(Base):
    __tablename__ = "people"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True, index=True)

    roles = relationship("MediaPerson", back_populates="person")


class MediaPerson(Base):
    __tablename__ = "media_people"
    __table_args__ = (
        UniqueConstraint("entry_id", "person_id", "role", name="uq_entry_person_role"),
    )

    id = Column(Integer, primary_key=True, index=True)
    entry_id = Column(Integer, ForeignKey("entries.id"), nullable=False)
    person_id = Column(Integer, ForeignKey("people.id"), nullable=False)
    role = Column(SAEnum(PersonRole), nullable=False)

    entry = relationship("Entry", back_populates="people")
    person = relationship("Person", back_populates="roles")


# ---------------------------------------------------------------------------
# WatchlistItem — priority queue on top of Entry
# ---------------------------------------------------------------------------

class WatchlistItem(Base):
    __tablename__ = "watchlist"

    id = Column(Integer, primary_key=True, index=True)
    entry_id = Column(Integer, ForeignKey("entries.id"), unique=True, nullable=False)
    priority = Column(Integer, default=0)
    notes = Column(Text)
    date_added = Column(DateTime, default=datetime.utcnow, nullable=False)

    entry = relationship("Entry", back_populates="watchlist_item")


# ---------------------------------------------------------------------------
# Custom Lists
# ---------------------------------------------------------------------------

class List(Base):
    __tablename__ = "lists"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    items = relationship("ListEntry", back_populates="list", cascade="all, delete-orphan", order_by="ListEntry.position")


class ListEntry(Base):
    __tablename__ = "list_entries"
    __table_args__ = (
        UniqueConstraint("list_id", "entry_id", name="uq_list_entry"),
    )

    id = Column(Integer, primary_key=True, index=True)
    list_id = Column(Integer, ForeignKey("lists.id"), nullable=False)
    entry_id = Column(Integer, ForeignKey("entries.id"), nullable=False)
    position = Column(Integer, default=0)
    added_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    list = relationship("List", back_populates="items")
    entry = relationship("Entry")
