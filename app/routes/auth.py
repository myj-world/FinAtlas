from flask import Blueprint, jsonify, request

from app.services.auth import check_mfa_level, get_auth_context, mfa_required
from app.utils import extract_bearer_token

bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@bp.route("/me", methods=["GET"])
def me():
    """Return the currently authenticated Supabase user and MFA status."""
    token = extract_bearer_token(request.headers)
    ctx = get_auth_context(token)

    if ctx["error"]:
        return jsonify({"error": ctx["error"]}), 401

    user = ctx["user"]
    mfa_ok = ctx["mfa_ok"]
    aal = None
    if token:
        _, aal = check_mfa_level(token)

    return jsonify(
        {
            "authenticated": user is not None,
            "user": user,
            "mfa": {"required": mfa_required(), "verified": mfa_ok, "aal": aal},
        }
    )
