"""Migrate scoring system: craft_score + vibe_score → rating, mood_tag → vibe_tags.

Uses table-recreate approach since SQLite can't drop columns with CHECK constraints.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "catalog.db")

MOOD_TO_VIBE = {
    "Feel-Good": "Cozy",
    "Dark": "Dark",
    "Intense": "Intense",
    "Chill": "Cozy",
    "Funny": "Funny",
    "Thought-Provoking": "Mind-Bending",
    "Action-Packed": "Hype",
    "Heartfelt": "Heartfelt",
    "Creepy": "Creepy",
    "Romantic": "Heartfelt",
}

# Columns to keep (excludes craft_score, vibe_score, mood_tag)
KEEP_COLS = [
    "id", "title", "media_type", "year", "year_end", "imdb_id", "imdb_link",
    "poster_url", "genres", "rt_tomatometer", "rt_audience", "imdb_rating",
    "metacritic", "legacy_rating", "rewatch_tag", "notes_what", "notes_why",
    "notes_recommend", "status", "date_watched", "date_added", "updated_on",
    "streaming_sources", "tmdb_id", "poster_path", "backdrop_path", "hero_eligible",
]


def migrate():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = OFF")
    cur = conn.cursor()

    # Check if already migrated
    cur.execute("PRAGMA table_info(entries)")
    columns = {row[1] for row in cur.fetchall()}
    if "rating" in columns and "craft_score" not in columns:
        print("Already migrated. Skipping.")
        conn.close()
        return

    print("Starting migration...")

    # Step 1: Create new table with correct schema
    cur.execute("""
        CREATE TABLE entries_new (
            id INTEGER PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            media_type VARCHAR(5) NOT NULL,
            year INTEGER,
            year_end INTEGER,
            imdb_id VARCHAR(20) UNIQUE,
            imdb_link VARCHAR(512),
            poster_url VARCHAR(512),
            genres VARCHAR(255),
            rt_tomatometer INTEGER,
            rt_audience INTEGER,
            imdb_rating FLOAT,
            metacritic INTEGER,
            legacy_rating INTEGER,
            rewatch_tag VARCHAR(9),
            notes_what TEXT,
            notes_why TEXT,
            notes_recommend TEXT,
            status VARCHAR(11) NOT NULL,
            date_watched DATETIME,
            date_added DATETIME NOT NULL,
            updated_on DATETIME NOT NULL,
            streaming_sources TEXT,
            tmdb_id INTEGER,
            poster_path TEXT,
            backdrop_path TEXT,
            hero_eligible INTEGER NOT NULL DEFAULT 1,
            rating FLOAT,
            vibe_tags VARCHAR(255),
            CHECK (rating IS NULL OR (rating >= 1 AND rating <= 10))
        )
    """)

    # Step 2: Copy data, converting scores inline
    cols_str = ", ".join(KEEP_COLS)
    cur.execute(f"""
        INSERT INTO entries_new ({cols_str}, rating, vibe_tags)
        SELECT {cols_str},
               COALESCE(vibe_score, craft_score) AS rating,
               NULL AS vibe_tags
        FROM entries
    """)
    print(f"  Copied {cur.rowcount} entries")

    # Step 3: Map old mood_tag → vibe_tags
    for old_tag, new_tag in MOOD_TO_VIBE.items():
        cur.execute(
            "UPDATE entries_new SET vibe_tags = ? WHERE id IN (SELECT id FROM entries WHERE mood_tag = ?)",
            (new_tag, old_tag),
        )

    # Step 4: Swap tables
    cur.execute("DROP TABLE entries")
    cur.execute("ALTER TABLE entries_new RENAME TO entries")

    # Step 5: Recreate indexes
    cur.execute("CREATE INDEX IF NOT EXISTS ix_entries_id ON entries (id)")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_entries_title ON entries (title)")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_entries_imdb_id ON entries (imdb_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_entries_tmdb_id ON entries (tmdb_id)")

    conn.execute("PRAGMA foreign_keys = ON")
    conn.commit()

    # Verify
    cur.execute("SELECT COUNT(*) FROM entries WHERE rating IS NOT NULL")
    rated = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM entries WHERE vibe_tags IS NOT NULL")
    tagged = cur.fetchone()[0]
    print(f"  Ratings migrated: {rated}")
    print(f"  Vibe tags migrated: {tagged}")

    conn.close()
    print("Migration complete.")


if __name__ == "__main__":
    migrate()
