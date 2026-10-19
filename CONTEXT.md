# FinAtlas Development Context

## Current Phase
Phase 2 — Full scoring engine implementation (done)

## Status
- Flask application factory created in `app/__init__.py`.
- WSGI entrypoint added in `wsgi.py` and used by Gunicorn, fixing the `app:create_app` deployment error.
- Supabase migration applied for RLS-ready `screenings` and `cases` tables.
- Deterministic sanctions loader performs exact/normalised matching against local `unsc.xml`, `eu.xml`, `ofac.xml`, including entity IDs and aliases.
- Deterministic scoring implemented (sanctions +0.50, large transaction +0.20, high-risk jurisdiction +0.15), cumulative and capped at `1.0`.
- Gemini REST client calls the model for any transaction matching at least one rule, with bounded retries, structured JSON output validation, and explicit failure handling.
- Gemini receives the deterministic score and returns the final refined score, confidence, reasoning and false-positive assessment.
- Risk classification thresholds enforced: `>0.85` High, `0.50–0.85` Medium, `<0.50` Low.
- Screening endpoints `/api/screen/single` and `/api/screen/batch` implemented.
- Unit tests added for sanctions matching, deterministic scoring and Gemini integration (Gemini mocked).
- Minimal HTML/CSS/JS dashboard created at `/`.

## Next (Phase 3)
- Expanded ingestion (sample dataset, additional validation, background batch processing).
- Case management workflow and investigation APIs.
