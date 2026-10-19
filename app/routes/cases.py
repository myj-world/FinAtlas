from flask import Blueprint, jsonify, request

from app.services.auth import get_auth_context
from app.services.store import (
    delete_case,
    fetch_case,
    fetch_cases,
    persist_case,
    update_case,
)
from app.utils import extract_bearer_token

bp = Blueprint("cases", __name__, url_prefix="/api/cases")


def _get_user_token():
    return extract_bearer_token(request.headers)


def _require_auth(token):
    ctx = get_auth_context(token)
    if ctx["error"]:
        return None, (jsonify({"error": ctx["error"]}), 401)
    return ctx, None


@bp.route("", methods=["GET"])
def list_cases():
    token = _get_user_token()
    ctx, error = _require_auth(token)
    if error:
        return error

    limit = request.args.get("limit", 50, type=int)
    offset = request.args.get("offset", 0, type=int)
    cases = fetch_cases(token, limit=limit, offset=offset)
    return jsonify({"count": len(cases), "cases": cases})


@bp.route("", methods=["POST"])
def create_case():
    token = _get_user_token()
    ctx, error = _require_auth(token)
    if error:
        return error

    body = request.get_json(force=True)
    screening_id = body.get("screening_id")
    if not screening_id:
        return jsonify({"error": "screening_id is required"}), 400

    status = body.get("status", "open")
    notes = body.get("notes")
    case = persist_case(token, screening_id, status=status, notes=notes)
    if case is None:
        return jsonify({"error": "Unable to create case"}), 503

    return jsonify(case), 201


@bp.route("/<case_id>", methods=["GET"])
def get_case(case_id):
    token = _get_user_token()
    ctx, error = _require_auth(token)
    if error:
        return error

    case = fetch_case(token, case_id)
    if case is None:
        return jsonify({"error": "Case not found"}), 404
    return jsonify(case)


@bp.route("/<case_id>", methods=["PATCH"])
def patch_case(case_id):
    token = _get_user_token()
    ctx, error = _require_auth(token)
    if error:
        return error

    body = request.get_json(force=True)
    case = update_case(
        token,
        case_id,
        status=body.get("status"),
        notes=body.get("notes"),
    )
    if case is None:
        return jsonify({"error": "Case not found or could not be updated"}), 404
    return jsonify(case)


@bp.route("/<case_id>", methods=["DELETE"])
def remove_case(case_id):
    token = _get_user_token()
    ctx, error = _require_auth(token)
    if error:
        return error

    if delete_case(token, case_id):
        return jsonify({"deleted": True})
    return jsonify({"error": "Case not found or could not be deleted"}), 404
