import json
import os
import time
from typing import Any, Dict

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.config import GEMINI_API_URL, GEMINI_TIMEOUT_SECONDS, GEMINI_MAX_RETRIES
from app.services.prompts import build_screening_prompt


class GeminiError(Exception):
    """Raised when the Gemini REST API cannot produce a valid response."""

    pass


class GeminiClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        retries = Retry(
            total=GEMINI_MAX_RETRIES,
            backoff_factor=1.0,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST"],
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retries))

    def review(self, transaction: dict, deterministic_score: float, rules: list, hits: list) -> Dict[str, Any]:
        prompt = build_screening_prompt(transaction, deterministic_score, rules, hits)
        url = f"{GEMINI_API_URL}?key={self.api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.0,
                "responseMimeType": "application/json",
            },
        }

        last_error = None
        for attempt in range(GEMINI_MAX_RETRIES + 1):
            try:
                response = self.session.post(
                    url, json=payload, timeout=GEMINI_TIMEOUT_SECONDS
                )
                response.raise_for_status()
                return _parse_gemini_response(response.json())
            except requests.Timeout as exc:
                last_error = f"Gemini request timed out (attempt {attempt + 1})"
            except requests.RequestException as exc:
                last_error = f"Gemini request failed: {exc}"
            except GeminiError as exc:
                raise
            except Exception as exc:
                last_error = f"Unexpected Gemini error: {exc}"

            if attempt < GEMINI_MAX_RETRIES:
                time.sleep(2 ** attempt)

        raise GeminiError(last_error or "Gemini review failed")


def _parse_gemini_response(payload: dict) -> Dict[str, Any]:
    try:
        text = payload["candidates"][0]["content"]["parts"][0]["text"]
        parsed = json.loads(text)
    except (KeyError, IndexError, json.JSONDecodeError) as exc:
        raise GeminiError(f"Gemini returned unparseable output: {exc}")

    required_keys = {
        "updated_risk_score",
        "unusual_pattern_detected",
        "confidence",
        "reasoning",
        "false_positive_assessment",
    }
    missing = required_keys - set(parsed.keys())
    if missing:
        raise GeminiError(f"Gemini response missing keys: {missing}")

    unusual_pattern_detected = parsed["unusual_pattern_detected"]
    if not isinstance(unusual_pattern_detected, bool):
        raise GeminiError("Gemini returned a non-boolean unusual_pattern_detected")

    score = float(parsed["updated_risk_score"])
    confidence = float(parsed["confidence"])
    if not (0.0 <= score <= 1.0) or not (0.0 <= confidence <= 1.0):
        raise GeminiError("Gemini returned score or confidence outside 0.0-1.0")

    return {
        "updated_risk_score": round(score, 3),
        "unusual_pattern_detected": unusual_pattern_detected,
        "confidence": round(confidence, 3),
        "reasoning": str(parsed["reasoning"]),
        "false_positive_assessment": str(parsed["false_positive_assessment"]),
    }


def get_gemini_client() -> GeminiClient:
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise GeminiError("GEMINI_API_KEY is not configured")
    return GeminiClient(key)
