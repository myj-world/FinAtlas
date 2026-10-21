# FinAtlas Development Context

## Current status

**Phase 4 — Complete.** The project now includes AML transaction screening, sanctions matching, Gemini review, CSV/JSON ingestion, investigator workflows, Supabase authentication and MFA, dashboard/history views, asynchronous batch processing, and per-user API keys.

No Phase 5 scope is recorded in the repository. Agree the next product priorities before starting another phase.

## Product and architecture

FinAtlas is a Flask application with a vanilla JavaScript single-page investigator UI. Supabase provides authentication and persistence; Gemini provides contextual review of each transaction. Gunicorn serves the app through `wsgi.py` and `gunicorn.conf.py`.

- `app/__init__.py` is the Flask application factory, registers route blueprints, initializes the batch worker, and handles Gemini and generic errors.
- `app/config.py` contains screening weights, thresholds, currencies, high-risk jurisdictions, sanctions-list filenames, and Gemini request settings.
- `app/routes/` contains auth, health, dashboard/config, import/ingestion, screening, screening history, cases, and API-key endpoints.
- `app/services/` contains auth and Supabase access, ingestion/validation, sanctions XML loading and matching, scoring, Gemini prompt/client, persistence/dashboard aggregation, batch jobs, and API-key operations.
- `app/templates/index.html`, `app/static/js/app.js`, and `app/static/css/style.css` implement the responsive investigator SPA: sign-in/sign-up, MFA setup/challenge, dashboard, screenings and details, cases, batches, single/batch screening, sample data, and API-key/API-reference views.
- `supabase/migrations/` defines RLS-protected screenings, cases, batches, screening rule/sanctions-hit details, and API keys.
- `tests/` covers the Flask API, ingestion and validation, scoring, sanctions matching, and Gemini parsing/client behavior. Gemini calls are mocked in tests.
- `unsc.xml`, `eu.xml`, and `ofac.xml` are the local sanctions data inputs. `sample_transactions.csv` is the sample import dataset.

## Completed phases

### Phase 1 — Application and persistence foundation

- Flask app factory and Gunicorn WSGI entry point.
- Supabase-backed `screenings` and `cases` tables with per-user row-level security (RLS).
- Initial web dashboard and API foundation.

### Phase 2 — Screening and scoring

- Deterministic sanctions matching against local UNSC, EU, and OFAC XML lists, including aliases and normalized/prefix token matching.
- Rule-based score weights: sanctions hit `+0.30`, transaction above USD 1,000 equivalent `+0.05`, high-risk jurisdiction `+0.10`; scores are capped at `1.0`.
- Gemini reviews every screened transaction and returns an unusual-pattern signal, confidence, reasoning, and false-positive assessment. The scoring service applies `+0.55` when Gemini flags an unusual pattern; it computes the final score from the rules rather than using Gemini's proposed score directly.
- Risk classification: High `>0.85`, Medium `>=0.50`, otherwise Low.
- Single and synchronous batch screening endpoints, with screening results persisted when Supabase is configured.

### Phase 3 — Ingestion and investigator workflows

- CSV and JSON transaction validation, supported-currency checks, sample data, and import endpoints.
- Investigator screening history, detail views, dashboard statistics, and case create/read/update/delete workflows.
- Supabase sign-in/sign-up and optional server/client MFA enforcement (AAL2).
- SPA navigation for dashboard, screening history, case management, and screening/import workflows.

### Phase 4 — Batch operations and API integration

- Background batch jobs with progress, per-row results, status polling/listing, and Supabase persistence; worker pool is initialized by the app factory.
- Persisted screening rule and sanctions-hit detail for investigation drill-down.
- Per-user API-key create, list, rotate, and revoke operations. Active keys can authenticate API requests and are scoped to their owner.
- API reference and key-management controls in the UI.

## API surface

Protected endpoints accept a Supabase access token or active API key as a Bearer token. Auth and MFA requirements are configurable.

- `GET /api/health` — service/configuration health.
- `GET /api/config` — safe frontend configuration.
- `GET /api/auth/me` — current user and MFA status.
- `POST /api/screen/single` — screen one transaction.
- `POST /api/screen/batch` — screen a JSON list or CSV upload; `?async=true` queues a background job.
- `GET /api/screen/batch/<batch_id>` and `GET /api/screen/batches` — retrieve batch status/results and list jobs.
- `GET /api/import/sample`, `POST /api/import/single`, `POST /api/import/csv`, `POST /api/import/validate` — load, validate, and optionally screen input data.
- `GET /api/screenings`, `GET /api/screenings/stats`, `GET /api/screenings/<id>` — history, dashboard stats, and screening detail.
- `GET/POST/PATCH/DELETE /api/cases` and `GET/PATCH/DELETE /api/cases/<id>` — case management.
- `GET/POST /api/api-keys`, `POST /api/api-keys/<id>/revoke`, `POST /api/api-keys/<id>/rotate` — API-key management.
- `GET /` — investigator SPA.

## Configuration and local development

See `.env.example` for names and development guidance. Main settings:

- Supabase: `SUPABASE_URL`, `SUPABASE_KEY` or `SUPABASE_ANON_KEY`; browser-safe values may use `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY`.
- `SUPABASE_SERVICE_ROLE_KEY` is server-only and required to resolve API-key bearer tokens.
- `GEMINI_API_KEY` is server-only. Gemini timeout and retry count are configurable with `GEMINI_TIMEOUT_SECONDS` and `GEMINI_MAX_RETRIES`.
- `REQUIRE_AUTH` and `REQUIRE_MFA` control protected access and AAL2 enforcement; disabling auth is intended only for local development.
- Run locally with `python -m gunicorn -c gunicorn.conf.py wsgi:application` (or `npm run dev`).
- Run tests with `python -m pytest` (or `npm test`).

## Known implementation notes

- API keys are stored as plaintext in `api_keys.key_text`; the service-role key must never be exposed to the browser.
- Gemini is called even when no deterministic rules match. Gemini failures are surfaced as HTTP 503 for affected screening requests.
- The `app/services/store.py` persistence helpers generally return empty/`None` values when Supabase is unavailable or a query fails; dashboard statistics also use zero/empty values as a fallback.
- Static FX conversion rates and the high-risk jurisdiction set are MVP configuration and should be reviewed for production use.
- The sanctions loader reads the configured local XML filenames from the process working directory.

## Checkpoint scope

This update replaces the stale Phase 2-only status with a snapshot of the implemented application and marks Phase 4 complete. Only `CONTEXT.md` is changed by this checkpoint. No tests were run because this is a documentation-only update.
