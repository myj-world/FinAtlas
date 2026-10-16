# FinAtlas — AI-Powered AML System

## 1. Overview

**Team:** FinAtlas  
**Project:** FinAtlas  
**Pitch:** AI-powered money laundering detection for banks and businesses.

FinAtlas is an AI-powered anti-money laundering (AML) platform that combines traditional transaction-monitoring rules with independent AI analysis. It identifies potentially suspicious financial activity, challenges false-positive alerts, and uncovers risks that conventional rule-based systems may overlook.

The platform simulates a modern AML investigation workflow, from transaction ingestion and risk assessment to AI-powered analysis, case review, and persistent investigation records.

## 2. Problem

Traditional AML systems depend heavily on predefined rules, which can generate excessive false-positive alerts while missing unfamiliar or complex transaction patterns.

FinAtlas addresses this challenge through a dual-engine approach: transparent rule-based screening identifies known risk indicators, while AI independently examines transaction behaviour, questions questionable alerts, and detects potential risks beyond predefined rules.

## 3. Core Features

- **Transaction ingestion:** Import transaction records through CSV files or use a sample dataset.
- **Rule-based screening:** Detect unusually large transfers, rapid transaction sequences, repeated transfers, and other supported suspicious patterns.
- **AI-powered detection:** Analyse both flagged and unflagged transactions to identify missed risks and challenge potential false positives.
- **Risk assessment:** Combine rule-based scores and AI findings into an explainable investigation view.
- **Investigation reports:** Present transaction evidence, risk indicators, possible legitimate explanations, uncertainty, and recommended investigative steps.
- **Monitoring dashboard:** Display risk distributions, suspicious patterns, alert disagreements, and investigation statuses.
- **Case management:** Save investigation reports, track review status, and retrieve historical cases.
- **Secure access:** Provide authenticated user accounts, multi-factor authentication, and user-isolated investigation records.

## 4. Technology Stack

- **Frontend:** HTML, CSS, JavaScript
- **Backend:** Python and Flask
- **Data processing:** Pandas
- **Database:** Supabase PostgreSQL
- **Authentication:** Supabase Auth with MFA
- **AI:** Hosted model API
- **Version control:** Git and GitHub

## 5. Potential Data Sources

The following sources are candidates for strengthening transaction analysis. Their suitability and integration feasibility will determine which are included.

- **IBM AMLSim:** Synthetic financial transaction networks and AML research data — https://github.com/IBM/AMLSim
- **UN Security Council Consolidated List:** Potential reference data for sanctions-name screening — https://main.un.org/securitycouncil/en/content/un-sc-consolidated-list
- **FATF high-risk and increased-monitoring lists:** Potential jurisdiction-level risk context — https://www.fatf-gafi.org/en/countries/black-and-grey-lists.html

A locally maintained synthetic dataset will support the core workflow independently of external data-source availability.

## 6. Dual-Engine AI Methodology

### Rule-Based Engine

A deterministic screening engine applies predefined transaction rules and assigns preliminary risk scores. Each triggered rule is recorded so investigators can understand the basis of an alert.

### AI Detection Engine

A hosted AI model independently reviews transaction data and available account activity. It identifies potentially suspicious patterns beyond predefined rules, evaluates whether existing alerts are adequately supported, and produces structured investigation findings.

### Combined Investigation

FinAtlas presents both engines' assessments, highlights disagreements, and prioritises transactions requiring further review. AI findings include supporting evidence, uncertainty, possible alternative explanations, and recommended next steps.

Risk scores and AI assessments represent indicators for investigation, not confirmed probabilities of criminal activity. Human reviewers retain control over case decisions.

## 7. Database Design

### Investigations

| Field | Purpose |
|---|---|
| `id` | Unique investigation identifier |
| `user_id` | Investigation owner |
| `transaction_reference` | Transaction or pattern reference |
| `transaction_data` | Relevant transaction details |
| `rule_risk_score` | Preliminary rule-based score |
| `triggered_rules` | Recorded rule findings |
| `ai_assessment` | AI findings and explanations |
| `review_status` | Pending, reviewed, or escalated |
| `created_at` | Investigation timestamp |

Structured findings may be stored as PostgreSQL JSONB fields. Supabase Row Level Security enforces ownership and prevents unauthorised access to investigation records.

## 8. Security and Operational Integrity

FinAtlas incorporates authenticated access, multi-factor authentication, user-level data isolation, input validation, and protected server-side AI credentials.

The system maintains a distinction between observed transaction data, rule-generated alerts, AI interpretations, and human review decisions. Potential sanctions matches and AI findings are treated as indicators requiring verification rather than conclusive evidence.

## 9. System Capabilities and Success Targets

FinAtlas provides an end-to-end AML investigation workflow with the following capabilities:

- **Secure access:** Users can register, sign in, and complete the supported multi-factor authentication flow.
- **Transaction monitoring:** Users can import transaction data and receive transparent rule-based risk assessments.
- **Independent AI detection:** The AI engine analyses both flagged and unflagged transactions using live hosted-model calls.
- **False-positive analysis:** The system identifies alerts that may warrant reconsideration without automatically dismissing them.
- **Missed-risk identification:** The system surfaces potentially suspicious activity that predefined rules do not flag.
- **Explainable investigations:** Each assessment presents relevant evidence, risk indicators, uncertainty, and suggested next steps.
- **Unified risk dashboard:** Users can compare engine findings, inspect alerts, and prioritise investigations.
- **Persistent case management:** Users can save, revisit, and update investigation records across sessions.
- **Data isolation:** Each authenticated user can access only their own saved investigations.
- **Deployed application:** The complete workflow is accessible through a browser-based application and suitable for a live demonstration.

The platform is designed to demonstrate how AI-enhanced transaction monitoring can improve investigative coverage while preserving transparency, secure data handling, and human oversight.

## 10. Implementation Flexibility

The proposed technology stack, features, and requirements represent the current project plan. Depending on the available development time, technical feasibility, and decisions made during the hackathon, implementation details, selected technologies, and feature scope may be adjusted while prioritising the platform's core objectives.
