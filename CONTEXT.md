# FinAtlas Development Context

## Current Phase
Phase 1 — Basic system skeleton & runserver (in progress)

## Status
- Flask application factory created in `app/__init__.py`.
- Gunicorn entrypoint configured via `gunicorn.conf.py` and `package.json`.
- Supabase migration applied for RLS-ready `screenings` and `cases` tables.
- Deterministic sanctions loader reads local `unsc.xml`, `eu.xml`, `ofac.xml`.
- Deterministic scoring implemented (sanctions, large transaction, high-risk jurisdiction).
- Gemini REST client implemented with retries, structured output validation, and explicit error handling.
- Screening endpoints `/api/screen/single` and `/api/screen/batch` implemented.
- Minimal HTML/CSS/JS dashboard created at `/`.

## Next (Phase 2)
- Full unit-test suite with mocked Gemini.
- Expanded ingestion (sample dataset, additional validation).
- Enhanced name matching and fuzzy sanctions logic.
