"""
Service for calculating reminder recommendations, generating safe preview templates,
and executing simulated reminder dispatches with duplicate prevention.
"""
from datetime import datetime, timezone, timedelta
from flask import current_app
from app.extensions import db
from app.models.appointment import Appointment
from app.models.reminder_log import ReminderLog
from app.services.prediction_service import PredictionService
from app.services.logging_service import LoggingService
from app.utils.exceptions import NotFoundError, ConflictError, BusinessRuleError

class ReminderService:
    @staticmethod
    def format_reminder_message(appointment: Appointment) -> str:
        """Format safe simulated reminder message for a patient."""
        dt = appointment.appointment_datetime
        date_str = dt.strftime("%B %d, %Y")
        time_str = dt.strftime("%I:%M %p").lstrip("0")
        return (
            f"Hello {appointment.patient_name}, this is a [SIMULATED] reminder from MediTrack "
            f"for your upcoming appointment on {date_str} at {time_str} ({appointment.department}). "
            f"Please contact clinic staff if you need to reschedule. [Reference: {appointment.appointment_code}]"
        )

    @staticmethod
    def get_recommendations(include_medium_risk: bool = True) -> list:
        """
        Identify upcoming appointments needing reminders based on predicted risk.
        Filters out past, cancelled, completed, and already-reminded appointments.
        """
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        upcoming_appointments = Appointment.query.filter(
            Appointment.status == "scheduled",
            Appointment.appointment_datetime > now
        ).order_by(Appointment.appointment_datetime.asc()).all()

        high_th = current_app.config.get("RISK_THRESHOLD_HIGH", 0.60)
        low_th = current_app.config.get("RISK_THRESHOLD_LOW", 0.30)

        recommendations = []

        for apt in upcoming_appointments:
            # Check existing reminders sent in the last 24 hours
            recent_reminder = ReminderLog.query.filter(
                ReminderLog.appointment_id == apt.id,
                ReminderLog.status == "sent",
                ReminderLog.sent_at >= now - timedelta(hours=24)
            ).first()

            # Total reminder attempts
            attempt_count = ReminderLog.query.filter_by(
                appointment_id=apt.id,
                status="sent"
            ).count()

            pred = PredictionService.get_latest_prediction(apt.id)
            no_show_prob = pred["no_show_probability"]
            risk_category = pred["risk_category"]

            should_recommend = False
            reason = ""

            if no_show_prob >= high_th:
                should_recommend = True
                reason = f"High predicted no-show risk ({no_show_prob:.1%})"
            elif include_medium_risk and no_show_prob >= low_th:
                # Recommend medium risk if appointment is within next 7 days
                days_until = (apt.appointment_datetime.date() - now.date()).days
                if days_until <= 7:
                    should_recommend = True
                    reason = f"Medium no-show risk ({no_show_prob:.1%}) within 7 days"

            if should_recommend:
                recommendations.append({
                    "appointment_id": apt.id,
                    "appointment_code": apt.appointment_code,
                    "patient_name": apt.patient_name,
                    "patient_reference": apt.patient_reference,
                    "department": apt.department,
                    "appointment_datetime": apt.appointment_datetime.isoformat(),
                    "no_show_probability": no_show_prob,
                    "risk_category": risk_category,
                    "reason": reason,
                    "preview_message": ReminderService.format_reminder_message(apt),
                    "already_reminded_recently": recent_reminder is not None,
                    "total_reminders_sent": attempt_count,
                    "can_send": recent_reminder is None and attempt_count < 2
                })

        return recommendations

    @staticmethod
    def send_simulated_reminder(appointment_id: int, channel: str = "simulated_sms", force: bool = False) -> dict:
        """
        Simulate reminder delivery and record event in database.
        Enforces duplicate prevention unless forced.
        """
        appointment = db.session.get(Appointment, appointment_id)
        if not appointment:
            raise NotFoundError(f"Appointment with ID {appointment_id} not found.")

        if appointment.status != "scheduled":
            raise BusinessRuleError(f"Cannot send reminder for an appointment with status '{appointment.status}'.")

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if appointment.appointment_datetime <= now:
            raise BusinessRuleError("Cannot send reminder for past appointments.")

        # Check duplicate reminder within 24 hours
        recent_reminder = ReminderLog.query.filter(
            ReminderLog.appointment_id == appointment_id,
            ReminderLog.status == "sent",
            ReminderLog.sent_at >= now - timedelta(hours=24)
        ).first()

        if recent_reminder and not force:
            raise ConflictError(
                f"A reminder was already sent for {appointment.appointment_code} at {recent_reminder.sent_at.isoformat()}. "
                "Duplicate reminders within 24 hours are blocked to prevent patient fatigue."
            )

        attempt_count = ReminderLog.query.filter_by(
            appointment_id=appointment_id,
            status="sent"
        ).count() + 1

        simulated_msg = ReminderService.format_reminder_message(appointment)

        log_entry = LoggingService.log_reminder(
            appointment_id=appointment.id,
            simulated_message=simulated_msg,
            channel=channel,
            status="sent",
            attempt_count=attempt_count
        )

        return {
            "success": True,
            "simulated": True,
            "message": "Simulated reminder delivered and recorded successfully.",
            "reminder": log_entry.to_dict() if log_entry else None
        }

    @staticmethod
    def get_reminders_for_appointment(appointment_id: int) -> list:
        """Retrieve historical reminders sent for a given appointment."""
        appointment = Appointment.query.get(appointment_id)
        if not appointment:
            raise NotFoundError(f"Appointment with ID {appointment_id} not found.")

        logs = ReminderLog.query.filter_by(appointment_id=appointment_id).order_by(
            ReminderLog.created_at.desc()
        ).all()
        return [log.to_dict() for log in logs]
