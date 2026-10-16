from flask import Blueprint, jsonify, request
from app.models.prediction_log import PredictionLog
from app.services.prediction_service import PredictionService
from app.services.appointment_service import AppointmentService

predictions_bp = Blueprint("predictions", __name__)

@predictions_bp.route("/predictions", methods=["GET"])
def list_predictions():
    """List recent prediction log entries with limit and ordering."""
    limit = request.args.get("limit", 50, type=int)
    risk_category = request.args.get("risk_category")

    query = PredictionLog.query
    if risk_category:
        query = query.filter_by(risk_category=risk_category)

    logs = query.order_by(PredictionLog.prediction_timestamp.desc()).limit(limit).all()
    return jsonify({
        "predictions": [log.to_dict() for log in logs],
        "count": len(logs)
    }), 200


@predictions_bp.route("/predictions/<int:appointment_id>", methods=["GET"])
def get_appointment_prediction(appointment_id):
    """Retrieve or compute attendance prediction for a given appointment."""
    pred = PredictionService.get_latest_prediction(appointment_id)
    return jsonify(pred), 200


@predictions_bp.route("/predictions/<int:appointment_id>/refresh", methods=["POST"])
def refresh_appointment_prediction(appointment_id):
    """Force re-computation and logging of attendance prediction."""
    pred = PredictionService.predict_for_appointment(appointment_id, log_result=True)
    return jsonify({
        "message": "Prediction recalculated and logged successfully.",
        "prediction": pred
    }), 200
