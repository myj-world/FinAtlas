"""Authentication helpers for Supabase Auth and MFA enforcement."""

import base64
import json
import os
from typing import Any, Dict, Optional, Tuple

from supabase import Client, create_client


def _decode_jwt_payload(token: str) -> Dict[str, Any]:
    """Decode a JWT payload without verifying the signature."""
    parts = token.split(".")
    if len(parts) != 3:
        return {}
    payload = parts[1]
    padding = 4 - len(payload) % 4
    if padding != 4:
        payload += "=" * padding
    try:
        decoded = base64.urlsafe_b64decode(payload)
        return json.loads(decoded)
    except Exception:
        return {}


def _apply_user_token(client: Client, token: str) -> None:
    try:
        if hasattr(client, "postgrest") and callable(getattr(client.postgrest, "auth", None)):
            client.postgrest.auth(token)
    except Exception:
        pass

    try:
        options = getattr(client, "options", None)
        global_options = getattr(options, "global", None)
        headers = getattr(global_options, "headers", None)
        if headers is not None:
            headers["Authorization"] = f"Bearer {token}"
    except Exception:
        pass


def _get_service_role_client() -> Optional[Client]:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        return None
    try:
        return create_client(url, key)
    except Exception:
        return None


def get_api_key_user_id(api_key: Optional[str]) -> Optional[str]:
    """Return the owner of an active API key, if the service role is configured."""
    if not api_key or api_key.count(".") == 2:
        return None
    client = _get_service_role_client()
    if client is None:
        return None
    try:
        response = (
            client.table("api_keys")
            .select("user_id")
            .eq("key_text", api_key)
            .eq("revoked", False)
            .maybe_single()
            .execute()
        )
        row = getattr(response, "data", None)
        return row.get("user_id") if row else None
    except Exception:
        return None


def get_client_api_key_user_id(client: Optional[Client]) -> Optional[str]:
    if client is None:
        return None
    user_id = getattr(client, "_finatlas_api_key_user_id", None)
    return user_id if isinstance(user_id, str) else None


def get_supabase_client(user_token: Optional[str] = None) -> Optional[Client]:
    """Return a user JWT client or a service client for a valid API key."""
    api_key_user_id = get_api_key_user_id(user_token)
    if api_key_user_id:
        client = _get_service_role_client()
        if client is not None:
            setattr(client, "_finatlas_api_key_user_id", api_key_user_id)
        return client

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    if not url or not key:
        return None

    try:
        client = create_client(url, key)
    except Exception:
        return None

    if user_token:
        _apply_user_token(client, user_token)
    return client


def get_current_user(client: Client, jwt: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Fetch the Supabase user associated with the supplied JWT."""
    response = None
    try:
        response = client.auth.get_user(jwt=jwt) if jwt else client.auth.get_user()
    except Exception:
        if jwt:
            try:
                client.auth.set_session(jwt, "")
                response = client.auth.get_user()
            except Exception:
                response = None

    user = getattr(response, "user", None)
    if user:
        return {
            "id": getattr(user, "id", None),
            "email": getattr(user, "email", None),
            "role": getattr(user, "role", "authenticated"),
        }
    return None


def check_mfa_level(user_token: str) -> Tuple[bool, Optional[str]]:
    """Return (is_aal2, assurance_level) for the supplied access token."""
    payload = _decode_jwt_payload(user_token)
    aal = payload.get("aal")
    if aal is None:
        return False, None
    aal = str(aal).lower()
    return aal == "aal2", aal


def mfa_required() -> bool:
    """Return whether the environment requires MFA for investigator endpoints."""
    return os.getenv("REQUIRE_MFA", "true").lower() in ("1", "true", "yes")


def auth_required() -> bool:
    """Return whether authenticated access is required for protected endpoints."""
    return os.getenv("REQUIRE_AUTH", "true").lower() in ("1", "true", "yes")


def get_auth_context(user_token: Optional[str]) -> Dict[str, Any]:
    """Resolve the user context from a Bearer token."""
    if auth_required() and not user_token:
        return {
            "client": None,
            "user": None,
            "mfa_ok": False,
            "error": "Authorization required",
        }

    if not auth_required() and not user_token:
        return {
            "client": get_supabase_client(),
            "user": None,
            "mfa_ok": True,
            "error": None,
        }

    client = get_supabase_client(user_token)
    if client is None:
        return {
            "client": None,
            "user": None,
            "mfa_ok": False,
            "error": "Supabase is not configured",
        }

    api_key_user_id = get_client_api_key_user_id(client)
    if api_key_user_id:
        return {
            "client": client,
            "user": {"id": api_key_user_id, "role": "authenticated"},
            "mfa_ok": True,
            "error": None,
            "api_key": True,
        }

    if not auth_required():
        return {
            "client": client,
            "user": None,
            "mfa_ok": True,
            "error": None,
        }

    user = get_current_user(client, jwt=user_token)
    if user is None:
        return {
            "client": client,
            "user": None,
            "mfa_ok": False,
            "error": "Invalid or expired token",
        }

    if mfa_required():
        mfa_ok, aal = check_mfa_level(user_token)
        if not mfa_ok:
            return {
                "client": client,
                "user": user,
                "mfa_ok": False,
                "error": "Multi-factor authentication required (AAL2)",
                "aal": aal,
            }

    return {
        "client": client,
        "user": user,
        "mfa_ok": True,
        "error": None,
    }
