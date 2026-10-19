# FinAtlas — AI-Powered AML System

**AI-powered money laundering detection and sanctions screening for banks and businesses.**

FinAtlas is an AI-powered AML platform combining deterministic sanctions list matching, rule-based risk scoring, and Gemini AI analysis. It identifies financial risks, verifies false positives, and uncovers suspicious patterns that traditional rule-based systems miss.

## Features

- **Multi-Format Ingestion:** Process bulk CSV uploads, pre-loaded sample data, or single-transaction manual entry.
- **Sanctions Screening:** Direct matching against UNSC, EU, and OFAC consolidated lists.
- **Rule-Based Scoring:** Heuristic risk scoring based on transaction amounts, high-risk jurisdictions, and execution patterns.
- **Gemini AI Verification:** Contextual analysis to verify potential false positives and assign calibrated risk scores ($0.0 - 1.0$).
- **REST APIs:** Developer-friendly endpoints for single (`/api/screen/single`) and batch (`/api/screen/batch`) screening.
- **Risk Dashboard & Case Management:** Interactive investigation reports with persistent tracking via Supabase.

## Technology Stack

- **Frontend:** HTML, CSS, JavaScript
- **Backend:** Python, Flask
- **Data Processing:** Pandas
- **Database & Authentication:** Supabase (PostgreSQL with Row Level Security & MFA)
- **AI Engine:** Gemini REST API

## Getting Started

1. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   If you are using the preview VM, `npm install` will run the same step automatically.
2. Add the required secrets in the workspace Secrets panel (do not commit values):
   - `SUPABASE_URL`
   - `SUPABASE_KEY` (Supabase anon key)
   - `GEMINI_API_KEY`
3. Run the development server:
   ```bash
   npm run dev
   # or directly
   python -m gunicorn -c gunicorn.conf.py wsgi:application
   ```
4. Open the dashboard at the served URL (default http://localhost:8000).
5. Run the unit tests:
   ```bash
   npm test
   # or directly
   python -m pytest
   ```

## Phase 2 scope

- Flask application factory and Gunicorn WSGI entrypoint (`wsgi.py`).
- Exact/normalised deterministic sanctions matching against local `unsc.xml`, `eu.xml` and `ofac.xml`, including entity IDs and aliases.
- Deterministic rule scoring (direct sanctions hit, large transaction >$1,000 USD, high-risk jurisdiction), cumulative and capped at `1.0`.
- Gemini REST client with bounded retries, structured JSON output validation, and explicit failure handling.
- Gemini score refinement: the deterministic score plus context is sent to Gemini, which returns the final score, confidence, reasoning and a false-positive assessment.
- Risk classification thresholds: `>0.85` High, `0.50–0.85` Medium, `<0.50` Low.
- `/api/screen/single` and `/api/screen/batch` endpoints.
- Unit tests for sanctions matching, scoring and Gemini integration (Gemini mocked).
- Minimal HTML/CSS/JS dashboard for manual and CSV screening.

## Phase 3 scope

- Robust import / ingestion system using Pandas for CSV parsing.
- Schema validation for the FinAtlas transaction model (required + optional fields, numeric amount, supported currency, unknown-field rejection).
- `/api/import/sample` — return the built-in `sample_transactions.csv` as JSON.
- `/api/import/single` — validate and screen a manually-entered transaction.
- `/api/import/csv` — ingest a CSV file; optional `?screen=true` to screen every row.
- `/api/import/validate` — validate a JSON list or CSV upload without screening.
- `/api/screen/batch` now validates and cleans CSV/JSON input before screening.
- WSGI callable fix so `app:create_app` works with Gunicorn as well as the standard `wsgi:application` target.
- Frontend sample-dataset loader that fetches sample data and screens it as a batch.

## Project Documentation

- [`SPEC.md`](SPEC.md) — System architecture, data schema, risk scoring thresholds, and API specifications.
- [`AI_DISCLOSURE.md`](AI_DISCLOSURE.md) — Information on AI models (Gemini REST API), development tools, and third-party data sources.
- [`AGENTS.md`](AGENTS.md) — Guidelines and agent personas used for automated development and code generation.
- [`SKILLS.md`](SKILLS.md) — Custom workflows and automated execution skills configured for the workspace.
- [`CONTEXT.md`](CONTEXT.md) — Real-time development state tracker for AI-assisted workflows.

## Deployment

**Live Application:** To be added.

*Developed for the DevMarketplace × NED AI Hackathon (October 19–22, 2026).*
