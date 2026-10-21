"""Helpers for per-user API key management stored in Supabase (plaintext keys).

This module exposes create, rotate, fetch and revoke utilities. Keys are stored
in the api_keys table created by a migration. All operations run as the signed-
in user via the Supabase anon key and respect RLS.
"""

import os
import secrets
from typing import List, Optional, Dict

from app.services.auth import get_supabase_client


def _generate_key() -> str:
    return secrets.token_urlsafe(32)


def create_api_key(user_token: Optional[str]) -> Optional[Dict[str, any]]:
    client = get_supabase_client(user_token)
    if client is None:
        return None

    key = _generate_key()
    data = {"key_text": key}
    try:
        resp = client.table("api_keys").insert(data).execute()
        rows = getattr(resp, "data", None) or []
        return rows[0] if rows else None
    except Exception:
        return None


def fetch_api_keys(user_token: Optional[str]) -> List[Dict[str, any]]:
    client = get_supabase_client(user_token)
    if client is None:
        return []
    try:
        resp = client.table("api_keys").select("id, key_text, revoked, created_at, revoked_at").order("created_at", desc=True).execute()
        return getattr(resp, "data", None) or []
    except Exception:
        return []


def revoke_api_key(user_token: Optional[str], key_id: str) -> bool:
    client = get_supabase_client(user_token)
    if client is None:
        return False
    try:
        client.table("api_keys").update({"revoked": True, "revoked_at": "now()"}).eq("id", key_id).execute()
        return True
    except Exception:
        return False


def rotate_api_key(user_token: Optional[str], key_id: str) -> Optional[Dict[str, any]]:
    # Revoke the old key and create a new one atomically where possible.
    client = get_supabase_client(user_token)
    if client is None:
        return None
    try:
        # Revoke
        client.table("api_keys").update({"revoked": True, "revoked_at": "now()"}).eq("id", key_id).execute()
        # Create new
        new_key = _generate_key()
        resp = client.table("api_keys").insert({"key_text": new_key}).execute()
        rows = getattr(resp, "data", None) or []
        return rows[0] if rows else None
    except Exception:
        return None
