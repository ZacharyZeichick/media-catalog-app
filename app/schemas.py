from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, AliasPath

from app.models.catalog import MediaType, PersonRole, RewatchTag, WatchStatus


class PersonOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int = Field(validation_alias=AliasPath("person", "id"))
    name: str = Field(validation_alias=AliasPath("person", "name"))
    role: PersonRole


class EntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    media_type: MediaType
    year: int | None
    year_end: int | None
    imdb_id: str | None
    imdb_link: str | None
    tmdb_id: int | None
    poster_path: str | None
    backdrop_path: str | None
    hero_eligible: bool = True
    genres: str | None
    status: WatchStatus
    rating: float | None
    legacy_rating: int | None
    vibe_tags: str | None
    rewatch_tag: RewatchTag | None
    notes_what: str | None
    notes_why: str | None
    notes_recommend: str | None
    rt_tomatometer: int | None
    rt_audience: int | None
    imdb_rating: float | None
    metacritic: int | None
    poster_url: str | None
    streaming_sources: str | None
    date_watched: datetime | None
    date_added: datetime
    updated_on: datetime
    people: list[PersonOut] = []


class EntryCreate(BaseModel):
    title: str
    media_type: MediaType
    year: int | None = None
    year_end: int | None = None
    imdb_id: str | None = None
    imdb_link: str | None = None
    tmdb_id: int | None = None
    poster_path: str | None = None
    backdrop_path: str | None = None
    genres: str | None = None
    status: WatchStatus = WatchStatus.planned
    rating: float | None = None
    legacy_rating: int | None = None
    vibe_tags: str | None = None
    rewatch_tag: RewatchTag | None = None
    notes_what: str | None = None
    notes_why: str | None = None
    notes_recommend: str | None = None
    rt_tomatometer: int | None = None
    rt_audience: int | None = None
    imdb_rating: float | None = None
    metacritic: int | None = None
    poster_url: str | None = None
    date_watched: datetime | None = None


class RecommendRequest(BaseModel):
    mode: Literal["rewatch", "watch_next"]
    mood: str | None = Field(default=None, max_length=500)
    preset: str | None = None
    media_filter: Literal["movie", "show"] | None = None


class Recommendation(BaseModel):
    entry_id: int
    title: str
    explanation: str
    poster_url: str | None = None
    genres: str | None = None
    year: int | None = None
    rating: float | None = None
    vibe_tags: str | None = None


class RecommendResponse(BaseModel):
    recommendations: list[Recommendation]


class DiscoverRequest(BaseModel):
    mood: str | None = Field(default=None, max_length=500)
    preset: str | None = None
    media_filter: Literal["movie", "show"] | None = None


class DiscoverRecommendation(BaseModel):
    title: str
    year: int | None = None
    media_type: str
    explanation: str


class DiscoverResponse(BaseModel):
    recommendations: list[DiscoverRecommendation]


class EntryUpdate(BaseModel):
    title: str | None = None
    media_type: MediaType | None = None
    year: int | None = None
    year_end: int | None = None
    imdb_id: str | None = None
    imdb_link: str | None = None
    hero_eligible: bool | None = None
    genres: str | None = None
    status: WatchStatus | None = None
    rating: float | None = None
    legacy_rating: int | None = None
    vibe_tags: str | None = None
    rewatch_tag: RewatchTag | None = None
    notes_what: str | None = None
    notes_why: str | None = None
    notes_recommend: str | None = None
    rt_tomatometer: int | None = None
    rt_audience: int | None = None
    imdb_rating: float | None = None
    metacritic: int | None = None
    poster_url: str | None = None
    date_watched: datetime | None = None


# ── Lists ──────────────────────────────────────────────────────────────

class ListCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None

class ListUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    description: str | None = None

class ListSummary(BaseModel):
    id: int
    name: str
    description: str | None
    entry_count: int = 0
    poster_paths: list[str | None] = []
    created_at: datetime
    updated_at: datetime

class ListEntryAdd(BaseModel):
    entry_id: int
    position: int | None = None

class ListEntryOut(BaseModel):
    id: int
    position: int
    added_at: datetime
    entry: EntryOut

class ListDetail(BaseModel):
    id: int
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime
    entries: list[ListEntryOut] = []

class ReorderItem(BaseModel):
    entry_id: int
    position: int

class ReorderRequest(BaseModel):
    items: list[ReorderItem]


# ── Watchlist ─────────────────────────────────────────────────────────

class ConvinceRequest(BaseModel):
    entry_id: int

class ConvinceResponse(BaseModel):
    pitch: str


class WatchlistAdd(BaseModel):
    entry_id: int
    notes: str | None = None

class WatchlistItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    entry_id: int
    priority: int
    notes: str | None
    date_added: datetime
    entry: EntryOut

class WatchlistUpdate(BaseModel):
    notes: str | None = None

class WatchlistReorderItem(BaseModel):
    entry_id: int
    priority: int

class WatchlistReorder(BaseModel):
    items: list[WatchlistReorderItem]
