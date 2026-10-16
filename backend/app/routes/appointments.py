from flask import Blueprint, request, jsonify
from app.services.appointment_service import AppointmentService
from app.utils.validators import (
    validate_appointment_payload,
    validate_reschedule_payload,
    sanitize_text
)
from app.utils.exceptions import ValidationError

appointments_bp = Blueprint("appointments", __name__)

@appointments_bp.route("/appointments", methods=["GET"])
def list_appointments():
    """List appointments with filtering, pagination, and sorting."""
    status = request.args.get("status")
    department = request.args.get("department")
    search = request.args.get("search")
    risk_category = request.args.get("risk_category")
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 15, type=int)
    sort_by = request.args.get("sort_by", "appointment_datetime")
    sort_dir = request.args.get("sort_dir", "asc")

    result = AppointmentService.get_appointments(
        status=status,
        department=department,
        search=search,
        risk_category=risk_category,
        page=page,
        per_page=per_page,
        sort_by=sort_by,
        sort_dir=sort_dir
    )
    return jsonify(result), 200


@appointments_bp.route("/appointments/<id_or_code>", methods=["GET"])
def get_appointment(id_or_code):
    """Retrieve appointment details by ID or code, including prediction and reminder history."""
    appointment = AppointmentService.get_appointment(id_or_code)
    return jsonify(appointment.to_dict(include_latest_prediction=True, include_reminders=True)), 200


@appointments_bp.route("/appointments", methods=["POST"])
def create_appointment():
    """Create a new appointment with validation and conflict checking."""
    data = request.get_json(silent=True) or {}
    cleaned = validate_appointment_payload(data, is_create=True)
    appointment = AppointmentService.create_appointment(cleaned)
    return jsonify({
        "message": "Appointment created successfully.",
        "appointment": appointment.to_dict(include_latest_prediction=True)
    }), 201


@appointments_bp.route("/appointments/<id_or_code>/reschedule", methods=["POST"])
def reschedule_appointment(id_or_code):
    """Reschedule an existing appointment."""
    data = request.get_json(silent=True) or {}
    cleaned = validate_reschedule_payload(data)
    appointment = AppointmentService.reschedule_appointment(
        id_or_code=id_or_code,
        new_datetime=cleaned["appointment_datetime"],
        client_version=cleaned.get("version")
    )
    return jsonify({
        "message": f"Appointment {appointment.appointment_code} rescheduled successfully.",
        "appointment": appointment.to_dict(include_latest_prediction=True)
    }), 200


@appointments_bp.route("/appointments/<id_or_code>/cancel", methods=["POST"])
def cancel_appointment(id_or_code):
    """Cancel an appointment with validation and reason recording."""
    data = request.get_json(silent=True) or {}
    reason = sanitize_text(data.get("reason", "Cancelled by clinic staff"), 200)
    version = data.get("version")
    if version is not None:
        try:
            version = int(version)
        except (ValueError, TypeError):
            raise ValidationError("Version must be an integer.")

    appointment = AppointmentService.cancel_appointment(
        id_or_code=id_or_code,
        reason=reason,
        client_version=version
    )
    return jsonify({
        "message": f"Appointment {appointment.appointment_code} has been cancelled.",
        "appointment": appointment.to_dict(include_latest_prediction=True)
    }), 200


@appointments_bp.route("/appointments/<id_or_code>", methods=["PATCH"])
def patch_appointment(id_or_code):
    """Update appointment operational notes or status."""
    appointment = AppointmentService.get_appointment(id_or_code)
    data = request.get_json(silent=True) or {}

    if "notes" in data:
        appointment.notes = sanitize_text(data["notes"], 500)

    if "status" in data:
        new_status = str(data["status"]).lower().strip()
        if new_status not in appointment.VALID_STATUSES:
            raise ValidationError(f"Invalid status '{new_status}'.")
        appointment.status = new_status

    from app.extensions import db
    appointment.version += 1
    db.session.commit()

    return jsonify({
        "message": "Appointment updated successfully.",
        "appointment": appointment.to_dict(include_latest_prediction=True)
    }), 200
