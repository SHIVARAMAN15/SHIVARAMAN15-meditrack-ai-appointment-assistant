from datetime import datetime, timezone
from app.extensions import db

class ReminderLog(db.Model):
    """
    Model for recording reminder recommendations, simulations, and duplicate prevention.
    """
    __tablename__ = "reminder_logs"

    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey("appointments.id"), nullable=False, index=True)
    reminder_channel = db.Column(db.String(30), nullable=False, default="simulated_sms")
    simulated_message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="sent", index=True)  # sent, failed, recommended
    attempt_count = db.Column(db.Integer, nullable=False, default=1)
    error_category = db.Column(db.String(50), nullable=True)
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True
    )
    sent_at = db.Column(
        db.DateTime,
        nullable=True,
        default=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self):
        return {
            "id": self.id,
            "appointment_id": self.appointment_id,
            "reminder_channel": self.reminder_channel,
            "simulated_message": self.simulated_message,
            "status": self.status,
            "attempt_count": self.attempt_count,
            "error_category": self.error_category,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
        }

    def __repr__(self):
        return f"<ReminderLog apt={self.appointment_id} status={self.status} channel={self.reminder_channel}>"
