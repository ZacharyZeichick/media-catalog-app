\# Media Catalog App



A local FastAPI and SQLite application for tracking movies and TV shows, managing watchlists, enriching titles with external metadata, and generating AI-assisted recommendations.



This project was built as a personal media catalog system, similar to a lightweight private Letterboxd/TV tracker, with custom lists, ratings, tags, import utilities, and metadata backfill scripts.



\## Features



\- Track movies and TV shows in a local SQLite database

\- Search and add titles using external metadata services

\- Maintain watchlists, ratings, notes, tags, and custom lists

\- Import existing catalog data from CSV files

\- Backfill metadata, posters, IMDb data, and Watchmode data through utility scripts

\- Generate AI-assisted watch recommendations

\- Run locally through a FastAPI backend and simple web frontend



\## Tech Stack



\- Python

\- FastAPI

\- SQLite

\- SQLAlchemy

\- HTML, CSS, and JavaScript

\- External movie/TV metadata APIs

\- Claude API for recommendation support



\## Project Structure



```text

app/

&#x20; main.py

&#x20; database.py

&#x20; schemas.py

&#x20; models/

&#x20; routers/

&#x20; services/



scripts/

&#x20; import\_csv.py

&#x20; backfill\_imdb.py

&#x20; backfill\_posters.py

&#x20; backfill\_watchmode.py

&#x20; migrate\_scores.py



static/

templates/

requirements.txt

.env.example

