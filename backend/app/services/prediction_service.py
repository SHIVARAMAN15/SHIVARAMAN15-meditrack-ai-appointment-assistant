"""
Service for computing, logging, and retrieving appointment attendance predictions.
"""
from datetime import datetime, timezone
from flask import current_app
from app.extensions import db
from app.models.appointment import Appointment
from app.models.prediction_log import PredictionLog
from app.models.reminder_log import ReminderLog
from app.ml.predict import predict_attendance
from app.services.logging_service import LoggingService
from app.utils.exceptions import NotFoundError, ValidationError

class PredictionService:
    @staticmethod
    def extract_features_for_appointment(appointment: Appointment) -> dict:
        """Extract prediction features from an appointment and historical patient data."""
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        apt_dt = appointment.appointment_datetime
        created = appointment.created_at or now

        # Lead time in days between creation/booking and appointment
        lead_time = max(0, (apt_dt.date() - created.date()).days)

        # Day of week and hour
        day_of_week = apt_dt.weekday()
        hour = apt_dt.hour

        # Historical patient behavior in the clinic system
        patient_ref = appointment.patient_reference

        # Previous appointments query
        prev_apts = Appointment.query.filter(
            Appointment.patient_reference == patient_ref,
            Appointment.id != appointment.id,
            Appointment.appointment_datetime < apt_dt
        ).all()

        total_prev = len(prev_apts)
        total_no_shows = sum(1 for a in prev_apts if a.status == "no_show")

        # Check if reminder was sent for this appointment
        had_reminder = 1 if len(appointment.reminders) > 0 else 0

        return {
            "lead_time_days": lead_time,
            "day_of_week": day_of_week,
            "appointment_hour": hour,
            "previous_appointments": total_prev,
            "previous_no_shows": total_no_shows,
            "had_previous_reminder": had_reminder,
            "department": appointment.department
        }

    @staticmethod
    def predict_for_appointment(appointment_id: int, log_result: bool = True) -> dict:
        """Compute attendance prediction for an appointment and optionally log to DB."""
        appointment = db.session.get(Appointment, appointment_id)
        if not appointment:
            raise NotFoundError(f"Appointment with ID {appointment_id} not found.")

        features = PredictionService.extract_features_for_appointment(appointment)

        low_th = current_app.config.get("RISK_THRESHOLD_LOW", 0.30)
        high_th = current_app.config.get("RISK_THRESHOLD_HIGH", 0.60)
        model_path = current_app.config.get("MODEL_ARTIFACT_PATH")

        prediction_result = predict_attendance(
            features=features,
            model_path=model_path,
            risk_threshold_low=low_th,
            risk_threshold_high=high_th
        )

        if log_result:
            log_entry = LoggingService.log_prediction(
                appointment_id=appointment.id,
                model_version=prediction_result["model_version"],
                attendance_prob=prediction_result["attendance_probability"],
                no_show_prob=prediction_result["no_show_probability"],
                risk_category=prediction_result["risk_category"],
                features_dict=prediction_result["features"]
            )
            prediction_result["id"] = log_entry.id if log_entry else None
            prediction_result["prediction_timestamp"] = log_entry.prediction_timestamp.isoformat() if log_entry else datetime.now(timezone.utc).isoformat()

        prediction_result["appointment_id"] = appointment.id
        prediction_result["appointment_code"] = appointment.appointment_code
        prediction_result["patient_name"] = appointment.patient_name

        return prediction_result

    @staticmethod
    def get_latest_prediction(appointment_id: int) -> dict:
        """Get latest recorded prediction for an appointment or compute a new one."""
        appointment = db.session.get(Appointment, appointment_id)
        if not appointment:
            raise NotFoundError(f"Appointment with ID {appointment_id} not found.")

        latest = PredictionLog.query.filter_by(appointment_id=appointment_id).order_by(
            PredictionLog.prediction_timestamp.desc()
        ).first()

        if latest:
            data = latest.to_dict()
            data["appointment_code"] = appointment.appointment_code
            data["patient_name"] = appointment.patient_name
            return data

        # If no prediction logged yet, compute one
        return PredictionService.predict_for_appointment(appointment_id, log_result=True)
