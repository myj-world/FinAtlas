# FinAtlas — AI-Powered AML System (Updated)

This document captures the current implementation and public APIs for FinAtlas.

1) Screening pipeline
- Deterministic sanctions matching: exact/normalized matching against local XML files `unsc.xml`, `eu.xml`, `ofac.xml`.
- Deterministic rules apply additive weights and are capped at 1.0. Weights configured in `app/config.py`.
- Gemini REST API performs contextual verification and detects unusual transaction patterns. The Gemini result includes `updated_risk_score`, `unusual_pattern_detected`, `confidence`, `reasoning`, and `false_positive_assessment`.
- Final score uses Gemini's `updated_risk_score` when available; otherwise deterministic score is used.

2) Risk thresholds
- High: > 0.85  — Definite Match / High Risk
- Medium: >= 0.50 — Potential Match / Medium Risk
- Low: < 0.50 — No Match / Low Risk

3) Persistence & RLS
- Supabase tables: `screenings`, `cases`, `batches`, `api_keys`.
- Every table has row-level security enabled and policies restricting access to `auth.uid() = user_id`.

4) Public REST APIs (all under /api)
- POST /api/screen/single — body: JSON transaction. Returns screening result and persists it under the signed-in user's context.
- POST /api/screen/batch[?async=true] — body: JSON list or CSV file upload. Async returns immediately with a `batch_id` and processes rows in background; sync returns results inline.
- GET /api/screen/batch/<id> — return batch job status and results.
- GET /api/screenings — list screenings for the signed-in user.
- GET /api/screenings/stats — dashboard statistics: risk distribution, disagreements, recent screenings, and open case count.
- GET /api/screenings/<id> — detailed screening with Gemini reasoning.
- Cases CRUD: GET/POST/PATCH/DELETE /api/cases
- API keys: GET /api/api-keys, POST /api/api-keys to create, POST /api/api-keys/<id>/revoke to revoke, POST /api/api-keys/<id>/rotate to rotate (revokes old key and creates a new one).

5) Frontend
- Vanilla JS SPA in `app/templates/index.html` and `app/static/js/app.js`.
- The UI requests safe config from the server and loads Supabase via the browser anon key. MFA is enforced on the client and server.
- API page documents endpoints, includes copy buttons, and shows the per-user API keys with regenerate/revoke actions.

6) Environment variables (see .env.example)
- SUPABASE_URL, SUPABASE_KEY or SUPABASE_ANON_KEY
- VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY (front-end-safe)
- GEMINI_API_KEY (server-only)
- REQUIRE_AUTH (true/false)
- REQUIRE_MFA (true/false)

7) Limitations / Notes
- The current migration to add `api_keys` has been applied in `supabase/migrations/20261021071739_create_api_keys_table_v3.sql`.
- The Supabase service-role key is intentionally not used; all DB access goes through the anon key and RLS policies.
- Gemini failures raise a GeminiError and return 503 for affected endpoints.
