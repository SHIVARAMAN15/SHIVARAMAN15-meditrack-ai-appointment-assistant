"""
MediTrack AI Application Factory and Blueprint Registration.
"""
import logging
from pathlib import Path
from flask import Flask, jsonify
from sqlalchemy import event
from sqlalchemy.engine import Engine
from app.config import Config
from app.extensions import db, cors
from app.utils.exceptions import AppException

# Configure root logger with both console and persistent file handlers
log_file_path = Path(__file__).resolve().parent.parent / "meditrack.log"
file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        file_handler
    ]
)
logger = logging.getLogger("meditrack.app")

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Enforce Write-Ahead Logging (WAL) and busy timeout on SQLite to handle concurrent requests safely."""
    try:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()
    except Exception as e:
        # If running on another engine (e.g. Postgres), ignore pragma failure
        pass


def create_app(config_class=Config):
    """Application factory for MediTrack AI Assistant backend."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    cors.init_app(
        app,
        origins=app.config.get("CORS_ORIGINS", ["http://localhost:5173", "http://127.0.0.1:5173"]),
        supports_credentials=True
    )

    # Register blueprints
    from app.routes.health import health_bp
    from app.routes.appointments import appointments_bp
    from app.routes.chatbot import chatbot_bp
    from app.routes.predictions import predictions_bp
    from app.routes.reminders import reminders_bp
    from app.routes.analytics import analytics_bp

    app.register_blueprint(health_bp, url_prefix="/api")
    app.register_blueprint(appointments_bp, url_prefix="/api")
    app.register_blueprint(chatbot_bp, url_prefix="/api")
    app.register_blueprint(predictions_bp, url_prefix="/api")
    app.register_blueprint(reminders_bp, url_prefix="/api")
    app.register_blueprint(analytics_bp, url_prefix="/api")

    # Global structured error handlers
    @app.errorhandler(AppException)
    def handle_app_exception(e):
        return jsonify(e.to_dict()), e.status_code

    @app.errorhandler(400)
    def handle_bad_request(e):
        return jsonify({
            "error": {
                "code": "BAD_REQUEST",
                "message": str(e.description) if hasattr(e, "description") else "Bad request."
            }
        }), 400

    @app.errorhandler(404)
    def handle_not_found(e):
        return jsonify({
            "error": {
                "code": "NOT_FOUND",
                "message": "The requested resource or endpoint was not found."
            }
        }), 404

    @app.errorhandler(405)
    def handle_method_not_allowed(e):
        return jsonify({
            "error": {
                "code": "METHOD_NOT_ALLOWED",
                "message": "The HTTP method is not allowed on this endpoint."
            }
        }), 405

    @app.errorhandler(500)
    def handle_internal_error(e):
        logger.error(f"Internal server error: {e}")
        return jsonify({
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An internal server error occurred. Please try again later."
            }
        }), 500

    # Auto-initialize database tables within app context
    with app.app_context():
        from app.models import Appointment  # register models with SQLAlchemy
        db.create_all()

    return app
