import os
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
import pytest

# Ensure backend directory is in python path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app import create_app
from app.config import TestingConfig
from app.extensions import db
from app.models.appointment import Appointment
from app.models.prediction_log import PredictionLog
from app.models.reminder_log import ReminderLog
from app.models.interaction_log import InteractionLog

@pytest.fixture(scope="session")
def app():
    """Create session-wide application for testing."""
    test_app = create_app(TestingConfig)
    with test_app.app_context():
        db.create_all()
        yield test_app
        db.session.remove()
        db.drop_all()

    # Clean up test database file if created
    test_db = backend_dir / "test_meditrack.db"
    if test_db.exists():
        try:
            os.remove(test_db)
        except Exception:
            pass


@pytest.fixture(scope="function")
def client(app):
    """Test HTTP client."""
    return app.test_client()


@pytest.fixture(scope="function")
def db_session(app):
    """Clean database state before each test function."""
    with app.app_context():
        # Clear tables
        InteractionLog.query.delete()
        ReminderLog.query.delete()
        PredictionLog.query.delete()
        Appointment.query.delete()
        db.session.commit()
        yield db.session
        db.session.rollback()


@pytest.fixture
def sample_appointment(db_session):
    """Create a sample future appointment."""
    future_dt = (datetime.now(timezone.utc) + timedelta(days=5)).replace(hour=10, minute=0, second=0, microsecond=0, tzinfo=None)
    apt = Appointment(
        appointment_code="APT-1001",
        patient_reference="PAT-2001",
        patient_name="Sarah Connor",
        department="Cardiology",
        appointment_datetime=future_dt,
        status="scheduled",
        notes="Pre-op cardiac checkup",
        version=1
    )
    db_session.add(apt)
    db_session.commit()
    return apt
