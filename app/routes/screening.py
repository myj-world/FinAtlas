from flask import Blueprint, request, jsonify

from app.services.ingestion import IngestionError, IngestionService
from app.services.scoring import screen_transaction
from app.utils import extract_bearer_token

bp = Blueprint("screening", __name__, url_prefix="/api/screen")


@bp.route("/single", methods=["POST"])
def single():
    transaction = request.get_json(force=True)
    token = extract_bearer_token(request.headers)
    result = screen_transaction(transaction, user_token=token)
    return jsonify(result)


@bp.route("/batch", methods=["POST"])
def batch():
    token = extract_bearer_token(request.headers)

    try:
        if "file" in request.files:
            file = request.files["file"]
            if file.filename == "":
                return jsonify({"error": "No file selected"}), 400
            transactions = IngestionService.from_csv(file)
        else:
            body = request.get_json(force=True)
            transactions = IngestionService.from_records(body)
    except IngestionError as exc:
        return jsonify({"error": str(exc)}), 400

    results = [screen_transaction(tx, user_token=token) for tx in transactions]
    return jsonify({"count": len(results), "results": results})
