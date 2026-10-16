from datetime import datetime, timezone
from app.extensions import db

class Appointment(db.Model):
    """
    Appointment model storing patient schedule details and operational status.
    Uses optimistic concurrency tracking with a version counter.
    """
    __tablename__ = "appointments"

    id = db.Column(db.Integer, primary_key=True)
    appointment_code = db.Column(db.String(32), unique=True, nullable=False, index=True)
    patient_reference = db.Column(db.String(32), nullable=False, index=True)
    patient_name = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(50), nullable=False, index=True)
    appointment_datetime = db.Column(db.DateTime, nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default="scheduled", index=True)
    notes = db.Column(db.String(500), nullable=True)
    version = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    predictions = db.relationship(
        "PredictionLog",
        backref="appointment",
        cascade="all, delete-orphan",
        order_by="desc(PredictionLog.prediction_timestamp)",
        lazy="select"
    )
    reminders = db.relationship(
        "ReminderLog",
        backref="appointment",
        cascade="all, delete-orphan",
        order_by="desc(ReminderLog.created_at)",
        lazy="select"
    )

    VALID_STATUSES = {"scheduled", "completed", "cancelled", "no_show"}

    def to_dict(self, include_latest_prediction=True, include_reminders=False):
        """Serialize appointment model to dictionary."""
        data = {
            "id": self.id,
            "appointment_code": self.appointment_code,
            "patient_reference": self.patient_reference,
            "patient_name": self.patient_name,
            "department": self.department,
            "appointment_datetime": self.appointment_datetime.isoformat(),
            "status": self.status,
            "notes": self.notes,
            "version": self.version,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

        if include_latest_prediction:
            latest_pred = self.predictions[0] if self.predictions else None
            data["latest_prediction"] = latest_pred.to_dict() if latest_pred else None

        if include_reminders:
            data["reminders"] = [r.to_dict() for r in self.reminders]

        return data

    def __repr__(self):
        return f"<Appointment {self.appointment_code} - {self.patient_name} ({self.status})>"
