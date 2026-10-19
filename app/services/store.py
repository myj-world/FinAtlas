import json
import os
from typing import Any, Dict, Optional

from supabase import create_client


def _get_supabase_client(user_token: Optional[str] = None):
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        return None

    client = create_client(url, key)
    if user_token:
        client.auth.set_session(user_token, "")
    return client


def persist_screening(
    transaction: dict,
    deterministic_score: float,
    gemini_result: Optional[Dict[str, Any]],
    final_score: float,
    classification: str,
    user_token: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Persist a screening result under the signed-in user's RLS context.

    If Supabase is not configured or no user token is provided, persistence is
    skipped without raising an error so the API remains usable during setup.
    """
    client = _get_supabase_client(user_token)
    if not client:
        return None

    try:
        data = {
            "transaction_id": transaction.get("transactionId"),
            "transaction_data": json.loads(json.dumps(transaction, default=str)),
            "deterministic_score": deterministic_score,
            "gemini_result": gemini_result,
            "final_score": final_score,
            "classification": classification,
        }
        response = client.table("screenings").insert(data).execute()
        return getattr(response, "data", None)
    except Exception:
        # Phase 1: do not let persistence failures block the screening response.
        return None
