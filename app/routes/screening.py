from flask import Blueprint, request, jsonify

from app.services.auth import get_auth_context
from app.services.batch import submit_batch
from app.services.ingestion import IngestionError, IngestionService
from app.services.scoring import screen_transaction
from app.services.store import fetch_batch, persist_batch as store_persist_batch
from app.utils import extract_bearer_token

bp = Blueprint("screening", __name__, url_prefix="/api/screen")


def _parse_transactions():
    """Parse transactions from a CSV upload or JSON list."""
    if "file" in request.files:
        file = request.files["file"]
        if file.filename == "":
            raise IngestionError("No file selected")
        return IngestionService.from_csv(file)

    body = request.get_json(force=True)
    if isinstance(body, dict):
        raise IngestionError("Request body must be a list of transactions")
    return IngestionService.from_records(body)


@bp.route("/single", methods=["POST"])
def single():
    transaction = request.get_json(force=True)
    token = extract_bearer_token(request.headers)
    ctx = get_auth_context(token)

    if ctx["error"]:
        return jsonify({"error": ctx["error"]}), 401

    result = screen_transaction(transaction, user_token=token)
    return jsonify(result)


@bp.route("/batch", methods=["POST"])
def batch():
    token = extract_bearer_token(request.headers)
    ctx = get_auth_context(token)

    if ctx["error"]:
        return jsonify({"error": ctx["error"]}), 401

    try:
        transactions = _parse_transactions()
    except IngestionError as exc:
        return jsonify({"error": str(exc)}), 400

    async_mode = request.args.get("async", "false").lower() in ("1", "true", "yes")

    if async_mode:
        batch_id = store_persist_batch(token, len(transactions))
        if batch_id is None:
            return jsonify({"error": "Unable to create batch job"}), 503
        submit_batch(batch_id, transactions, token)
        return jsonify(
            {
                "batch_id": batch_id,
                "status": "pending",
                "total": len(transactions),
                "message": "Batch accepted and is being processed in the background.",
            }
        ), 202

    results = [screen_transaction(tx, user_token=token) for tx in transactions]
    return jsonify({"count": len(results), "results": results})


@bp.route("/batch/<batch_id>", methods=["GET"])
def batch_status(batch_id):
    token = extract_bearer_token(request.headers)
    ctx = get_auth_context(token)

    if ctx["error"]:
        return jsonify({"error": ctx["error"]}), 401

    batch = fetch_batch(token, batch_id)
    if batch is None:
        return jsonify({"error": "Batch not found"}), 404

    return jsonify(batch)
