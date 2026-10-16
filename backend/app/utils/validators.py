"""
Validation utilities for appointments, inputs, and payloads.
"""
from datetime import datetime, timezone
import re
from app.utils.exceptions import ValidationError

ALLOWED_DEPARTMENTS = [
    "General Practice",
    "Cardiology",
    "Dermatology",
    "Orthopedics",
    "Pediatrics",
    "Neurology",
    "Oncology",
    "Endocrinology"
]

def parse_iso_datetime(dt_str: str) -> datetime:
    """Safely parse ISO datetime string, normalizing to naive UTC."""
    if not dt_str or not isinstance(dt_str, str):
        raise ValidationError("Appointment datetime must be a valid ISO format string.")

    try:
        # Handles 2026-10-22T10:30:00 or 2026-10-22 10:30:00 or with trailing Z
        cleaned_str = dt_str.strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(cleaned_str)
        # Convert to naive UTC for consistent database storage
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt
    except Exception as e:
        raise ValidationError(f"Invalid date/time format: '{dt_str}'. Use ISO 8601 (e.g. YYYY-MM-DDTHH:MM:SS).")


def sanitize_text(text: str, max_length: int = 500) -> str:
    """Sanitize text input by stripping whitespace, limiting length, and removing risky tags."""
    if text is None:
        return ""
    text = str(text).strip()
    # Strip basic script or html tags
    text = re.sub(r"<[^>]*>", "", text)
    if len(text) > max_length:
        text = text[:max_length]
    return text


def validate_appointment_payload(data: dict, is_create: bool = True) -> dict:
    """Validate appointment creation or update payload."""
    if not isinstance(data, dict):
        raise ValidationError("Request payload must be a JSON object.")

    cleaned = {}

    if is_create:
        # Required fields
        if not data.get("patient_name") or not str(data["patient_name"]).strip():
            raise ValidationError("Patient name is required.")
        cleaned["patient_name"] = sanitize_text(data["patient_name"], 100)

        if not data.get("department") or not str(data["department"]).strip():
            raise ValidationError("Department is required.")
        dept = str(data["department"]).strip()
        if dept not in ALLOWED_DEPARTMENTS:
            raise ValidationError(
                f"Invalid department '{dept}'. Allowed departments: {', '.join(ALLOWED_DEPARTMENTS)}."
            )
        cleaned["department"] = dept

        if "patient_reference" in data and data["patient_reference"]:
            cleaned["patient_reference"] = sanitize_text(data["patient_reference"], 32)
        else:
            # Generate synthetic patient reference
            cleaned["patient_reference"] = None

    if "appointment_datetime" in data or is_create:
        raw_dt = data.get("appointment_datetime")
        if not raw_dt:
            raise ValidationError("A valid future appointment date and time is required.")
        dt = parse_iso_datetime(raw_dt)
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
        if dt <= now_utc:
            raise ValidationError("A valid future appointment date is required. Past dates are rejected.")
        cleaned["appointment_datetime"] = dt

    if "notes" in data and data["notes"]:
        cleaned["notes"] = sanitize_text(data["notes"], 500)
    elif is_create:
        cleaned["notes"] = ""

    if "version" in data and data["version"] is not None:
        try:
            cleaned["version"] = int(data["version"])
        except (ValueError, TypeError):
            raise ValidationError("Version must be an integer.")

    return cleaned


def validate_reschedule_payload(data: dict) -> dict:
    """Validate reschedule payload."""
    if not isinstance(data, dict):
        raise ValidationError("Request payload must be a JSON object.")

    raw_dt = data.get("appointment_datetime")
    if not raw_dt:
        raise ValidationError("A valid future appointment date and time is required.")
    dt = parse_iso_datetime(raw_dt)
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    if dt <= now_utc:
        raise ValidationError("A valid future appointment date is required. Past dates are rejected.")

    version = None
    if "version" in data and data["version"] is not None:
        try:
            version = int(data["version"])
        except (ValueError, TypeError):
            raise ValidationError("Version must be an integer.")

    return {
        "appointment_datetime": dt,
        "version": version
    }


def validate_chat_payload(data: dict) -> dict:
    """Validate chatbot query payload."""
    if not isinstance(data, dict):
        raise ValidationError("Request payload must be a JSON object.")

    raw_msg = data.get("message")
    if not raw_msg or not str(raw_msg).strip():
        raise ValidationError("Message cannot be empty.")

    cleaned_msg = sanitize_text(raw_msg, 500)
    session_id = sanitize_text(data.get("session_id", "staff_session"), 100)

    return {
        "message": cleaned_msg,
        "session_id": session_id or "staff_session"
    }
