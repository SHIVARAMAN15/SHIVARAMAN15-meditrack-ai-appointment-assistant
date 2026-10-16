import json
from datetime import datetime, timezone
from app.extensions import db

class PredictionLog(db.Model):
    """
    Model for recording machine learning attendance prediction outputs and features.
    """
    __tablename__ = "prediction_logs"

    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey("appointments.id"), nullable=False, index=True)
    model_version = db.Column(db.String(50), nullable=False, default="v1.0.0")
    attendance_probability = db.Column(db.Float, nullable=False)
    no_show_probability = db.Column(db.Float, nullable=False)
    risk_category = db.Column(db.String(20), nullable=False, index=True)  # low, medium, high
    input_summary_json = db.Column(db.Text, nullable=True)
    prediction_timestamp = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True
    )

    def to_dict(self):
        input_data = {}
        if self.input_summary_json:
            try:
                input_data = json.loads(self.input_summary_json)
            except Exception:
                input_data = {"raw": self.input_summary_json}

        return {
            "id": self.id,
            "appointment_id": self.appointment_id,
            "model_version": self.model_version,
            "attendance_probability": round(self.attendance_probability, 4),
            "no_show_probability": round(self.no_show_probability, 4),
            "risk_category": self.risk_category,
            "features": input_data,
            "prediction_timestamp": self.prediction_timestamp.isoformat() if self.prediction_timestamp else None
        }

    def __repr__(self):
        return f"<PredictionLog apt={self.appointment_id} attend={self.attendance_probability:.2f} risk={self.risk_category}>"
