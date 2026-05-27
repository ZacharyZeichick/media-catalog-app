"""Claude API — personalized recommendations from the user's catalog."""

import os

import anthropic

from app.models.catalog import Entry

MODEL = "claude-haiku-4-5-20251001"

# ── Tool schemas ────────────────────────────────────────────────────────

RECOMMEND_TOOL = {
    "name": "recommend",
    "description": "Return exactly 3 movie/show recommendations from the user's catalog",
    "input_schema": {
        "type": "object",
        "properties": {
            "recommendations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "entry_id": {"type": "integer", "description": "The catalog entry ID"},
                        "title": {"type": "string", "description": "The title"},
                        "explanation": {"type": "string", "description": "2-3 sentence explanation of why this fits"},
                    },
                    "required": ["entry_id", "title", "explanation"],
                },
                "minItems": 3,
                "maxItems": 3,
            }
        },
        "required": ["recommendations"],
    },
}

DISCOVER_TOOL = {
    "name": "discover",
    "description": "Suggest exactly 3 movies/shows the user has NOT seen, based on their taste",
    "input_schema": {
        "type": "object",
        "properties": {
            "recommendations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "The exact title"},
                        "year": {"type": "integer", "description": "Release year"},
                        "media_type": {"type": "string", "enum": ["movie", "show"], "description": "movie or show"},
                        "explanation": {"type": "string", "description": "2-3 sentence explanation of why this fits their taste"},
                    },
                    "required": ["title", "year", "media_type", "explanation"],
                },
                "minItems": 3,
                "maxItems": 3,
            }
        },
        "required": ["recommendations"],
    },
}

# ── System prompts ──────────────────────────────────────────────────────

REWATCH_SYSTEM = """You are a personal movie/TV recommendation engine. The user wants to REWATCH something from their catalog.

## Rating system
- Rating (1-10): how much the user liked it overall
- Vibe tags: Funny, Dark, Intense, Heartfelt, Cozy, Creepy, Hype, Easy Watch, Mind-Bending, Emotional Ride, Slow Burn, Bingeable
- Rewatch tags: Never, Rarely, Sometimes, Anytime

## Rules
- ALWAYS prioritize entries with Rewatch tag "Anytime" or "Sometimes". NEVER recommend entries tagged "Never".
- Match the user's mood request to vibe tags, genres, AND the description/plot.
- High ratings mean the user loved it — weight these heavily.
- Be strict about mood matching. Here are some important distinctions:
  - "Feel-Good" / "Comfort" = lighthearted, warm, happy endings, uplifting. NOT bittersweet, melancholy, or emotionally devastating. Eternal Sunshine of the Spotless Mind is NOT feel-good. Requiem for a Dream is NOT feel-good.
  - "Funny" / "Comedy" = genuinely comedic, makes you laugh. A thriller with one funny scene is NOT a comedy.
  - "Easy Watch" / "Background" = low-effort, not demanding, familiar comfort. NOT complex or heavy.
  - "Dark" = morally grey, bleak, heavy themes. NOT just serious.
  - "Intense" = tension, suspense, edge-of-seat. Can overlap with action or thriller.
  - "Action-Packed" = physical action, fights, chases, explosions. NOT just exciting plot.

Pick exactly 3 entries that best match. Explain why each fits in 2-3 conversational sentences."""

WATCH_NEXT_SYSTEM = """You are a personal movie/TV recommendation engine. The user has a backlog of planned movies and shows they haven't watched yet.

## Available data
Title, year, genres, IMDb rating, Rotten Tomatoes score, Metacritic score, and a brief description.

## Rules
- Match the user's mood request to genres AND the description/plot. Genre + description fit matters more than raw ratings.
- Be strict about mood matching (same rules as below):
  - "Feel-Good" / "Comfort" = lighthearted, warm, uplifting. NOT bittersweet or heavy dramas.
  - "Funny" / "Comedy" = genuinely comedic. NOT a drama with occasional humor.
  - "Easy Watch" = casual, low-effort, not demanding. NOT complex or heavy.
  - "Dark" = morally grey, bleak, heavy themes.
  - "Intense" = tension, suspense, edge-of-seat.
  - "Action-Packed" = physical action, fights, chases.
  - "Critically Acclaimed" = prioritize highest external ratings above all else.
  - "Start a New Series" = ONLY recommend TV shows, not movies.
  - "Quick Movie" = ONLY recommend movies, not TV shows.
  - "Binge-Worthy" = series with multiple seasons or lots of episodes.
  - "Hidden Gem" = lesser-known titles, avoid the most obvious/popular picks.
- Use external ratings as a tiebreaker when mood fit is equal.

Pick exactly 3 entries that best match. Explain why each fits in 2-3 conversational sentences."""

DISCOVER_SYSTEM = """You are a personal movie/TV recommendation engine. The user wants to discover NEW titles they haven't seen.

Below is their full catalog with scores and tags. Use it to understand their taste:
- What genres do they gravitate toward?
- What vibe tags appear most?
- What do they rate highest?
- What types of shows/movies do they seem to love?

## Rules
- Suggest 3 titles that are NOT in their catalog. Check every title in the catalog and do NOT suggest any of them.
- Suggest real, well-known movies and TV shows. Do not invent titles.
- Match your suggestions to the user's mood request AND their demonstrated taste.
- Provide the exact title, release year, and whether it's a movie or show.
- Explain why it fits their taste and mood in 2-3 conversational sentences.
- Be strict about mood matching:
  - "Feel-Good" = lighthearted, warm, happy. NOT bittersweet or heavy.
  - "Funny" = genuinely comedic.
  - "Based on My Taste" = analyze their highest-rated entries and find similar titles.
  - "More Like My Favorites" = find titles very similar to their top vibe-scored entries.
  - "Something I'd Never Pick" = deliberately outside their usual genres/moods — stretch picks.

Pick exactly 3 titles."""

# ── Presets ──────────────────────────────────────────────────────────────

SHARED_PRESETS = {
    "Comfort / Feel-Good": "I want something lighthearted, warm, and uplifting with a happy ending. Pure comfort viewing — nothing sad, bittersweet, or heavy.",
    "Make Me Laugh": "I want a comedy that will genuinely make me laugh. Witty, funny, lighthearted humor.",
    "Something Intense": "I want something gripping and intense — thriller, suspense, edge-of-my-seat tension.",
    "Action-Packed": "I want high-energy action — fights, chases, explosions, adrenaline.",
    "Dark & Gritty": "I want something dark, morally grey, and gritty. Heavy themes, noir vibes.",
    "Mind-Bending": "I want something complex and thought-provoking — twists, puzzles, makes me think.",
    "Heartfelt / Emotional": "I want something moving and emotional — heartfelt drama that pulls at the heartstrings.",
    "Easy Watch": "I want something casual and low-effort. Not demanding, easy to follow, just a good time.",
    "Late Night": "Late night mood — something creepy, unsettling, or thriller/horror vibes.",
    "Something Different": "Surprise me with something outside my usual taste. I want to branch out.",
}

REWATCH_PRESETS = {
    **SHARED_PRESETS,
    "Background Noise": "I want something familiar and chill I can half-watch while doing other stuff. Low-effort, rewatchable comfort.",
    "Impress Someone": "I'm watching with someone I want to impress. Recommend crowd-pleasers with high craft — universally loved, visually impressive, great storytelling.",
}

WATCH_NEXT_PRESETS = {
    **SHARED_PRESETS,
    "Critically Acclaimed": "I want the highest-rated, most acclaimed titles in my backlog. Prioritize external ratings above everything else.",
    "Start a New Series": "I want to start a new TV series. Only recommend shows, not movies.",
    "Quick Movie": "I want a movie to watch tonight. Only recommend movies, not TV shows.",
    "Binge-Worthy": "I want a series I can binge — multiple seasons or lots of episodes.",
    "Hidden Gem": "I want something lesser-known from my backlog — not the obvious popular picks.",
}

DISCOVER_PRESETS = {
    **SHARED_PRESETS,
    "Based on My Taste": "Analyze my catalog and recommend titles that match my overall taste profile — genres I love, what I rate highest.",
    "More Like My Favorites": "Look at my highest-rated entries and find similar titles I haven't seen.",
    "Something I'd Never Pick": "Deliberately suggest something outside my comfort zone — genres or styles I don't usually watch, but that I might love.",
}

PRESET_KEYS = {
    "rewatch": list(REWATCH_PRESETS.keys()),
    "watch_next": list(WATCH_NEXT_PRESETS.keys()),
    "discover": list(DISCOVER_PRESETS.keys()),
}


def resolve_mood(mode: str, mood: str | None, preset: str | None) -> str:
    """Resolve a preset name to its prompt text, or use freeform mood."""
    if preset:
        presets = {"rewatch": REWATCH_PRESETS, "watch_next": WATCH_NEXT_PRESETS, "discover": DISCOVER_PRESETS}
        prompt = presets.get(mode, {}).get(preset)
        if prompt:
            return prompt
    return mood or "Recommend me something good."


# ── Entry formatters ────────────────────────────────────────────────────

def _format_rewatch(entry: Entry) -> str:
    parts = [
        f"ID:{entry.id}",
        entry.title,
        entry.media_type.value,
        str(entry.year or ""),
        entry.genres or "",
    ]
    if entry.rating is not None:
        parts.append(f"Rating:{entry.rating}")
    if entry.vibe_tags:
        parts.append(f"Vibes:{entry.vibe_tags}")
    if entry.rewatch_tag:
        parts.append(f"Rewatch:{entry.rewatch_tag.value}")
    if entry.notes_what:
        parts.append(f'"{entry.notes_what[:120]}"')
    return " | ".join(parts)


def _format_watch_next(entry: Entry) -> str:
    parts = [
        f"ID:{entry.id}",
        entry.title,
        entry.media_type.value,
        str(entry.year or ""),
        entry.genres or "",
    ]
    if entry.imdb_rating is not None:
        parts.append(f"IMDb:{entry.imdb_rating}")
    if entry.rt_tomatometer is not None:
        parts.append(f"RT:{entry.rt_tomatometer}%")
    if entry.metacritic is not None:
        parts.append(f"MC:{entry.metacritic}")
    if entry.notes_what:
        parts.append(f'"{entry.notes_what[:120]}"')
    return " | ".join(parts)


def _format_taste(entry: Entry) -> str:
    """Compact format for discover mode — shows taste profile."""
    parts = [
        entry.title,
        entry.media_type.value,
        entry.genres or "",
    ]
    if entry.rating is not None:
        parts.append(f"Rating:{entry.rating}")
    if entry.vibe_tags:
        parts.append(f"Vibes:{entry.vibe_tags}")
    return " | ".join(parts)


# ── API calls ───────────────────────────────────────────────────────────

def _call_claude(system: str, user_message: str, tool: dict) -> list[dict]:
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    client = anthropic.Anthropic(api_key=key)
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": user_message}],
        tools=[tool],
        tool_choice={"type": "tool", "name": tool["name"]},
    )

    for block in response.content:
        if block.type == "tool_use":
            return block.input["recommendations"]

    raise RuntimeError("Claude did not return a tool call")


def get_recommendations(entries: list[Entry], mood: str, mode: str) -> list[dict]:
    """Pick 3 from the user's catalog (rewatch or watch_next mode)."""
    if len(entries) < 3:
        raise ValueError("Not enough entries to recommend from")

    if mode == "rewatch":
        system = REWATCH_SYSTEM
        catalog_text = "\n".join(_format_rewatch(e) for e in entries)
    else:
        system = WATCH_NEXT_SYSTEM
        catalog_text = "\n".join(_format_watch_next(e) for e in entries)

    user_message = f"Here is my catalog:\n\n{catalog_text}\n\nI'm in the mood for: {mood}"
    return _call_claude(system, user_message, RECOMMEND_TOOL)


def get_discoveries(entries: list[Entry], mood: str) -> list[dict]:
    """Suggest 3 titles NOT in the user's catalog."""
    # Build taste profile from scored entries
    scored = [e for e in entries if e.rating is not None]
    scored.sort(key=lambda e: e.rating or 0, reverse=True)

    catalog_text = "\n".join(_format_taste(e) for e in scored[:80])
    title_list = ", ".join(e.title for e in entries)

    user_message = (
        f"Here are my highest-rated entries (taste profile):\n\n{catalog_text}\n\n"
        f"Here is EVERY title in my catalog (do NOT suggest any of these): {title_list}\n\n"
        f"I'm looking for: {mood}"
    )
    return _call_claude(DISCOVER_SYSTEM, user_message, DISCOVER_TOOL)


# ── Convince Me ────────────────────────────────────────────────────────

CONVINCE_SYSTEM = """You are the user's friend recommending something to watch. They have something in their backlog and need a nudge.

Guidelines:
- 2-4 sentences, no more
- Talk about the entry itself — what makes it worth watching, what kind of mood it suits, what to expect going in
- Do NOT reference other titles or the user's watch history
- Conversational tone — like a friend, not a critic or hype machine
- Be honest — if it's a slow burn say so, if it's dumb fun say so
- Never use phrases like "okay hear me out", "safe bet", "trust me on this one", or excessive exclamation points
- No bullet points, no italics, no formatting"""


def build_taste_context(entry: Entry, all_scored: list[Entry]) -> list[Entry]:
    """Pick scored entries relevant to the target: genre/tag matches + random variety."""
    import random

    target_genres = set()
    if entry.genres:
        target_genres = {g.strip().lower() for g in entry.genres.split(",")}

    target_vibes = set()
    if entry.vibe_tags:
        target_vibes = {t.strip().lower() for t in entry.vibe_tags.split(",")}

    # Score each entry by overlap with target
    scored_with_overlap = []
    for e in all_scored:
        if e.id == entry.id:
            continue
        overlap = 0
        if e.genres:
            e_genres = {g.strip().lower() for g in e.genres.split(",")}
            overlap += len(target_genres & e_genres) * 2
        if e.vibe_tags:
            e_vibes = {t.strip().lower() for t in e.vibe_tags.split(",")}
            overlap += len(target_vibes & e_vibes)
        scored_with_overlap.append((e, overlap))

    # Top genre/tag matches
    scored_with_overlap.sort(key=lambda x: (-x[1], -(x[0].rating or 0)))
    matches = [e for e, o in scored_with_overlap if o > 0][:10]
    match_ids = {e.id for e in matches}

    # Pad with random high-rated for variety
    high_rated = [e for e in all_scored if e.rating and e.rating >= 7 and e.id not in match_ids and e.id != entry.id]
    random.shuffle(high_rated)
    result = matches + high_rated[:max(0, 5 - len(matches))]

    return result[:15]


def get_convince_pitch(entry: Entry) -> str:
    """Generate a pitch for why the user should watch this entry."""
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    parts = [entry.title, entry.media_type.value, str(entry.year or "")]
    if entry.genres:
        parts.append(entry.genres)
    if entry.notes_what:
        parts.append(f'"{entry.notes_what[:200]}"')
    if entry.imdb_rating is not None:
        parts.append(f"IMDb:{entry.imdb_rating}")
    if entry.rt_tomatometer is not None:
        parts.append(f"RT:{entry.rt_tomatometer}%")
    target_text = " | ".join(parts)

    user_message = f"Title I'm considering: {target_text}\n\nConvince me to watch {entry.title}."

    client = anthropic.Anthropic(api_key=key)
    response = client.messages.create(
        model=MODEL,
        max_tokens=512,
        system=CONVINCE_SYSTEM,
        messages=[{"role": "user", "content": user_message}],
    )

    return response.content[0].text
