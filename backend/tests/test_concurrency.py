from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
import pytest
from app.services.appointment_service import AppointmentService
from app.utils.exceptions import ConflictError
from app.models.appointment import Appointment
from app.extensions import db

def test_optimistic_concurrency_stale_version_rejection(db_session, sample_appointment):
    """Requirement 20: Stale version in reschedule request triggers ConflictError (optimistic locking)."""
    current_version = sample_appointment.version
    stale_version = current_version - 1  # Older version

    new_dt = (datetime.now(timezone.utc) + timedelta(days=9)).replace(hour=14, minute=0, second=0, microsecond=0, tzinfo=None)

    with pytest.raises(ConflictError) as exc_info:
        AppointmentService.reschedule_appointment(
            sample_appointment.id,
            new_datetime=new_dt,
            client_version=stale_version
        )
    assert "modified by another session" in str(exc_info.value).lower()


def test_concurrent_simultaneous_rescheduling(app, sample_appointment):
    """
    Requirement 20: Multiple concurrent requests attempting to reschedule the same appointment.
    Verifies that the database does not corrupt or deadlock and handles optimistic locking.
    """
    apt_id = sample_appointment.id
    target_times = [
        (datetime.now(timezone.utc) + timedelta(days=10, hours=i)).replace(minute=0, second=0, microsecond=0, tzinfo=None)
        for i in range(1, 6)
    ]

    success_count = 0
    conflict_count = 0

    def attempt_reschedule(target_dt):
        with app.app_context():
            try:
                # Read latest version first
                apt = db.session.get(Appointment, apt_id)
                AppointmentService.reschedule_appointment(
                    id_or_code=apt_id,
                    new_datetime=target_dt,
                    client_version=apt.version
                )
                return "success"
            except ConflictError:
                return "conflict"
            except Exception as e:
                return f"error: {e}"

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(attempt_reschedule, dt) for dt in target_times]
        for f in as_completed(futures):
            res = f.result()
            if res == "success":
                success_count += 1
            elif res == "conflict":
                conflict_count += 1

    # At least one succeeded and state remained integral
    assert success_count >= 1
    with app.app_context():
        apt = db.session.get(Appointment, apt_id)
        assert apt.version >= 2
        assert apt.status == "scheduled"


def test_concurrent_read_write_safety(app, db_session, sample_appointment):
    """
    Requirement 10 & 20: Verify SQLite WAL mode allows simultaneous reading and writing
    across concurrent worker threads without crashing.
    """
    def read_appointments():
        with app.app_context():
            res = AppointmentService.get_appointments(page=1, per_page=10)
            return len(res["appointments"])

    def create_dummy_appointment(idx):
        with app.app_context():
            dt = (datetime.now(timezone.utc) + timedelta(days=15, hours=idx)).replace(minute=0, second=0, microsecond=0, tzinfo=None)
            apt = AppointmentService.create_appointment({
                "patient_name": f"Concurrent Patient {idx}",
                "department": "Pediatrics",
                "appointment_datetime": dt
            })
            return apt.appointment_code

    with ThreadPoolExecutor(max_workers=6) as executor:
        write_futures = [executor.submit(create_dummy_appointment, i) for i in range(4)]
        read_futures = [executor.submit(read_appointments) for _ in range(4)]

        for f in as_completed(write_futures):
            code = f.result()
            assert code.startswith("APT-")

        for f in as_completed(read_futures):
            count = f.result()
            assert count >= 1
