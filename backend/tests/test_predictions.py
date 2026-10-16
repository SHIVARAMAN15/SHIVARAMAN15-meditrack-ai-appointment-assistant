from app.services.prediction_service import PredictionService
from app.models.prediction_log import PredictionLog
from app.ml.predict import predict_attendance
from app.utils.exceptions import ModelNotReadyError
import pytest

def test_prediction_output_ranges(sample_appointment):
    """Requirement 12: Attendance and no-show probabilities are between 0.0 and 1.0."""
    result = PredictionService.predict_for_appointment(sample_appointment.id, log_result=True)
    attend_prob = result["attendance_probability"]
    noshow_prob = result["no_show_probability"]

    assert 0.0 <= attend_prob <= 1.0
    assert 0.0 <= noshow_prob <= 1.0
    assert abs((attend_prob + noshow_prob) - 1.0) < 0.01
    assert result["risk_category"] in ("low", "medium", "high")


def test_risk_categorization_thresholds():
    """Verify deterministic risk categorization rules."""
    features = {
        "lead_time_days": 2,
        "day_of_week": 2,
        "appointment_hour": 10,
        "previous_appointments": 5,
        "previous_no_shows": 0,
        "had_previous_reminder": 1,
        "department": "General Practice"
    }

    # Low risk (<30%)
    res_low = predict_attendance(features, risk_threshold_low=0.50, risk_threshold_high=0.80)
    assert res_low["risk_category"] in ("low", "medium")

    # High risk when threshold set low
    res_high = predict_attendance(features, risk_threshold_low=0.01, risk_threshold_high=0.02)
    assert res_high["risk_category"] == "high"


def test_prediction_logging(db_session, sample_appointment):
    """Requirement 14: Predictions are logged in PredictionLog table."""
    initial_count = PredictionLog.query.filter_by(appointment_id=sample_appointment.id).count()
    result = PredictionService.predict_for_appointment(sample_appointment.id, log_result=True)

    new_count = PredictionLog.query.filter_by(appointment_id=sample_appointment.id).count()
    assert new_count == initial_count + 1

    latest = PredictionLog.query.filter_by(appointment_id=sample_appointment.id).first()
    assert latest.attendance_probability == result["attendance_probability"]
    assert latest.model_version == "v1.0.0"


def test_model_unavailable_behavior():
    """Requirement 13: ModelNotReadyError raised gracefully when model path is invalid."""
    with pytest.raises(ModelNotReadyError) as exc_info:
        predict_attendance(
            features={"lead_time_days": 5},
            model_path="/non/existent/path/model.joblib"
        )
    assert "not found" in str(exc_info.value).lower()
