"""Authentication helpers for Supabase Auth and MFA enforcement."""

import base64
import json
import os
from typing import Any, Dict, Optional, Tuple

from supabase import Client, create_client


def _decode_jwt_payload(token: str) -> Dict[str, Any]:
    """Decode a JWT payload without verifying the signature.

    The signature is verified by Supabase Postgres RLS when the token is used
    with the Supabase client, so unverified decoding here is only used for
    application-level claim checks such as the MFA assurance level.
    """
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
    """Configure a Supabase client so that DB calls are executed as the user.

    This sets the Authorization header used by PostgREST so that Row Level
    Security policies see auth.uid() == the token's user.
    """
    # Modern postgrest-py clients expose an auth() helper.
    try:
        if hasattr(client, "postgrest") and callable(getattr(client.postgrest, "auth", None)):
            client.postgrest.auth(token)
    except Exception:
        pass

    # Fallback / additional global header.
    try:
        if hasattr(client, "options") and hasattr(client.options, "global"):
            client.options.global.headers["Authorization"] = f"Bearer {token}"
    except Exception:
        pass


def get_supabase_client(user_token: Optional[str] = None) -> Optional[Client]:
    """Return a Supabase client configured with the anon key and optional user JWT."""
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
        # Some versions of gotrue-py do not accept a jwt keyword; fall back to
        # setting the session and reading the current user.
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
    return aal == "aal2", aal


def mfa_required() -> bool:
    """Return whether the environment requires MFA for investigator endpoints."""
    return os.getenv("REQUIRE_MFA", "true").lower() in ("1", "true", "yes")


def auth_required() -> bool:
    """Return whether authenticated access is required for protected endpoints."""
    return os.getenv("REQUIRE_AUTH", "true").lower() in ("1", "true", "yes")


def get_auth_context(user_token: Optional[str]) -> Dict[str, Any]:
    """Resolve the user context from a Bearer token.

    Returns a dict with client, user, mfa_ok, and error. If Supabase is not
    configured, the user is treated as anonymous and endpoints that do not
    require auth can still function.
    """
    if auth_required() and not user_token:
        return {
            "client": None,
            "user": None,
            "mfa_ok": False,
            "error": "Authorization required",
        }

    client = get_supabase_client(user_token)
    if client is None:
        return {
            "client": None,
            "user": None,
            "mfa_ok": False,
            "error": "Supabase is not configured",
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
        mfa_ok, _ = check_mfa_level(user_token)
        if not mfa_ok:
            return {
                "client": client,
                "user": user,
                "mfa_ok": False,
                "error": "Multi-factor authentication required (AAL2)",
            }

    return {
        "client": client,
        "user": user,
        "mfa_ok": True,
        "error": None,
    }
