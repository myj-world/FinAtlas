import os

from flask import Blueprint, abort, jsonify, render_template, send_from_directory

from app.services.auth import auth_required, mfa_required

bp = Blueprint("dashboard", __name__)


@bp.route("/")
def index():
    return render_template(
        "index.html",
        supabase_url=os.getenv("VITE_SUPABASE_URL") or os.getenv("SUPABASE_URL") or "",
        supabase_key=os.getenv("VITE_SUPABASE_ANON_KEY")
        or os.getenv("SUPABASE_ANON_KEY")
        or os.getenv("SUPABASE_KEY")
        or "",
        require_auth=auth_required(),
        require_mfa=mfa_required(),
    )


@bp.route("/api/config")
def public_config():
    """Return safe, non-secret server configuration for the frontend."""
    return jsonify(
        {
            "require_auth": auth_required(),
            "require_mfa": mfa_required(),
            "supabase_url": os.getenv("VITE_SUPABASE_URL")
            or os.getenv("SUPABASE_URL")
            or "",
        }
    )


@bp.route("/icon.png")
def favicon():
    """Serve the project-root icon.png if it exists. Falls back to icon.jpg for older projects."""
    if os.path.exists("icon.png"):
        return send_from_directory(os.getcwd(), "icon.png", mimetype="image/png")
    if os.path.exists("icon.jpg"):
        return send_from_directory(os.getcwd(), "icon.jpg", mimetype="image/jpeg")
    abort(404)
