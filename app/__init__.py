from flask import Flask
from flask_cors import CORS
from werkzeug.exceptions import HTTPException
from dotenv import load_dotenv

from app.routes.health import bp as health_bp
from app.routes.screening import bp as screening_bp
from app.routes.dashboard import bp as dashboard_bp
from app.services.gemini import GeminiError


def create_app() -> Flask:
    load_dotenv()
    app = Flask(__name__, static_folder="static", template_folder="templates")
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    app.register_blueprint(health_bp)
    app.register_blueprint(screening_bp)
    app.register_blueprint(dashboard_bp)

    @app.errorhandler(GeminiError)
    def handle_gemini_error(error):
        return {"error": "Gemini review failed", "detail": str(error)}, 503

    @app.errorhandler(Exception)
    def handle_generic_error(error):
        if isinstance(error, HTTPException):
            return {"error": error.description}, error.code
        app.logger.exception("Unhandled error")
        return {"error": "Internal server error"}, 500

    return app
