"""Import / ingestion endpoints for CSV, sample data and single-entry input."""

import os

from flask import Blueprint, jsonify, request

from app.services.ingestion import IngestionError, IngestionService
from app.services.scoring import screen_transaction
from app.utils import extract_bearer_token

bp = Blueprint("import", __name__, url_prefix="/api/import")

_SAMPLE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "sample_transactions.csv",
)


@bp.route("/sample", methods=["GET"])
def sample():
    """Return the pre-loaded sample dataset as JSON."""
    try:
        records = IngestionService.from_csv_path(_SAMPLE_PATH)
    except FileNotFoundError:
        return jsonify({"error": "Sample dataset not found"}), 404
    except IngestionError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify({"count": len(records), "records": records})


@bp.route("/single", methods=["POST"])
def single():
    """Screen a single manually-entered transaction after schema validation."""
    token = extract_bearer_token(request.headers)
    body = request.get_json(force=True)
    if not isinstance(body, dict):
        return jsonify({"error": "Request body must be a single transaction object"}), 400

    try:
        records = IngestionService.from_records([body])
    except IngestionError as exc:
        return jsonify({"error": str(exc)}), 400

    result = screen_transaction(records[0], user_token=token)
    return jsonify(result)


@bp.route("/csv", methods=["POST"])
def csv_import():
    """Ingest a CSV file. Use ?screen=true to screen every row immediately."""
    token = extract_bearer_token(request.headers)
    screen = request.args.get("screen", "false").lower() == "true"

    if "file" not in request.files:
        return jsonify({"error": "No CSV file provided (expected field name 'file')"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    try:
        records = IngestionService.from_csv(file)
    except IngestionError as exc:
        return jsonify({"error": str(exc)}), 400

    response = {"count": len(records), "records": records}
    if screen:
        response["results"] = [
            screen_transaction(tx, user_token=token) for tx in records
        ]
    return jsonify(response)


@bp.route("/validate", methods=["POST"])
def validate():
    """Validate a JSON list or CSV upload without screening."""
    if "file" in request.files:
        file = request.files["file"]
        if file.filename == "":
            return jsonify({"error": "No file selected"}), 400
        try:
            df = IngestionService._read_dataframe(file)
            records = IngestionService._dataframe_to_records(df)
        except IngestionError as exc:
            return jsonify({"error": str(exc)}), 400
    else:
        body = request.get_json(force=True)
        if not isinstance(body, list):
            return jsonify({"error": "Request body must be a list of transactions"}), 400
        records = body

    summary = IngestionService.validate_records(records)
    return jsonify(summary)
