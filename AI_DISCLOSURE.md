# AI Disclosure — FinAtlas

## AI-Assisted Development

FinAtlas is being developed with assistance from AI-powered development tools, specifically DevMarketplace. This tool assist with code generation, debugging, architecture design, documentation, and feature implementation.

All AI-generated code and suggestions are reviewed, tested, and adapted by the team as part of the development process.

## AI Within the Application

FinAtlas integrates the **Gemini REST API** into its core AML screening pipeline. The AI engine:
- Conducts contextual risk analysis on transaction data alongside deterministic sanctions list matching (UNSC, EU, OFAC).
- Evaluates potential false positives resulting from direct or fuzzy name matches.
- Generates structured risk reasoning and assigns a calibrated risk score (0.0 to 1.0).

AI-generated assessments serve as investigative indicators rather than definitive legal conclusions. Human review remains central to all final case decisions.

## Third-Party Data & Component Declarations

- **AI Model Provider:** Gemini REST API (Google)
- **Sanctions Reference Lists:** UNSC Consolidated List, EU Consolidated Sanctions List, OFAC Sanctions List
- **Database & Authentication:** Supabase (PostgreSQL with Row Level Security & Auth)
- **Backend Infrastructure:** Python & Flask
