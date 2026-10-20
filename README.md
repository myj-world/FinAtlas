# FinAtlas — AI-Powered AML System

**AI-powered money laundering detection and sanctions screening for banks and businesses.**

FinAtlas is an AI-powered AML platform combining deterministic sanctions list matching, rule-based risk scoring, and Gemini AI analysis. It identifies financial risks, verifies false positives, and uncovers suspicious patterns that traditional rule-based systems miss.

## Features

- **Multi-Format Ingestion:** Process bulk CSV uploads, pre-loaded sample data, or single-transaction manual entry.
- **Sanctions Screening:** Direct matching against UNSC, EU, and OFAC consolidated lists.
- **Rule-Based Scoring:** Weighted risk scoring for direct sanctions matches, large transactions, and high-risk jurisdictions.
- **Gemini AI Analysis:** Reviews every transaction for unusual patterns, regardless of deterministic rule matches; detected patterns add to the weighted score.
- **REST APIs:** Developer-friendly endpoints for single (`/api/screen/single`) and batch (`/api/screen/batch`) screening, plus optional async background batch processing.
- **Risk Dashboard & Case Management:** Interactive investigator reports with risk distributions, alert disagreements, Gemini explanations, and persistent per-user case tracking via Supabase.

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
   - `SUPABASE_KEY` or `SUPABASE_ANON_KEY` (Supabase anon key)
   - `GEMINI_API_KEY`
   - `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` (used by the browser; in the preview VM these mirror the Supabase values)
3. (Optional) Set `REQUIRE_AUTH=false` and `REQUIRE_MFA=false` for local development without Supabase Auth; never disable these in production.
4. Run the development server:
   ```bash
   npm run dev
   # or directly
   python -m gunicorn -c gunicorn.conf.py wsgi:application
   ```
5. Open the dashboard at the served URL (default http://localhost:8000).
6. Sign in or create an account. New accounts receive a confirmation email; clicking the link returns you to the dashboard and prompts for TOTP-based MFA enrolment. Existing users with MFA enabled are asked for their authenticator code at each sign-in.
   - Ensure your Supabase project does **not** enforce MFA at the project level; FinAtlas enforces AAL2 lazily after sign-in so users can enrol on first access.
7. Run the unit tests:
   ```bash
   npm test
   # or directly
   python -m pytest
   ```

## Phase 2 scope

- Flask application factory and Gunicorn WSGI entrypoint (`wsgi.py`).
- Exact/normalised deterministic sanctions matching against local `unsc.xml`, `eu.xml` and `ofac.xml`, including entity IDs and aliases.
- Weighted risk scoring, cumulative and capped at `1.0`: direct sanctions match `+0.30`, transaction above `$1,000 USD` equivalent `+0.05`, high-risk sender/receiver jurisdiction `+0.10`, and AI-detected unusual transaction pattern `+0.55`.
- Gemini REST client with bounded retries, structured JSON output validation, and explicit failure handling.
- Every transaction is sent to Gemini, including transactions with no deterministic matches. Gemini returns whether an unusual pattern was detected, confidence, reasoning, and a false-positive assessment; the backend applies the `+0.55` pattern weight when detected.
- Risk classification thresholds: `>0.85` High, `0.50–0.85` Medium, `<0.50` Low. For example, the four listed weights sum to `1.0` when all apply.
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

## Phase 4 scope

- Supabase Auth integration with MFA enforcement (AAL2) on protected API endpoints and in the frontend.
- Row-level security policies on `screenings`, `cases`, and `batches` so data is isolated per user.
- Background batch screening: `POST /api/screen/batch?async=true` returns a `batch_id` immediately and processes rows in a worker thread; `GET /api/screen/batch/<id>` returns progress.
- Dashboard API: `GET /api/screenings/stats` returns risk distributions, alert disagreements, recent screenings, and open-case counts.
- Screenings API: `GET /api/screenings` and `GET /api/screenings/<id>` for listing and detail.
- Cases API: `GET /api/cases`, `POST /api/cases`, `GET /api/cases/<id>`, `PATCH /api/cases/<id>`, `DELETE /api/cases/<id>`.
- Auth API: `GET /api/auth/me` returns the current user and MFA status.
- Modern vanilla-JS SPA dashboard with sidebar navigation, KPI cards, risk-distribution chart, screenings/cases tables, single/batch screening forms, and a screening-detail modal with Gemini explanations and case creation.

## Project Documentation

- [`SPEC.md`](SPEC.md) — System architecture, data schema, risk scoring thresholds, and API specifications.
- [`AI_DISCLOSURE.md`](AI_DISCLOSURE.md) — Information on AI models (Gemini REST API), development tools, and third-party data sources.
- [`AGENTS.md`](AGENTS.md) — Guidelines and agent personas used for automated development and code generation.
- [`SKILLS.md`](SKILLS.md) — Custom workflows and automated execution skills configured for the workspace.
- [`CONTEXT.md`](CONTEXT.md) — Real-time development state tracker for AI-assisted workflows.

## Deployment

**Live Application:** To be added.

*Developed for the DevMarketplace × NED AI Hackathon (October 19–22, 2026).*
