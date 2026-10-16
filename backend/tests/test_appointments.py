from datetime import datetime, timezone, timedelta
import json
from app.models.appointment import Appointment
from app.services.analytics_service import AnalyticsService

def test_health_endpoint(client):
    """Requirement 1: Health endpoint returns system status and connectivity."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] in ("healthy", "degraded")
    assert data["database"]["status"] == "connected"
    assert "ml_model" in data
    assert "reminder_provider" in data


def test_appointment_creation(client, db_session):
    """Requirement 2: Appointment creation with valid payload."""
    future_dt = (datetime.now(timezone.utc) + timedelta(days=3)).replace(hour=14, minute=30, second=0, microsecond=0, tzinfo=None).isoformat()
    payload = {
        "patient_name": "Thomas Anderson",
        "department": "Neurology",
        "appointment_datetime": future_dt,
        "notes": "Headache consultation"
    }
    response = client.post("/api/appointments", json=payload)
    assert response.status_code == 201
    data = response.get_json()
    assert data["appointment"]["patient_name"] == "Thomas Anderson"
    assert data["appointment"]["department"] == "Neurology"
    assert data["appointment"]["status"] == "scheduled"
    assert data["appointment"]["appointment_code"].startswith("APT-")


def test_appointment_listing_and_filtering(client, db_session, sample_appointment):
    """Requirement 3: Listing and filtering appointments by department and status."""
    # List all
    res = client.get("/api/appointments")
    assert res.status_code == 200
    data = res.get_json()
    assert data["total"] >= 1

    # Filter by department
    res_cardio = client.get("/api/appointments?department=Cardiology")
    assert res_cardio.status_code == 200
    assert len(res_cardio.get_json()["appointments"]) == 1

    res_neuro = client.get("/api/appointments?department=Neurology")
    assert res_neuro.status_code == 200
    assert len(res_neuro.get_json()["appointments"]) == 0

    # Search by name
    res_search = client.get("/api/appointments?search=Connor")
    assert res_search.status_code == 200
    assert len(res_search.get_json()["appointments"]) == 1


def test_invalid_appointment_payloads(client):
    """Requirement 4: Rejection of invalid payloads (missing name, invalid department)."""
    future_dt = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()

    # Missing patient_name
    res1 = client.post("/api/appointments", json={"department": "Cardiology", "appointment_datetime": future_dt})
    assert res1.status_code == 400
    assert "Patient name is required" in res1.get_json()["error"]["message"]

    # Invalid department
    res2 = client.post("/api/appointments", json={"patient_name": "John", "department": "Witchcraft", "appointment_datetime": future_dt})
    assert res2.status_code == 400
    assert "Invalid department" in res2.get_json()["error"]["message"]

    # Invalid datetime format
    res3 = client.post("/api/appointments", json={"patient_name": "John", "department": "Cardiology", "appointment_datetime": "invalid-date"})
    assert res3.status_code == 400


def test_past_appointment_rejection(client):
    """Requirement 5: Appointments in the past must be rejected."""
    past_dt = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    payload = {
        "patient_name": "Marty McFly",
        "department": "General Practice",
        "appointment_datetime": past_dt
    }
    res = client.post("/api/appointments", json=payload)
    assert res.status_code == 400
    assert "future" in res.get_json()["error"]["message"].lower()


def test_successful_rescheduling(client, sample_appointment):
    """Requirement 6: Successfully rescheduling an appointment."""
    new_dt = (datetime.now(timezone.utc) + timedelta(days=7)).replace(hour=11, minute=0, second=0, microsecond=0, tzinfo=None).isoformat()
    res = client.post(f"/api/appointments/{sample_appointment.appointment_code}/reschedule", json={
        "appointment_datetime": new_dt
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["appointment"]["version"] == 2
    assert "2026" in data["appointment"]["appointment_datetime"] or "T11:00:00" in data["appointment"]["appointment_datetime"]


def test_conflicting_rescheduling(client, db_session, sample_appointment):
    """Requirement 7: Rescheduling to a time conflicting with another appointment for same patient."""
    # Create second appointment for same patient on Day 6
    day6_dt = (datetime.now(timezone.utc) + timedelta(days=6)).replace(hour=10, minute=0, second=0, microsecond=0, tzinfo=None)
    apt2 = Appointment(
        appointment_code="APT-1002",
        patient_reference=sample_appointment.patient_reference,
        patient_name=sample_appointment.patient_name,
        department="General Practice",
        appointment_datetime=day6_dt,
        status="scheduled",
        version=1
    )
    db_session.add(apt2)
    db_session.commit()

    # Try to reschedule apt1 to within 15 minutes of apt2
    conflicting_dt = (day6_dt + timedelta(minutes=10)).isoformat()
    res = client.post(f"/api/appointments/{sample_appointment.appointment_code}/reschedule", json={
        "appointment_datetime": conflicting_dt
    })
    assert res.status_code == 409
    assert "conflicting" in res.get_json()["error"]["message"].lower()


def test_cancellation(client, sample_appointment):
    """Requirement 8: Cancellation of an appointment."""
    res = client.post(f"/api/appointments/{sample_appointment.appointment_code}/cancel", json={
        "reason": "Patient requested cancellation"
    })
    assert res.status_code == 200
    assert res.get_json()["appointment"]["status"] == "cancelled"

    # Cancelling again should fail with business rule violation
    res_again = client.post(f"/api/appointments/{sample_appointment.appointment_code}/cancel")
    assert res_again.status_code == 422


def test_unknown_appointment_ids(client):
    """Requirement 9: Non-existent appointment IDs return 404."""
    res = client.get("/api/appointments/APT-9999")
    assert res.status_code == 404
    assert res.get_json()["error"]["code"] == "NOT_FOUND"


def test_database_transaction_rollback(app, db_session, sample_appointment):
    """Requirement 19: Database rollback occurs on operational errors."""
    with app.app_context():
        orig_dt = sample_appointment.appointment_datetime
        try:
            # Force an integrity error by updating code to None or violation
            sample_appointment.appointment_code = None
            db_session.commit()
        except Exception:
            db_session.rollback()

        # Check that original object was restored
        refetched = db_session.get(Appointment, sample_appointment.id)
        assert refetched.appointment_code == "APT-1001"
        assert refetched.appointment_datetime == orig_dt


def test_analytics_calculations(client, db_session, sample_appointment):
    """Requirement 18: Analytics summary calculation verification."""
    res = client.get("/api/analytics/summary")
    assert res.status_code == 200
    data = res.get_json()
    assert data["total_appointments"] == 1
    assert data["scheduled_appointments"] == 1
    assert data["completed_appointments"] == 0
    assert data["cancelled_appointments"] == 0
    assert "historical_no_show_rate" in data

    trends = client.get("/api/analytics/trends")
    assert trends.status_code == 200
    assert "outcomes" in trends.get_json()
    assert "risk_distribution" in trends.get_json()
