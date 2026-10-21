# FinAtlas — AI-Powered AML System

**AI-powered money laundering detection and sanctions screening for banks and investigators.**

FinAtlas combines deterministic sanctions list matching, rule-based risk scoring, and Gemini AI analysis to surface suspicious transactions, provide human-friendly explanations, and let investigators manage cases.

Live app: https://finatlas-wrin.onrender.com/


Features
- Single-transaction and batch screening (CSV or JSON) via REST API and the web UI.
- Deterministic sanctions screening against local UNSC, EU and OFAC XML files.
- Rule-based scoring with configurable weights and Gemini verification for unusual-pattern detection.
- Supabase persistence with per-user row-level security for screenings, batches and cases.
- Supabase Auth integration with optional MFA enforcement (AAL2) for investigator accounts.
- Per-user API keys stored in Supabase (plaintext), with support for multiple active keys and rotation/revoke.

Open FinAtlas at https://finatlas-wrin.onrender.com/.

Notes on authentication and MFA
- New users receive a confirmation email after signup. Click the link in the email to complete confirmation; the frontend exchanges the confirmation `code` for a session and prompts to set up TOTP MFA.
- REQUIRE_AUTH and REQUIRE_MFA environment variables control whether the app enforces authentication and MFA. Use `REQUIRE_AUTH=false` for local development only.

API
- POST /api/screen/single — screen one transaction (requires auth unless disabled).
- POST /api/screen/batch — screen a JSON list or upload CSV; add `?async=true` to queue a background job.
- GET /api/screen/batch/<id> — poll status of background batch jobs.
- GET /api/screenings — list your screenings.
- GET /api/screenings/stats — dashboard statistics.
- GET /api/screenings/<id> — screening detail including Gemini reasoning.
- Cases API: GET/POST/PATCH/DELETE /api/cases
- API Keys: GET/POST /api/api-keys, POST /api/api-keys/<id>/revoke, POST /api/api-keys/<id>/rotate
- Protected API endpoints accept either a Supabase access token or an active API key in `Authorization: Bearer <token>`.

Testing
Run the test suite with:
```
python -m pytest
```

License
MIT

### Developed for NED × DevMarketplace Hackathon (19th-22nd October, 2026)
