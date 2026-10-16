from flask import Blueprint, jsonify, request
from app.models.reminder_log import ReminderLog
from app.services.reminder_service import ReminderService
from app.utils.validators import sanitize_text

reminders_bp = Blueprint("reminders", __name__)

@reminders_bp.route("/reminders", methods=["GET"])
def list_reminders():
    """List historical simulated reminders sent."""
    limit = request.args.get("limit", 50, type=int)
    appointment_id = request.args.get("appointment_id", type=int)

    query = ReminderLog.query
    if appointment_id:
        query = query.filter_by(appointment_id=appointment_id)

    logs = query.order_by(ReminderLog.created_at.desc()).limit(limit).all()
    return jsonify({
        "reminders": [log.to_dict() for log in logs],
        "count": len(logs)
    }), 200


@reminders_bp.route("/reminders/recommendations", methods=["GET", "POST"])
def get_reminder_recommendations():
    """Identify upcoming appointments meeting risk thresholds for reminder dispatch."""
    include_medium = True
    if request.is_json and request.json:
        include_medium = request.json.get("include_medium_risk", True)

    recommendations = ReminderService.get_recommendations(include_medium_risk=include_medium)
    return jsonify({
        "recommendations": recommendations,
        "count": len(recommendations)
    }), 200


@reminders_bp.route("/reminders/<int:appointment_id>/send", methods=["POST"])
def send_simulated_reminder(appointment_id):
    """Trigger simulated reminder dispatch for an appointment with duplicate prevention."""
    data = request.get_json(silent=True) or {}
    channel = sanitize_text(data.get("channel", "simulated_sms"), 30) or "simulated_sms"
    force = bool(data.get("force", False))

    result = ReminderService.send_simulated_reminder(
        appointment_id=appointment_id,
        channel=channel,
        force=force
    )
    return jsonify(result), 200
