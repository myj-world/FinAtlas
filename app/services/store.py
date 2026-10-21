"""Supabase persistence for screenings, cases, batch jobs and dashboard stats."""

import json
from typing import Any, Dict, List, Optional

from app.services.auth import get_supabase_client


def _safe_json(value: Any) -> Any:
    """Return a JSON-serialisable copy of a value."""
    return json.loads(json.dumps(value, default=str))


def _insert(client, table: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    try:
        response = client.table(table).insert(data).execute()
        rows = getattr(response, "data", None)
        return rows[0] if rows else None
    except Exception:
        return None


def persist_screening(
    transaction: dict,
    deterministic_score: float,
    gemini_result: Optional[Dict[str, Any]],
    final_score: float,
    classification: str,
    user_token: Optional[str] = None,
    sanctions_hits: Optional[List[Dict[str, Any]]] = None,
    rules: Optional[List[Dict[str, Any]]] = None,
) -> Optional[Dict[str, Any]]:
    """Persist a screening result under the signed-in user's RLS context."""
    client = get_supabase_client(user_token)
    if not client:
        return None

    data = {
        "transaction_id": transaction.get("transactionId"),
        "transaction_data": _safe_json(transaction),
        "deterministic_score": deterministic_score,
        "gemini_result": _safe_json(gemini_result) if gemini_result else None,
        "final_score": final_score,
        "classification": classification,
        "sanctions_hits": _safe_json(sanctions_hits or []),
        "rules": _safe_json(rules or []),
    }
    return _insert(client, "screenings", data)


def persist_batch(
    user_token: Optional[str],
    total: int,
) -> Optional[str]:
    """Create a pending batch job and return its id."""
    client = get_supabase_client(user_token)
    if not client:
        return None

    data = {
        "status": "pending",
        "total": total,
        "processed": 0,
        "succeeded": 0,
        "failed": 0,
        "results": [],
    }
    row = _insert(client, "batches", data)
    return row.get("id") if row else None


def fetch_batches(
    user_token: str,
    limit: int = 50,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    client = get_supabase_client(user_token)
    if not client:
        return []
    try:
        response = (
            client.table("batches")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .offset(offset)
            .execute()
        )
        return getattr(response, "data", []) or []
    except Exception:
        return []


def fetch_batch(user_token: str, batch_id: str) -> Optional[Dict[str, Any]]:
    client = get_supabase_client(user_token)
    if not client:
        return None
    try:
        response = client.table("batches").select("*").eq("id", batch_id).single().execute()
        return getattr(response, "data", None)
    except Exception:
        return None


def fetch_screenings(
    user_token: str,
    limit: int = 50,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    client = get_supabase_client(user_token)
    if not client:
        return []
    try:
        response = (
            client.table("screenings")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .offset(offset)
            .execute()
        )
        return getattr(response, "data", []) or []
    except Exception:
        return []


def fetch_screening(user_token: str, screening_id: str) -> Optional[Dict[str, Any]]:
    client = get_supabase_client(user_token)
    if not client:
        return None
    try:
        response = (
            client.table("screenings")
            .select("*")
            .eq("id", screening_id)
            .single()
            .execute()
        )
        return getattr(response, "data", None)
    except Exception:
        return None


def update_screening_case_id(
    user_token: str,
    screening_id: str,
    case_id: str,
) -> bool:
    client = get_supabase_client(user_token)
    if not client:
        return False
    try:
        # Screening rows do not currently store a case_id; this helper is a no-op
        # placeholder in case the schema is extended later.
        return True
    except Exception:
        return False


def persist_case(
    user_token: str,
    screening_id: str,
    status: str = "open",
    notes: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    client = get_supabase_client(user_token)
    if not client:
        return None

    data: Dict[str, Any] = {
        "screening_id": screening_id,
        "status": status,
        "notes": notes,
    }
    return _insert(client, "cases", data)


def fetch_cases(
    user_token: str,
    limit: int = 50,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    client = get_supabase_client(user_token)
    if not client:
        return []
    try:
        response = (
            client.table("cases")
            .select("*, screenings!inner(transaction_id, final_score, classification)")
            .order("created_at", desc=True)
            .limit(limit)
            .offset(offset)
            .execute()
        )
        return getattr(response, "data", []) or []
    except Exception:
        # Fallback without the join if the inner join fails for any reason.
        try:
            response = (
                client.table("cases")
                .select("*")
                .order("created_at", desc=True)
                .limit(limit)
                .offset(offset)
                .execute()
            )
            return getattr(response, "data", []) or []
        except Exception:
            return []


def fetch_case(user_token: str, case_id: str) -> Optional[Dict[str, Any]]:
    client = get_supabase_client(user_token)
    if not client:
        return None
    try:
        response = client.table("cases").select("*").eq("id", case_id).single().execute()
        return getattr(response, "data", None)
    except Exception:
        return None


def update_case(
    user_token: str,
    case_id: str,
    status: Optional[str] = None,
    notes: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    client = get_supabase_client(user_token)
    if not client:
        return None

    data: Dict[str, Any] = {}
    if status is not None:
        data["status"] = status
    if notes is not None:
        data["notes"] = notes
    if not data:
        return fetch_case(user_token, case_id)

    try:
        response = (
            client.table("cases").update(data).eq("id", case_id).execute()
        )
        rows = getattr(response, "data", None)
        return rows[0] if rows else None
    except Exception:
        return None


def delete_case(user_token: str, case_id: str) -> bool:
    client = get_supabase_client(user_token)
    if not client:
        return False
    try:
        client.table("cases").delete().eq("id", case_id).execute()
        return True
    except Exception:
        return False


def fetch_dashboard_stats(user_token: str) -> Dict[str, Any>:
    """Return aggregate statistics for the investigator dashboard."""
    client = get_supabase_client(user_token)
    if not client:
        return {
            "total_screenings": 0,
            "risk_distribution": {},
            "alert_disagreements": 0,
            "recent_screenings": [],
            "open_cases": 0,
        }

    try:
        all_screenings = (
            client.table("screenings")
            .select("id, deterministic_score, final_score, classification, transaction_id, created_at, gemini_result")
            .order("created_at", desc=True)
            .execute()
        )
        screenings = getattr(all_screenings, "data", []) or []
    except Exception:
        screenings = []

    distribution: Dict[str, int] = {}
    disagreements = 0
    disagreement_rows: List[Dict[str, Any]] = []
    for row in screenings:
        classification = row.get("classification") or "Unknown"
        distribution[classification] = distribution.get(classification, 0) + 1

        det = float(row.get("deterministic_score") or 0)
        final = float(row.get("final_score") or 0)
        det_class = _classify(det)
        final_class = _classify(final)
        if det_class != final_class:
            disagreements += 1
            disagreement_rows.append(row)

    open_cases = 0
    try:
        cases_resp = client.table("cases").select("id", count="exact").eq("status", "open").execute()
        open_cases = getattr(cases_resp, "count", 0) or 0
    except Exception:
        pass

    return {
        "total_screenings": len(screenings),
        "risk_distribution": distribution,
        "alert_disagreements": disagreements,
        "disagreement_screenings": disagreement_rows[:10],
        "recent_screenings": screenings[:5],
        "open_cases": open_cases,
    }


def _classify(score: float) -> str:
    from app.config import THRESHOLD_HIGH, THRESHOLD_MEDIUM

    if score > THRESHOLD_HIGH:
        return "Definite Match / High Risk"
    if score >= THRESHOLD_MEDIUM:
        return "Potential Match / Medium Risk"
    return "No Match / Low Risk"

    """Return aggregate statistics for the investigator dashboard."""
    client = get_supabase_client(user_token)
    if not client:
        return {
            "total_screenings": 0,
            "risk_distribution": {},
            "alert_disagreements": 0,
            "recent_screenings": [],
            "open_cases": 0,
        }

    try:
        all_screenings = (
            client.table("screenings")
            .select("id, deterministic_score, final_score, classification, transaction_id, created_at, gemini_result")
            .order("created_at", desc=True)
            .execute()
        )
        screenings = getattr(all_screenings, "data", []) or []
    except Exception:
        screenings = []

    distribution: Dict[str, int] = {}
    disagreements = 0
    disagreement_rows: List[Dict[str, Any]] = []
    for row in screenings:
        classification = row.get("classification") or "Unknown"
        distribution[classification] = distribution.get(classification, 0) + 1

        det = float(row.get("deterministic_score") or 0)
        final = float(row.get("final_score") or 0)
        det_class = _classify(det)
        final_class = _classify(final)
        if det_class != final_class:
            disagreements += 1
            disagreement_rows.append(row)

    open_cases = 0
    try:
        cases_resp = client.table("cases").select("id", count="exact").eq("status", "open").execute()
        open_cases = getattr(cases_resp, "count", 0) or 0
    except Exception:
        pass

    return {
        "total_screenings": len(screenings),
        "risk_distribution": distribution,
        "alert_disagreements": disagreements,
        "disagreement_screenings": disagreement_rows[:10],
        "recent_screenings": screenings[:5],
        "open_cases": open_cases,
    }


def _classify(score: float) -> str:
    from app.config import THRESHOLD_HIGH, THRESHOLD_MEDIUM

    if score > THRESHOLD_HIGH:
        return "Definite Match / High Risk"
    if score >= THRESHOLD_MEDIUM:
        return "Potential Match / Medium Risk"
    return "No Match / Low Risk"
