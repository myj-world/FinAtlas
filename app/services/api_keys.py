"""Helpers for per-user API key management stored in Supabase (plaintext keys).

This module exposes create, rotate, fetch and revoke utilities. Keys are stored
in the api_keys table created by a migration. All operations run as the signed-
in user via the Supabase anon key and respect RLS.
"""

import secrets
from typing import Any, Dict, List, Optional

from app.services.auth import get_client_api_key_user_id, get_supabase_client


def _generate_key() -> str:
    return secrets.token_urlsafe(32)


def _scope_query(query, client):
    user_id = get_client_api_key_user_id(client)
    return query.eq("user_id", user_id) if user_id else query


def _owned_data(data: Dict[str, Any], client) -> Dict[str, Any]:
    user_id = get_client_api_key_user_id(client)
    if user_id:
        return {**data, "user_id": user_id}
    return data


def create_api_key(user_token: Optional[str]) -> Optional[Dict[str, Any]]:
    client = get_supabase_client(user_token)
    if client is None:
        return None

    key = _generate_key()
    data = {"key_text": key}
    try:
        resp = client.table("api_keys").insert(_owned_data(data, client)).execute()
        rows = getattr(resp, "data", None) or []
        return rows[0] if rows else None
    except Exception:
        return None


def fetch_api_keys(user_token: Optional[str]) -> List[Dict[str, Any]]:
    client = get_supabase_client(user_token)
    if client is None:
        return []
    try:
        query = client.table("api_keys").select(
            "id, key_text, revoked, created_at, revoked_at"
        ).order("created_at", desc=True)
        resp = _scope_query(query, client).execute()
        return getattr(resp, "data", None) or []
    except Exception:
        return []


def revoke_api_key(user_token: Optional[str], key_id: str) -> bool:
    client = get_supabase_client(user_token)
    if client is None:
        return False
    try:
        query = client.table("api_keys").update(
            {"revoked": True, "revoked_at": "now()"}
        ).eq("id", key_id)
        _scope_query(query, client).execute()
        return True
    except Exception:
        return False


def rotate_api_key(user_token: Optional[str], key_id: str) -> Optional[Dict[str, Any]]:
    # Revoke the old key and create a new one atomically where possible.
    client = get_supabase_client(user_token)
    if client is None:
        return None
    try:
        # Revoke
        query = client.table("api_keys").update(
            {"revoked": True, "revoked_at": "now()"}
        ).eq("id", key_id)
        _scope_query(query, client).execute()
        # Create new
        new_key = _generate_key()
        resp = client.table("api_keys").insert(
            _owned_data({"key_text": new_key}, client)
        ).execute()
        rows = getattr(resp, "data", None) or []
        return rows[0] if rows else None
    except Exception:
        return None
