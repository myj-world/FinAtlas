import os
from flask import Blueprint, jsonify

bp = Blueprint("health", __name__)


@bp.route("/api/health")
def health():
    return jsonify(
        {
            "status": "ok",
            "service": "FinAtlas AML API",
            "environment": {
                "supabase_url_configured": bool(os.getenv("SUPABASE_URL")),
                "supabase_key_configured": bool(
                    os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY")
                ),
                "gemini_api_key_configured": bool(os.getenv("GEMINI_API_KEY")),
            },
        }
    )
