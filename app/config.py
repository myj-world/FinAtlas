import os

LARGE_TX_THRESHOLD_USD = 1_000.0

# Cumulative deterministic weights (Gemini decides the unusual-pattern component).
WEIGHT_SANCTIONS_HIT = 0.50
WEIGHT_LARGE_TRANSACTION = 0.20
WEIGHT_HIGH_RISK_JURISDICTION = 0.15

# Risk classification thresholds.
THRESHOLD_HIGH = 0.85
THRESHOLD_MEDIUM = 0.50

# Static conversion rates to USD for the MVP. Update as needed.
FX_RATES_TO_USD = {
    "USD": 1.0,
    "EUR": 1.08,
    "GBP": 1.27,
    "JPY": 0.0067,
    "CHF": 1.13,
    "CAD": 0.73,
    "AUD": 0.66,
    "CNY": 0.14,
}

# Example high-risk jurisdictions (FATF/AML watchlists). Configurable later.
HIGH_RISK_JURISDICTIONS = {
    "IR",  # Iran
    "KP",  # North Korea
    "MM",  # Myanmar
    "AF",  # Afghanistan
    "SY",  # Syria
    "BY",  # Belarus
    "RU",  # Russia
    "VE",  # Venezuela
}

SANCTIONS_FILES = {
    "UNSC": "unsc.xml",
    "EU": "eu.xml",
    "OFAC": "ofac.xml",
}

GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-1.5-flash:generateContent"
)
GEMINI_TIMEOUT_SECONDS = int(os.getenv("GEMINI_TIMEOUT_SECONDS", "15"))
GEMINI_MAX_RETRIES = int(os.getenv("GEMINI_MAX_RETRIES", "3"))
