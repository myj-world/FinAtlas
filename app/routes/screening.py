from flask import Blueprint, request, jsonify
import pandas as pd

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

    if "file" in request.files:
        file = request.files["file"]
        df = pd.read_csv(file)
        transactions = df.where(pd.notnull(df), None).to_dict(orient="records")
    else:
        transactions = request.get_json(force=True)
        if not isinstance(transactions, list):
            return jsonify({"error": "Request body must be a list of transactions"}), 400

    results = [screen_transaction(tx, user_token=token) for tx in transactions]
    return jsonify({"count": len(results), "results": results})
