from flask import Blueprint, jsonify, request

from app.services.auth import get_auth_context
from app.services.api_keys import create_api_key, fetch_api_keys, revoke_api_key, rotate_api_key
from app.utils import extract_bearer_token

bp = Blueprint("api_keys", __name__, url_prefix="/api/api-keys")


def _require_auth(token):
    ctx = get_auth_context(token)
    if ctx["error"]:
        return None, (jsonify({"error": ctx["error"]}), 401)
    return ctx, None


@bp.route("", methods=["GET"])
def list_keys():
    token = extract_bearer_token(request.headers)
    ctx, error = _require_auth(token)
    if error:
        return error

    keys = fetch_api_keys(token)
    # Do not include the full key_text in list responses in other contexts; the UI shows them.
    return jsonify({"count": len(keys), "keys": keys})


@bp.route("", methods=["POST"])
def create_key():
    token = extract_bearer_token(request.headers)
    ctx, error = _require_auth(token)
    if error:
        return error

    key = create_api_key(token)
    if key is None:
        return jsonify({"error": "Unable to create API key"}), 503
    return jsonify(key), 201


@bp.route("/<key_id>/revoke", methods=["POST"])
def revoke(key_id):
    token = extract_bearer_token(request.headers)
    ctx, error = _require_auth(token)
    if error:
        return error

    ok = revoke_api_key(token, key_id)
    if not ok:
        return jsonify({"error": "Unable to revoke API key"}), 404
    return jsonify({"revoked": True})


@bp.route("/<key_id>/rotate", methods=["POST"])
def rotate(key_id):
    token = extract_bearer_token(request.headers)
    ctx, error = _require_auth(token)
    if error:
        return error

    new = rotate_api_key(token, key_id)
    if new is None:
        return jsonify({"error": "Unable to rotate API key"}), 503
    return jsonify(new)
