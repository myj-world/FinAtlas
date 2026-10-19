# FinAtlas — AI-Powered AML System

## 1. Overview

**Project:** FinAtlas

**Pitch:** AI-powered anti-money laundering (AML) detection combining sanctions list matching, deterministic risk scoring, and Gemini AI analysis.

FinAtlas streamlines AML screening by processing transaction data through deterministic sanctions checks, rule-based risk scoring, and Gemini-powered risk analysis, delivering actionable insights via UI and REST APIs.

---

## 2. Data Model

Input data (CSV upload, sample dataset, or single-transaction manual entry) supports the following schema:

* `transactionId`, `transactionDate`, `transactionType`
* `amount`, `currency`
* **Sender:** `senderName`, `senderDOB`, `senderPlaceOfBirth`, `senderNationality`, `senderCountry`, `senderAccount`
* **Receiver:** `receiverName`, `receiverDOB`, `receiverPlaceOfBirth`, `receiverNationality`, `receiverCountry`, `receiverAccount`

---

## 3. AML Screening Pipeline & Risk Scoring

### Step 1: Direct Sanctions List Matching

First-line deterministic matching against global sanctions lists:

* **UNSC** Sanctions Consolidated List
* **EU** Consolidated Sanctions List
* **OFAC** Sanctions List

### Step 2: Deterministic Rule-Based Scoring

Initial cumulative risk score calculation (normalized to 1.0):

* **Direct Sanctions Match:** +0.50
* **Large Transaction (>$1,000 USD equivalent):** +0.20
* **High-Risk Jurisdiction (Sender/Receiver Country):** +0.15
* **Unusual Transaction Pattern:** +0.15

### Step 3: Gemini AI Verification & Contextual Analysis

Transactions are sent via **Gemini REST API** to verify potential false positives, evaluate context, and produce a final normalized risk score ($0.0 - 1.0$).

### Risk Classification Thresholds

* **$> 0.85$:** Definite Match / High Risk
* **$0.50 - 0.85$:** Potential Match / Medium Risk
* **$< 0.50$:** No Match / Low Risk

---

## 4. Core Features

* **Multi-Format Ingestion:** Bulk CSV dataset uploads, pre-loaded sample data, or single-transaction manual entry.
* **Hybrid AML Engine:** Combined sanctions list direct matching, heuristic rules, and Gemini AI verification.
* **Interactive Dashboard:** Display risk distributions, alert disagreements, and detailed risk explanations.
* **REST API Integration:** Programmatic endpoints for single or batch screening.
* **Case Management:** Persistent investigation tracking backed by Supabase with user isolation.

---

## 5. Technology Stack

* **Frontend:** HTML, CSS, JavaScript
* **Backend:** Python, Flask (REST APIs)
* **Data Processing:** Pandas
* **Database & Auth:** Supabase PostgreSQL & Supabase Auth (with MFA)
* **AI Engine:** Gemini REST API
* **Version Control:** Git & GitHub

---

## 6. System Architecture & API Endpoints

```
[ Frontend / API Client ] 
           │
           ▼
     [ Flask API ]
     ├── 1. Direct Sanctions Match (UNSC, EU, OFAC)
     ├── 2. Rule Risk Engine (Amount, Country, Patterns)
     └── 3. Gemini REST API (Verification & Deep Analysis)
           │
           ▼
[ Supabase PostgreSQL ] (Persisted Cases & Row-Level Security)

```

### Core API Endpoints

* `POST /api/screen/single` — Screen a single transaction object.
* `POST /api/screen/batch` — Ingest CSV/batch data for background processing.
