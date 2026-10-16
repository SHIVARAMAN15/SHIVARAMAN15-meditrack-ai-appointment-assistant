"""
Inference module for attendance prediction with thread-safe model caching and risk categorization.
"""
import os
import threading
from pathlib import Path
import pandas as pd
import joblib
from app.utils.exceptions import ModelNotReadyError, ValidationError

_MODEL_CACHE = None
_MODEL_LOCK = threading.Lock()
_MODEL_VERSION = "v1.0.0"

def get_model(model_path: str = None, force_reload: bool = False):
    """Retrieve or load cached model pipeline in a thread-safe manner."""
    global _MODEL_CACHE
    if model_path is None and _MODEL_CACHE is not None and not force_reload:
        return _MODEL_CACHE

    with _MODEL_LOCK:
        if model_path is None and _MODEL_CACHE is not None and not force_reload:
            return _MODEL_CACHE

        if not model_path:
            backend_dir = Path(__file__).resolve().parent.parent.parent
            target_path = backend_dir / "app" / "ml" / "artifacts" / "attendance_model.joblib"
        else:
            target_path = Path(model_path)

        if not target_path.exists():
            raise ModelNotReadyError(
                f"Model artifact not found at '{target_path}'. Run training script to initialize model."
            )

        try:
            loaded = joblib.load(target_path)
            if model_path is None:
                _MODEL_CACHE = loaded
            return loaded
        except Exception as e:
            raise ModelNotReadyError(f"Failed to load model artifact: {str(e)}")


def predict_attendance(
    features: dict,
    model_path: str = None,
    risk_threshold_low: float = 0.30,
    risk_threshold_high: float = 0.60
) -> dict:
    """
    Predict likelihood of patient attendance and assess no-show risk category.

    Categories:
    - low: predicted no-show < 30%
    - medium: 30% <= predicted no-show < 60%
    - high: predicted no-show >= 60%
    """
    pipeline = get_model(model_path)

    # Validate and default input features
    try:
        lead_time = max(0, int(features.get("lead_time_days", 7)))
        day_of_week = max(0, min(6, int(features.get("day_of_week", 2))))
        hour = max(0, min(23, int(features.get("appointment_hour", 10))))
        prev_apts = max(0, int(features.get("previous_appointments", 2)))
        prev_ns = max(0, int(features.get("previous_no_shows", 0)))
        had_rem = 1 if features.get("had_previous_reminder") else 0
        dept = str(features.get("department", "General Practice")).strip()
    except (ValueError, TypeError) as e:
        raise ValidationError(f"Invalid feature type in prediction input: {e}")

    input_df = pd.DataFrame([{
        "lead_time_days": lead_time,
        "day_of_week": day_of_week,
        "appointment_hour": hour,
        "previous_appointments": prev_apts,
        "previous_no_shows": prev_ns,
        "had_previous_reminder": had_rem,
        "department": dept
    }])

    try:
        probs = pipeline.predict_proba(input_df)[0]
        # Class 1 is attended, Class 0 is no-show
        prob_attend = float(probs[1])
        prob_noshow = float(probs[0])
    except Exception as e:
        raise ValidationError(f"Prediction inference error: {str(e)}")

    # Ensure bounds [0.0, 1.0]
    prob_attend = max(0.0, min(1.0, prob_attend))
    prob_noshow = max(0.0, min(1.0, prob_noshow))

    # Categorize risk
    if prob_noshow < risk_threshold_low:
        risk_category = "low"
    elif prob_noshow < risk_threshold_high:
        risk_category = "medium"
    else:
        risk_category = "high"

    return {
        "attendance_probability": round(prob_attend, 4),
        "no_show_probability": round(prob_noshow, 4),
        "risk_category": risk_category,
        "model_version": _MODEL_VERSION,
        "features": {
            "lead_time_days": lead_time,
            "day_of_week": day_of_week,
            "appointment_hour": hour,
            "previous_appointments": prev_apts,
            "previous_no_shows": prev_ns,
            "had_previous_reminder": had_rem,
            "department": dept
        }
    }
