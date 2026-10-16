from datetime import datetime, timezone
from app.extensions import db

class InteractionLog(db.Model):
    """
    Model for recording chatbot and staff interactions, recognized intents, and operational results.
    Excludes sensitive medical data and limits text lengths.
    """
    __tablename__ = "interaction_logs"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), nullable=False, default="staff_session", index=True)
    actor = db.Column(db.String(50), nullable=False, default="staff_demo")
    intent = db.Column(db.String(50), nullable=True, index=True)
    sanitized_user_message = db.Column(db.String(500), nullable=True)
    response_summary = db.Column(db.String(500), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="success", index=True)  # success, failure, ambiguous
    error_category = db.Column(db.String(50), nullable=True)
    timestamp = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True
    )

    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "actor": self.actor,
            "intent": self.intent,
            "sanitized_user_message": self.sanitized_user_message,
            "response_summary": self.response_summary,
            "status": self.status,
            "error_category": self.error_category,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }

    def __repr__(self):
        return f"<InteractionLog intent={self.intent} status={self.status} at={self.timestamp}>"
