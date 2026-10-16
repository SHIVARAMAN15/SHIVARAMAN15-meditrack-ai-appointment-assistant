from datetime import datetime, timezone
from pathlib import Path
from flask import Blueprint, jsonify, current_app
from sqlalchemy import text
from app.extensions import db

health_bp = Blueprint("health", __name__)

@health_bp.route("/health", methods=["GET"])
def health_check():
    """System health check endpoint verifying database connectivity and ML readiness."""
    # 1. Database check
    db_connected = False
    try:
        db.session.execute(text("SELECT 1"))
        db_connected = True
    except Exception:
        db_connected = False

    # 2. ML model artifact readiness
    model_path_str = current_app.config.get("MODEL_ARTIFACT_PATH")
    model_ready = False
    model_type = "Random Forest Classifier (scikit-learn)"
    model_version = "v1.0.0"

    if model_path_str and Path(model_path_str).exists():
        model_ready = True

    return jsonify({
        "status": "healthy" if db_connected else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": {
            "status": "connected" if db_connected else "disconnected",
            "type": "SQLite with WAL & Busy Timeout"
        },
        "ml_model": {
            "status": "ready" if model_ready else "not_trained",
            "model_type": model_type,
            "version": model_version
        },
        "reminder_provider": {
            "mode": "simulation_dry_run",
            "channel": "simulated_sms"
        }
    }), 200 if db_connected else 503
