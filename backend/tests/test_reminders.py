from datetime import datetime, timezone, timedelta
import pytest
from app.services.reminder_service import ReminderService
from app.models.reminder_log import ReminderLog
from app.models.appointment import Appointment
from app.utils.exceptions import ConflictError, BusinessRuleError

def test_reminder_recommendation_filtering(db_session, sample_appointment):
    """Requirement 15: Recommendations exclude past and cancelled appointments."""
    # Past appointment
    past_apt = Appointment(
        appointment_code="APT-PAST",
        patient_reference="PAT-PAST",
        patient_name="Past Patient",
        department="General Practice",
        appointment_datetime=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=2),
        status="completed",
        version=1
    )
    db_session.add(past_apt)
    db_session.commit()

    recs = ReminderService.get_recommendations()
    rec_codes = [r["appointment_code"] for r in recs]
    assert "APT-PAST" not in rec_codes


def test_simulated_reminder_dispatch_and_logging(db_session, sample_appointment):
    """Test simulated reminder creation, log persistence, and message formatting."""
    res = ReminderService.send_simulated_reminder(
        appointment_id=sample_appointment.id,
        channel="simulated_sms"
    )
    assert res["success"] is True
    assert res["simulated"] is True
    assert sample_appointment.patient_name in res["reminder"]["simulated_message"]
    assert "[SIMULATED]" in res["reminder"]["simulated_message"]

    log = ReminderLog.query.filter_by(appointment_id=sample_appointment.id).first()
    assert log is not None
    assert log.status == "sent"
    assert log.attempt_count == 1


def test_duplicate_reminder_prevention(db_session, sample_appointment):
    """Requirement 16: Sending a reminder within 24 hours without force raises ConflictError."""
    # First send succeeds
    ReminderService.send_simulated_reminder(sample_appointment.id)

    # Second send within 24 hours fails with ConflictError
    with pytest.raises(ConflictError) as exc_info:
        ReminderService.send_simulated_reminder(sample_appointment.id)
    assert "already sent" in str(exc_info.value).lower()

    # With force=True, send succeeds
    res_forced = ReminderService.send_simulated_reminder(sample_appointment.id, force=True)
    assert res_forced["success"] is True
    assert res_forced["reminder"]["attempt_count"] == 2
