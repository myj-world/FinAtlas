# FinAtlas — AI-Powered AML System

## 1. Overview

**Team:** FinAtlas  
**Project:** FinAtlas  
**Pitch:** AI-powered money laundering detection for banks and businesses.

FinAtlas is an AI-powered anti-money laundering (AML) screening platform that combines deterministic transaction screening with contextual AI analysis through the Gemini REST API.

The platform is designed to help banks and businesses analyse large volumes of financial transactions, identify potentially suspicious activity, screen against sanctions lists, and prioritise transactions for further investigation.

FinAtlas uses a deterministic scoring engine to establish a preliminary risk score, which Gemini then evaluates to determine whether unusual patterns warrant additional risk. The AI produces explanations for its assessments, helping investigators understand why a transaction was flagged.

The platform supports individual and batch screening, dashboard analytics, persistent screening records, case management, authenticated access, and programmatic API integration.

**Live application:** https://finatlas-wrin.onrender.com/

## 2. Problem

Traditional anti-money laundering systems often rely on static rules and matching techniques. Although these methods are useful for detecting known risk indicators, they can produce excessive false-positive alerts and overlook unfamiliar transaction patterns.

Financial institutions also face the challenge of reviewing large volumes of transactions without allowing suspicious activity to pass unnoticed.

FinAtlas addresses these challenges through a dual-engine approach:

- **Deterministic screening** establishes a consistent preliminary risk score based on sanctions matches, transaction amounts, and jurisdiction risk.
- **AI-powered analysis** independently evaluates the screening results, identifies unusual patterns, and determines whether additional risk should be assigned.
- **Human investigation** allows users to create cases for any transaction, examine supporting information, and make final decisions.

The objective is to use AI as an investigative screening agent that helps filter large transaction volumes and prioritise potential risks without removing the need for human oversight.

## 3. Core Features

- **Transaction ingestion:** Screen individual transactions or import multiple records using JSON or CSV.
- **Batch screening:** Process large transaction collections synchronously or asynchronously.
- **Sanctions screening:** Match names against locally maintained UN, EU, and OFAC sanctions lists.
- **Deterministic risk scoring:** Calculate a preliminary score using sanctions matches, transaction amounts, and high-risk jurisdictions.
- **AI-powered risk assessment:** Send the deterministic score and relevant transaction information to Gemini for contextual analysis.
- **Unusual-pattern detection:** Use Gemini's `unusual_pattern_detected` result to determine whether an additional risk adjustment is required.
- **Explainable findings:** Present AI reasoning, confidence, and false-positive assessments where returned by the model.
- **Combined risk scoring:** Combine the deterministic score with the AI-triggered adjustment, capped at 1.0.
- **Risk dashboard:** Display risk distributions, engine disagreements, recent screenings, and open case counts.
- **Manual investigation:** Allow users to create a case for any transaction, including transactions that the automated screening system does not flag.
- **Case management:** Create, retrieve, update, and delete investigation cases.
- **Persistent screening history:** Store and retrieve screening results across sessions.
- **Secure access:** Support authenticated accounts and multi-factor authentication.
- **API key management:** Create, copy, revoke, and rotate per-user API keys for programmatic access.

## 4. Technology Stack

- **Frontend:** HTML, CSS, vanilla JavaScript
- **Application architecture:** Browser-based single-page application (SPA)
- **Backend:** Python and Flask
- **Data processing:** Pandas where applicable
- **Database:** Supabase PostgreSQL
- **Authentication:** Supabase Auth with multi-factor authentication (MFA)
- **AI:** Gemini REST API — required for the screening workflow
- **Sanctions data:** Local XML files for UN, EU, and OFAC lists
- **Foreign exchange:** Static exchange-rate table for transaction amount conversion
- **Version control:** Git and GitHub
- **Deployment:** Render

## 5. Data Sources and Planned Expansion

### 5.1 Current Data Sources

FinAtlas currently uses locally maintained XML files for sanctions screening:

- **UN Security Council Consolidated List:** Reference data for screening against UN sanctions designations.
- **European Union sanctions list:** Reference data for screening against EU sanctions designations.
- **OFAC sanctions list:** Reference data for screening against US sanctions designations.

The files are maintained locally as `unsc.xml`, `eu.xml`, and `ofac.xml`. The deterministic screening engine uses exact and normalized name matching.

The current jurisdiction risk component uses a hardcoded set of high-risk jurisdictions. Transaction amounts are converted to USD equivalents using a static foreign-exchange table.

### 5.2 Potential Supplementary Sources

Additional data sources may improve screening coverage and contextual risk assessment.

- **IBM AMLSim:** Synthetic transaction networks for testing and evaluating AML screening approaches — https://github.com/IBM/AMLSim
- **FATF high-risk and increased-monitoring lists:** Jurisdiction-level risk context — https://www.fatf-gafi.org/en/countries/black-and-grey-lists.html
- **UN Security Council Consolidated List:** Official sanctions designations and updates — https://main.un.org/securitycouncil/en/content/un-sc-consolidated-list
- **OFAC Sanctions List Service:** Official US sanctions data and downloadable list resources — https://ofac.treasury.gov/sanctions-list-service
- **European Union sanctions data:** Official EU sanctions information and relevant downloadable datasets.
- **Additional national sanctions lists:** Lists from other jurisdictions, subject to data availability, licensing, and implementation feasibility.
- **Synthetic and research datasets:** Additional AML datasets for testing transaction patterns, false-positive handling, and detection coverage.

### 5.3 Planned Data Improvements

Future versions may expand and improve the data infrastructure through:

- **Cloud-hosted sanctions data:** Retrieve current sanctions lists from official sources instead of relying exclusively on manually maintained local files.
- **Automatic updates:** Periodically refresh local copies from official sources, with update timestamps, validation, error handling, and a fallback to the last valid dataset.
- **Expanded sanctions coverage:** Integrate additional official international and national sanctions lists.
- **Dynamic jurisdiction risk:** Replace the hardcoded high-risk jurisdiction set with regularly updated data based on authoritative sources, while retaining transparent fallback behaviour.
- **Improved foreign-exchange data:** Replace static exchange rates with a maintained rate source and a clearly defined policy for unavailable or stale rates.
- **Additional AML datasets:** Incorporate suitable synthetic or research datasets to evaluate the screening engine and improve testing.

External data integrations and automatic updates are planned improvements rather than claims about the current implementation.

## 6. Dual-Engine Screening Methodology

### 6.1 Deterministic Screening Engine

The deterministic engine performs sanctions matching and calculates a preliminary risk score using configured indicators.

The current scoring system is:

| Risk indicator | Score adjustment |
|---|---:|
| Sanctions hit | +0.30 |
| Transaction exceeding $1,000 USD equivalent | +0.05 |
| High-risk jurisdiction | +0.10 |
| Gemini-based AI scoring system to detect unusual transactions | +0.55 |

The deterministic score is calculated by adding the applicable adjustments and capping the result at 1.0.

The engine currently uses exact and normalized sanctions-name matching, a static foreign-exchange table for USD-equivalent transaction amounts, and a hardcoded set of high-risk jurisdictions.

The resulting deterministic score provides a transparent, repeatable starting point for the AI assessment.

### 6.2 Required AI Analysis Engine

Gemini is a required component of the screening pipeline. Every transaction screening depends on a successful Gemini assessment; the system does not silently continue with a deterministic-only result when the AI service fails.

The deterministic score and relevant transaction information are sent to Gemini for contextual analysis.

Gemini evaluates the transaction and returns structured findings that can include:

- `unusual_pattern_detected`
- `updated_risk_score`
- `confidence`
- `reasoning`
- `false_positive_assessment`

The current risk-adjustment logic uses `unusual_pattern_detected` to determine whether the AI contributes an additional 0.55 to the risk score.

The AI's primary role is to determine whether the transaction warrants additional risk beyond the deterministic indicators, while providing explanations for its assessment.

If Gemini fails, the screening operation returns an error rather than treating the transaction as successfully screened. A Gemini failure currently raises `GeminiError` and results in HTTP 503 for affected endpoints.

### 6.3 Combined Risk Scoring

The final score combines the deterministic score and the AI-triggered adjustment.

This means the deterministic engine establishes the baseline, while Gemini can add a substantial risk adjustment when it identifies an unusual pattern.

For example, if the deterministic score is 0.40 and Gemini identifies a potential unusual pattern, the final score becomes 0.80. If Gemini does not identify an unusual pattern, the final score remains 0.40 under this scoring formula.

The score is capped at 1.0. It is a screening indicator, not a statistically calibrated probability of money laundering.

### 6.4 Risk Classification

The application currently uses the following thresholds:

| Risk level | Score threshold | Display label |
|---|---|---|
| High | Greater than 0.85 | Definite Match / High Risk |
| Medium | 0.50 to 0.85 inclusive | Potential Match / Medium Risk |
| Low | Below 0.50 | No Match / Low Risk |

These labels are application-defined classifications. In particular, a high score does not establish a definite identity match or prove criminal activity.

A sanctions hit, an unusual pattern, and an elevated combined score are indicators that may warrant further investigation.

### 6.5 AI-Assisted Investigation and Human Oversight

FinAtlas uses AI as an agent-like screening component to help filter large transaction collections, surface potential risks, and explain its findings.

The system is intended to:

- Prioritise transactions that warrant closer review.
- Identify unusual activity that may not be covered by predefined rules.
- Provide contextual explanations for risk assessments.
- Highlight potential false positives without automatically dismissing alerts.
- Reduce the manual effort involved in reviewing large transaction volumes.

Automated screening is not infallible. Users can create an investigation case for any transaction, even if it receives a low-risk classification or is not flagged by the AI.

Human reviewers retain control over investigation outcomes and consequential decisions.

## 7. Database Design

FinAtlas uses Supabase PostgreSQL to persist screening results, investigation cases, batch-processing information, and API key records.

### 7.1 Screenings

Stores transaction screening records and associated assessments, including supported transaction details, risk scores, screening outcomes, and AI findings.

### 7.2 Cases

Stores investigation cases created by users. Cases support retrieval and status or detail updates through the application's case-management API.

Users can create cases for any transaction, allowing manual review even when the automated screening result is low risk.

### 7.3 Batches

Stores batch-processing information needed to retrieve asynchronous screening status and results.

### 7.4 API Keys

Stores API key records and their management information, supporting creation, listing, revocation, and rotation.

### 7.5 Data Integrity

The system distinguishes transaction input data, deterministic screening results, AI-generated assessments, combined risk scores, and human investigation records.

This separation helps preserve the context behind a screening decision and supports subsequent investigation without treating automated conclusions as verified facts.

## 8. Security and Operational Integrity

FinAtlas incorporates authentication, protected credentials, controlled API access, and explicit error handling.

- **Authenticated access:** Supabase Auth manages user authentication.
- **MFA:** The application supports multi-factor authentication enforcement on the client and server.
- **Protected credentials:** The Gemini API key and Supabase service-role key are intended for server-side use only.
- **API key lifecycle:** Users can create, revoke, and rotate API keys.
- **Owner-scoped API access:** Bearer API keys are authenticated server-side and scoped to their owners.
- **Input validation:** Screening endpoints accept supported JSON transaction data, JSON batches, and CSV uploads.
- **AI dependency handling:** Gemini is mandatory; AI failures produce explicit errors rather than successful deterministic-only screening responses.
- **Explainability:** The system presents deterministic indicators and available AI reasoning to support review.
- **Manual review:** Users can create cases for any transaction, regardless of automated risk classification.

Sanctions matches may be false positives, jurisdiction indicators provide context rather than proof, and AI assessments can be incomplete or incorrect.

FinAtlas is a screening and investigation-support prototype, not a substitute for formal compliance procedures, independent verification, or professional review.

## 9. System Capabilities and Success Targets

The current implementation supports the following workflows.

### 9.1 Transaction Screening APIs

All public REST endpoints are under `/api`.

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/screen/single` | Screen a single JSON transaction and persist its result under the signed-in user's context. |
| POST | `/api/screen/batch` | Screen a JSON list or CSV upload, with synchronous and asynchronous processing options. |
| GET | `/api/screen/batch/<id>` | Retrieve batch status and results. |
| GET | `/api/screenings` | List screenings for the signed-in user. |
| GET | `/api/screenings/stats` | Retrieve risk distribution, disagreements, recent screenings, and open case count. |
| GET | `/api/screenings/<id>` | Retrieve a detailed screening with Gemini reasoning where available. |

Synchronous batch screening returns results inline. Asynchronous screening returns a `batch_id` for subsequent status and result retrieval.

All successful screening operations require the configured Gemini assessment. AI service failures are reported rather than silently bypassed.

### 9.2 Case Management APIs

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/cases` | Retrieve cases. |
| POST | `/api/cases` | Create a case. |
| PATCH | `/api/cases` | Update a case. |
| DELETE | `/api/cases` | Delete a case. |

Case management enables further investigation of transactions independently of their automated risk classifications.

### 9.3 API Key Management

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/api-keys` | List the current user's API keys. |
| POST | `/api/api-keys` | Create an API key. |
| POST | `/api/api-keys/<id>/revoke` | Revoke an API key. |
| POST | `/api/api-keys/<id>/rotate` | Revoke the old key and create a replacement. |

API keys support programmatic access through bearer-token authentication and are scoped to their owners.

### 9.4 Frontend and Dashboard

The frontend is a vanilla JavaScript single-page application implemented in:

- `app/templates/index.html`
- `app/static/js/app.js`

The interface retrieves safe configuration from the server and loads Supabase using the browser anonymous key.

The API page documents supported endpoints, provides copyable cURL examples, and includes per-user API key management with copy, rotation, and revocation controls.

### 9.5 Environment Configuration

The application uses environment variables documented in `.env.example`:

- `SUPABASE_URL`
- `SUPABASE_KEY` or `SUPABASE_ANON_KEY`
- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `GEMINI_API_KEY`
- `REQUIRE_AUTH`
- `REQUIRE_MFA`

Sensitive credentials must remain server-side. Frontend configuration should contain only values appropriate for public client-side use.

### 9.6 Deployment and Demonstration

The application is deployed at:

https://finatlas-wrin.onrender.com/

The intended demonstration workflow includes importing transactions, screening them through the deterministic and AI engines, inspecting explanations, comparing risk outcomes, reviewing dashboard statistics, and creating investigation cases.

The platform aims to demonstrate how AI-assisted screening can help prioritise large volumes of transactions while preserving the ability to investigate any individual result.

## 10. Future Improvements and Implementation Flexibility

FinAtlas is a hackathon project, and its implementation may evolve as development continues.

The current version demonstrates the core screening workflow. Future development can expand its detection coverage, improve data freshness, strengthen evaluation, and introduce more advanced AI capabilities.

### 10.1 Expanded and Automatically Updated Data Sources

- Integrate additional official national and international sanctions lists.
- Retrieve supported lists directly from official cloud-hosted sources.
- Automatically refresh sanctions data on a scheduled basis.
- Validate downloaded data before replacing the last known valid dataset.
- Track update timestamps and report stale or unavailable sources.
- Expand jurisdiction risk data using current authoritative publications.
- Replace the static foreign-exchange table with maintained exchange-rate data.
- Add supplementary transaction and entity-risk datasets where legally and technically appropriate.

### 10.2 Improved Deterministic Screening

- Improve name normalization to handle aliases, transliteration, spelling variations, and alternative name orders.
- Introduce configurable fuzzy matching with appropriate safeguards against excessive false positives.
- Improve entity matching using additional identifiers where available.
- Add configurable transaction-pattern rules for repeated transfers, rapid movement of funds, unusual transaction frequency, and related activity.
- Introduce time-window analysis and transaction-network relationships.
- Improve jurisdiction scoring and maintain transparent, configurable risk weights.
- Support versioned screening rules so investigators can understand which logic produced a historical result.
- Evaluate rule effectiveness using labelled or synthetic datasets.

These improvements would extend the current deterministic engine without removing the need for transparent, explainable screening results.

### 10.3 Advanced AI and Model Training

- Improve AI prompts and structured outputs for more consistent assessments.
- Evaluate false positives and missed-risk cases using curated test datasets.
- Compare AI findings against deterministic alerts and verified review outcomes.
- Develop labelled datasets from appropriate synthetic or authorised historical transaction data.
- Explore training or fine-tuning a specialised AML model where suitable data, infrastructure, and model-training support are available.
- Consider hybrid approaches that combine a trained detection model with the current Gemini analysis workflow.
- Measure precision, recall, false-positive rates, and missed-risk rates against labelled evaluation data.
- Monitor model performance and periodically reassess its reliability.

Training a specialised model is a future possibility, not a current capability. It would require appropriate training data, evaluation procedures, and safeguards against overfitting and biased outcomes.

### 10.4 Investigation and Operational Improvements

- Expand case management with evidence attachments, investigation notes, review histories, and configurable statuses.
- Improve batch-processing observability and recovery from transient service failures.
- Add monitoring for AI availability, response quality, latency, and cost.
- Introduce configurable risk policies for different institutions and use cases.
- Provide more detailed audit records for screening and investigation decisions.

### 10.5 Scope and Limitations

The current implementation uses local sanctions XML files, a static foreign-exchange table, a hardcoded high-risk jurisdiction set, deterministic scoring, and mandatory hosted Gemini analysis.

Cloud-based data retrieval, scheduled updates, expanded sanctions coverage, advanced deterministic algorithms, and specialised model training are proposed future improvements.

Risk scores are application-defined screening indicators, not calibrated probabilities of criminal activity. AI findings and sanctions matches require verification, and human reviewers retain responsibility for final investigation decisions.

FinAtlas aims to demonstrate how deterministic financial screening and AI-assisted analysis can work together to make AML investigations more scalable, explainable, and effective.
