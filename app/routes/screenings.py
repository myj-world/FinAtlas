from flask import Blueprint, jsonify, request

from app.services.auth import get_auth_context
from app.services.store import fetch_dashboard_stats, fetch_screening, fetch_screenings
from app.utils import extract_bearer_token

bp = Blueprint("screenings", __name__, url_prefix="/api/screenings")


def _require_auth(token):
    ctx = get_auth_context(token)
    if ctx["error"]:
        return None, (jsonify({"error": ctx["error"]}), 401)
    return ctx, None


@bp.route("", methods=["GET"])
def list_screenings():
    token = extract_bearer_token(request.headers)
    ctx, error = _require_auth(token)
    if error:
        return error

    limit = request.args.get("limit", 50, type=int)
    offset = request.args.get("offset", 0, type=int)
    screenings = fetch_screenings(token, limit=limit, offset=offset)
    return jsonify({"count": len(screenings), "screenings": screenings})


@bp.route("/stats", methods=["GET"])
def stats():
    token = extract_bearer_token(request.headers)
    ctx, error = _require_auth(token)
    if error:
        return error

    dashboard_stats = fetch_dashboard_stats(token)
    return jsonify(dashboard_stats)


@bp.route("/<screening_id>", methods=["GET"])
def get_screening(screening_id):
    token = extract_bearer_token(request.headers)
    ctx, error = _require_auth(token)
    if error:
        return error

    screening = fetch_screening(token, screening_id)
    if screening is None:
        return jsonify({"error": "Screening not found"}), 404
    return jsonify(screening)
