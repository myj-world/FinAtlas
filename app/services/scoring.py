from typing import Any, Dict, List, Optional

from app.config import (
    FX_RATES_TO_USD,
    HIGH_RISK_JURISDICTIONS,
    LARGE_TX_THRESHOLD_USD,
    THRESHOLD_HIGH,
    THRESHOLD_MEDIUM,
    WEIGHT_HIGH_RISK_JURISDICTION,
    WEIGHT_LARGE_TRANSACTION,
    WEIGHT_SANCTIONS_HIT,
)
from app.services.gemini import GeminiError, get_gemini_client
from app.services.sanctions import sanctions_repo
from app.services.store import persist_screening


def screen_transaction(transaction: dict, user_token: Optional[str] = None) -> Dict[str, Any]:
    tx = _clean_transaction(transaction)
    hits = _find_sanctions_hits(tx)
    rules: List[Dict[str, Any]] = []
    score = 0.0

    if hits:
        score = _add_rule(rules, score, "sanctions_hit", WEIGHT_SANCTIONS_HIT)

    if _is_large_transaction(tx):
        score = _add_rule(rules, score, "large_transaction", WEIGHT_LARGE_TRANSACTION)

    if _is_high_risk_jurisdiction(tx):
        score = _add_rule(rules, score, "high_risk_jurisdiction", WEIGHT_HIGH_RISK_JURISDICTION)

    deterministic_score = round(min(score, 1.0), 3)
    gemini_result = None
    final_score = deterministic_score

    # Gemini reviews any transaction that matched at least one deterministic rule.
    if rules:
        gemini_result = get_gemini_client().review(tx, deterministic_score, rules, hits)
        final_score = round(float(gemini_result["updated_risk_score"]), 3)

    classification = classify_score(final_score)

    result = {
        "transaction_id": tx.get("transactionId"),
        "deterministic_score": deterministic_score,
        "gemini_reviewed": rules is not None and bool(rules),
        "gemini_result": gemini_result,
        "final_score": final_score,
        "classification": classification,
        "sanctions_hits": hits,
        "rules": rules,
    }

    persist_screening(
        tx,
        deterministic_score,
        gemini_result,
        final_score,
        classification,
        user_token=user_token,
        sanctions_hits=hits,
        rules=rules,
    )
    return result


def _clean_transaction(tx: dict) -> dict:
    cleaned = {}
    for key, value in (tx or {}).items():
        if isinstance(value, float) and value != value:  # NaN from pandas
            cleaned[key] = None
        else:
            cleaned[key] = value
    return cleaned


def _find_sanctions_hits(tx: dict) -> List[Dict[str, str]]:
    hits = []
    for field in ("senderName", "receiverName"):
        name = tx.get(field)
        for match in sanctions_repo.match(name):
            hits.append({"field": field, **match})
    return hits


def _is_large_transaction(tx: dict) -> bool:
    try:
        amount = float(tx.get("amount", 0))
    except (TypeError, ValueError):
        return False
    currency = str(tx.get("currency", "USD")).upper()
    rate = FX_RATES_TO_USD.get(currency, 1.0)
    usd_equivalent = amount * rate
    return usd_equivalent > LARGE_TX_THRESHOLD_USD


def _is_high_risk_jurisdiction(tx: dict) -> bool:
    for field in ("senderCountry", "receiverCountry"):
        country = str(tx.get(field, "")).upper()
        if country in HIGH_RISK_JURISDICTIONS:
            return True
    return False


def _add_rule(rules: List[Dict[str, Any]], current_score: float, rule_name: str, weight: float) -> float:
    new_score = min(current_score + weight, 1.0)
    rules.append(
        {
            "rule": rule_name,
            "weight": weight,
            "cumulative_score": round(new_score, 3),
        }
    )
    return new_score


def classify_score(score: float) -> str:
    if score > THRESHOLD_HIGH:
        return "Definite Match / High Risk"
    if score >= THRESHOLD_MEDIUM:
        return "Potential Match / Medium Risk"
    return "No Match / Low Risk"
