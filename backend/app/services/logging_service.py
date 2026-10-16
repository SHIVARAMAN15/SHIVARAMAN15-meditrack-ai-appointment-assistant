"""
Audit and interaction logging service for application events and analytics.
"""
import logging
import json
from datetime import datetime, timezone
from app.extensions import db
from app.models.interaction_log import InteractionLog
from app.models.prediction_log import PredictionLog
from app.models.reminder_log import ReminderLog

logger = logging.getLogger("meditrack.audit")

class LoggingService:
    @staticmethod
    def log_interaction(
        session_id: str = "staff_session",
        actor: str = "staff_demo",
        intent: str = None,
        sanitized_user_message: str = None,
        response_summary: str = None,
        status: str = "success",
        error_category: str = None
    ) -> InteractionLog:
        """Record a chat or staff interaction in the database and operational log."""
        try:
            entry = InteractionLog(
                session_id=session_id or "staff_session",
                actor=actor or "staff_demo",
                intent=intent,
                sanitized_user_message=sanitized_user_message[:500] if sanitized_user_message else None,
                response_summary=response_summary[:500] if response_summary else None,
                status=status,
                error_category=error_category,
                timestamp=datetime.now(timezone.utc)
            )
            db.session.add(entry)
            db.session.commit()
            logger.info(f"Interaction logged: intent={intent} status={status} actor={actor}")
            return entry
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to record interaction log: {e}")
            return None

    @staticmethod
    def log_prediction(
        appointment_id: int,
        model_version: str,
        attendance_prob: float,
        no_show_prob: float,
        risk_category: str,
        features_dict: dict = None
    ) -> PredictionLog:
        """Record an ML inference result in the database."""
        try:
            features_json = json.dumps(features_dict) if features_dict else None
            entry = PredictionLog(
                appointment_id=appointment_id,
                model_version=model_version or "v1.0.0",
                attendance_probability=attendance_prob,
                no_show_probability=no_show_prob,
                risk_category=risk_category,
                input_summary_json=features_json,
                prediction_timestamp=datetime.now(timezone.utc)
            )
            db.session.add(entry)
            db.session.commit()
            logger.info(f"Prediction logged: apt={appointment_id} attend={attendance_prob:.2f} risk={risk_category}")
            return entry
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to record prediction log: {e}")
            return None

    @staticmethod
    def log_reminder(
        appointment_id: int,
        simulated_message: str,
        channel: str = "simulated_sms",
        status: str = "sent",
        attempt_count: int = 1,
        error_category: str = None
    ) -> ReminderLog:
        """Record a simulated reminder delivery event in the database."""
        try:
            entry = ReminderLog(
                appointment_id=appointment_id,
                reminder_channel=channel,
                simulated_message=simulated_message,
                status=status,
                attempt_count=attempt_count,
                error_category=error_category,
                created_at=datetime.now(timezone.utc),
                sent_at=datetime.now(timezone.utc) if status == "sent" else None
            )
            db.session.add(entry)
            db.session.commit()
            logger.info(f"Reminder logged: apt={appointment_id} channel={channel} status={status}")
            return entry
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to record reminder log: {e}")
            return None
