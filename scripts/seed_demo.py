"""
Seed the database with ~20 well-known public movies and shows for demo/screenshot use.

Usage (from project root):
    python scripts/seed_demo.py

Safe to rerun — skips entries that already exist (matched by title + media_type).
Does not require any API keys or external calls.
"""

import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from app.database import Base, engine, SessionLocal
from app.models.catalog import Entry, MediaType, RewatchTag, VibeTag, WatchStatus

# ---------------------------------------------------------------------------
# Demo entries
# ---------------------------------------------------------------------------

DEMO_ENTRIES = [
    # ── Watched movies ──────────────────────────────────────────────────
    dict(
        title="The Shawshank Redemption",
        media_type=MediaType.movie,
        year=1994,
        genres="Drama",
        status=WatchStatus.watched,
        rating=9.5,
        rewatch_tag=RewatchTag.anytime,
        vibe_tags=f"{VibeTag.heartfelt},{VibeTag.slow_burn},{VibeTag.emotional_ride}",
        imdb_rating=9.3,
        rt_tomatometer=89,
        rt_audience=98,
        metacritic=80,
        notes_what="A wrongly convicted banker forms a friendship with a fellow prisoner over decades inside Shawshank State Penitentiary.",
        notes_why="One of the few films that gets better every rewatch. The hope angle never gets old.",
        notes_recommend="Anyone who hasn't seen it. Non-negotiable.",
        date_watched=datetime(2023, 3, 12),
    ),
    dict(
        title="Parasite",
        media_type=MediaType.movie,
        year=2019,
        genres="Thriller, Drama, Dark Comedy",
        status=WatchStatus.watched,
        rating=9.0,
        rewatch_tag=RewatchTag.sometimes,
        vibe_tags=f"{VibeTag.dark},{VibeTag.intense},{VibeTag.mind_bending}",
        imdb_rating=8.5,
        rt_tomatometer=99,
        rt_audience=90,
        metacritic=96,
        notes_what="A poor Korean family schemes their way into employment with a wealthy household.",
        notes_why="Flawless construction. Every scene earns what comes after it.",
        notes_recommend="Anyone who can handle subtitles and tonal whiplash.",
        date_watched=datetime(2023, 8, 5),
    ),
    dict(
        title="Everything Everywhere All at Once",
        media_type=MediaType.movie,
        year=2022,
        genres="Sci-Fi, Comedy, Drama",
        status=WatchStatus.watched,
        rating=9.0,
        rewatch_tag=RewatchTag.anytime,
        vibe_tags=f"{VibeTag.mind_bending},{VibeTag.emotional_ride},{VibeTag.hype}",
        imdb_rating=7.8,
        rt_tomatometer=95,
        rt_audience=88,
        metacritic=81,
        notes_what="A laundromat owner discovers she can access skills from parallel universe versions of herself while dealing with an IRS audit.",
        notes_why="Somehow both maximalist chaos and a genuinely moving mother-daughter story.",
        notes_recommend="People who like weird films that actually have something to say.",
        date_watched=datetime(2023, 11, 20),
    ),
    dict(
        title="Interstellar",
        media_type=MediaType.movie,
        year=2014,
        genres="Sci-Fi, Drama",
        status=WatchStatus.watched,
        rating=8.5,
        rewatch_tag=RewatchTag.sometimes,
        vibe_tags=f"{VibeTag.intense},{VibeTag.slow_burn},{VibeTag.mind_bending}",
        imdb_rating=8.7,
        rt_tomatometer=73,
        rt_audience=86,
        metacritic=74,
        notes_what="A former NASA pilot leads a mission through a wormhole to find a new home for humanity.",
        notes_why="The docking scene and the third act alone justify the runtime. The science hand-waving is forgivable.",
        notes_recommend="Nolan fans and anyone who wants a film that takes its ideas seriously.",
        date_watched=datetime(2024, 1, 8),
    ),
    dict(
        title="The Grand Budapest Hotel",
        media_type=MediaType.movie,
        year=2014,
        genres="Comedy, Drama",
        status=WatchStatus.watched,
        rating=8.5,
        rewatch_tag=RewatchTag.anytime,
        vibe_tags=f"{VibeTag.funny},{VibeTag.cozy},{VibeTag.easy_watch}",
        imdb_rating=8.1,
        rt_tomatometer=92,
        rt_audience=85,
        metacritic=88,
        notes_what="The adventures of a legendary hotel concierge and his lobby boy protégé in 1930s Europe.",
        notes_why="Wes Anderson at peak Wes Anderson. The aesthetic is the argument.",
        notes_recommend="Anyone who just wants to feel good for 100 minutes.",
        date_watched=datetime(2023, 6, 14),
    ),
    dict(
        title="Hereditary",
        media_type=MediaType.movie,
        year=2018,
        genres="Horror",
        status=WatchStatus.watched,
        rating=8.0,
        rewatch_tag=RewatchTag.rarely,
        vibe_tags=f"{VibeTag.creepy},{VibeTag.dark},{VibeTag.intense}",
        imdb_rating=7.3,
        rt_tomatometer=90,
        rt_audience=66,
        metacritic=87,
        notes_what="A family unravels after the death of their secretive grandmother.",
        notes_why="The most genuinely unsettling film I've seen in years. Toni Collette deserved every award.",
        notes_recommend="Horror fans only. Not for the faint of heart.",
        date_watched=datetime(2023, 10, 28),
    ),
    dict(
        title="Knives Out",
        media_type=MediaType.movie,
        year=2019,
        genres="Mystery, Comedy",
        status=WatchStatus.watched,
        rating=8.5,
        rewatch_tag=RewatchTag.sometimes,
        vibe_tags=f"{VibeTag.funny},{VibeTag.easy_watch},{VibeTag.hype}",
        imdb_rating=7.9,
        rt_tomatometer=97,
        rt_audience=92,
        metacritic=82,
        notes_what="A detective investigates the death of a wealthy crime novelist during a family gathering.",
        notes_why="Rare film that's both smart and crowd-pleasing without compromising either.",
        notes_recommend="Great for group watching. Everyone enjoys it.",
        date_watched=datetime(2024, 2, 17),
    ),
    dict(
        title="Arrival",
        media_type=MediaType.movie,
        year=2016,
        genres="Sci-Fi, Drama",
        status=WatchStatus.watched,
        rating=9.0,
        rewatch_tag=RewatchTag.sometimes,
        vibe_tags=f"{VibeTag.mind_bending},{VibeTag.slow_burn},{VibeTag.emotional_ride}",
        imdb_rating=7.9,
        rt_tomatometer=94,
        rt_audience=82,
        metacritic=81,
        notes_what="A linguist is recruited to communicate with extraterrestrials who have landed on Earth.",
        notes_why="One of the best sci-fi films of the decade. The ending reframes the entire film.",
        notes_recommend="Thoughtful sci-fi fans. Not an action film.",
        date_watched=datetime(2023, 5, 3),
    ),
    # ── Planned movies ───────────────────────────────────────────────────
    dict(
        title="Past Lives",
        media_type=MediaType.movie,
        year=2023,
        genres="Drama, Romance",
        status=WatchStatus.planned,
        imdb_rating=7.9,
        rt_tomatometer=97,
        rt_audience=90,
        metacritic=94,
    ),
    dict(
        title="Oppenheimer",
        media_type=MediaType.movie,
        year=2023,
        genres="Drama, History",
        status=WatchStatus.planned,
        imdb_rating=8.3,
        rt_tomatometer=93,
        rt_audience=91,
        metacritic=88,
    ),
    dict(
        title="The Zone of Interest",
        media_type=MediaType.movie,
        year=2023,
        genres="Drama, War",
        status=WatchStatus.planned,
        imdb_rating=7.4,
        rt_tomatometer=93,
        rt_audience=75,
        metacritic=93,
    ),
    # ── Watched shows ────────────────────────────────────────────────────
    dict(
        title="The Bear",
        media_type=MediaType.show,
        year=2022,
        year_end=None,
        genres="Drama, Comedy",
        status=WatchStatus.caught_up,
        rating=9.0,
        rewatch_tag=RewatchTag.sometimes,
        vibe_tags=f"{VibeTag.intense},{VibeTag.emotional_ride},{VibeTag.bingeable}",
        imdb_rating=8.6,
        rt_tomatometer=98,
        rt_audience=93,
        metacritic=88,
        notes_what="A fine-dining chef returns to Chicago to run his family's chaotic sandwich shop after a family tragedy.",
        notes_why="Season 1 episode 7 (the long take episode) is one of the best single episodes of television ever made.",
        notes_recommend="Anyone who can handle stress. Cook or not.",
        date_watched=datetime(2024, 3, 1),
    ),
    dict(
        title="Succession",
        media_type=MediaType.show,
        year=2018,
        year_end=2023,
        genres="Drama",
        status=WatchStatus.watched,
        rating=9.5,
        rewatch_tag=RewatchTag.sometimes,
        vibe_tags=f"{VibeTag.dark},{VibeTag.intense},{VibeTag.bingeable}",
        imdb_rating=8.9,
        rt_tomatometer=98,
        rt_audience=88,
        metacritic=74,
        notes_what="The Roy family battles for control of their global media empire as their aging patriarch considers his succession.",
        notes_why="The writing is the sharpest on television. Every character is a monster you can't stop watching.",
        notes_recommend="Anyone who tolerates morally bankrupt characters. One of the all-time greats.",
        date_watched=datetime(2023, 9, 15),
    ),
    dict(
        title="Severance",
        media_type=MediaType.show,
        year=2022,
        year_end=None,
        genres="Sci-Fi, Thriller, Drama",
        status=WatchStatus.caught_up,
        rating=9.0,
        rewatch_tag=RewatchTag.anytime,
        vibe_tags=f"{VibeTag.mind_bending},{VibeTag.creepy},{VibeTag.slow_burn}",
        imdb_rating=8.7,
        rt_tomatometer=97,
        rt_audience=93,
        metacritic=85,
        notes_what="Employees at a mysterious company undergo a procedure that surgically separates their work and personal memories.",
        notes_why="The premise is used to its absolute maximum. Every episode ends on a perfect cliffhanger.",
        notes_recommend="Anyone who wants a slow burn that pays off.",
        date_watched=datetime(2024, 4, 10),
    ),
    dict(
        title="The Rehearsal",
        media_type=MediaType.show,
        year=2022,
        year_end=2024,
        genres="Comedy, Documentary",
        status=WatchStatus.watched,
        rating=9.5,
        rewatch_tag=RewatchTag.sometimes,
        vibe_tags=f"{VibeTag.mind_bending},{VibeTag.funny},{VibeTag.slow_burn}",
        imdb_rating=8.3,
        rt_tomatometer=96,
        rt_audience=89,
        metacritic=88,
        notes_what="Nathan Fielder helps ordinary people rehearse difficult conversations by constructing elaborate simulations of their lives.",
        notes_why="The most unsettling and profound thing I've watched in years. Defies categorization.",
        notes_recommend="People comfortable with deeply weird television that asks real questions.",
        date_watched=datetime(2024, 5, 1),
    ),
    dict(
        title="Andor",
        media_type=MediaType.show,
        year=2022,
        year_end=2024,
        genres="Sci-Fi, Drama",
        status=WatchStatus.watched,
        rating=9.0,
        rewatch_tag=RewatchTag.sometimes,
        vibe_tags=f"{VibeTag.intense},{VibeTag.slow_burn},{VibeTag.dark}",
        imdb_rating=8.4,
        rt_tomatometer=96,
        rt_audience=90,
        metacritic=88,
        notes_what="The story of Cassian Andor's journey to becoming a Rebel spy in the years before Rogue One.",
        notes_why="Best Star Wars content by a mile. Treats the audience like adults.",
        notes_recommend="Star Wars fans and non-fans alike. It's a political thriller that happens to be set in space.",
        date_watched=datetime(2024, 2, 28),
    ),
    # ── Currently watching ───────────────────────────────────────────────
    dict(
        title="Slow Horses",
        media_type=MediaType.show,
        year=2022,
        year_end=None,
        genres="Thriller, Drama",
        status=WatchStatus.watching,
        rating=8.5,
        vibe_tags=f"{VibeTag.intense},{VibeTag.slow_burn}",
        imdb_rating=8.0,
        rt_tomatometer=98,
        rt_audience=95,
        metacritic=86,
        notes_what="A British espionage thriller following the disgraced MI5 agents of Slough House.",
    ),
    # ── Planned shows ─────────────────────────────────────────────────────
    dict(
        title="Fleabag",
        media_type=MediaType.show,
        year=2016,
        year_end=2019,
        genres="Comedy, Drama",
        status=WatchStatus.planned,
        imdb_rating=8.7,
        rt_tomatometer=99,
        rt_audience=96,
        metacritic=96,
    ),
    dict(
        title="The Leftovers",
        media_type=MediaType.show,
        year=2014,
        year_end=2017,
        genres="Drama, Mystery",
        status=WatchStatus.planned,
        imdb_rating=8.3,
        rt_tomatometer=93,
        rt_audience=86,
        metacritic=73,
    ),
    dict(
        title="I May Destroy You",
        media_type=MediaType.show,
        year=2020,
        year_end=2020,
        genres="Drama",
        status=WatchStatus.planned,
        imdb_rating=8.1,
        rt_tomatometer=99,
        rt_audience=87,
        metacritic=97,
    ),
]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    Base.metadata.create_all(bind=engine)

    session = SessionLocal()
    created = 0
    skipped = 0

    try:
        for data in DEMO_ENTRIES:
            exists = (
                session.query(Entry)
                .filter_by(title=data["title"], media_type=data["media_type"])
                .first()
            )
            if exists:
                skipped += 1
                continue

            entry = Entry(**data)
            session.add(entry)
            created += 1

        session.commit()
        print(f"Done. {created} entries created, {skipped} skipped (already existed).")

    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
