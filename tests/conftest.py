import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.models.catalog import Entry, MediaType, WatchStatus

TEST_ENTRIES = [
    dict(title="The Dark Knight",          media_type=MediaType.movie, year=2008, status=WatchStatus.watched,   rating=9.5, genres="Action, Drama"),
    dict(title="The Shawshank Redemption", media_type=MediaType.movie, year=1994, status=WatchStatus.watched,   rating=9.0, genres="Drama"),
    dict(title="Severance",                media_type=MediaType.show,  year=2022, status=WatchStatus.caught_up, rating=9.0, genres="Sci-Fi"),
    dict(title="Parasite",                 media_type=MediaType.movie, year=2019, status=WatchStatus.watched,   rating=8.5, genres="Thriller"),
    dict(title="The Bear",                 media_type=MediaType.show,  year=2022, status=WatchStatus.watching,  rating=8.5, genres="Drama"),
    dict(title="Arrival",                  media_type=MediaType.movie, year=2016, status=WatchStatus.watched,   rating=8.0, genres="Sci-Fi"),
    dict(title="Knives Out",               media_type=MediaType.movie, year=2019, status=WatchStatus.watched,   rating=7.5, genres="Mystery"),
    dict(title="Past Lives",               media_type=MediaType.movie, year=2023, status=WatchStatus.planned,   rating=7.0, genres="Drama"),
]


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    db = TestingSession()
    for data in TEST_ENTRIES:
        db.add(Entry(**data))
    db.commit()
    db.close()

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
