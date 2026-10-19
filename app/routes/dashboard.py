import os

from flask import Blueprint, render_template

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
    )
