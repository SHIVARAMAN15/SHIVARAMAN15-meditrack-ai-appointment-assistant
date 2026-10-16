"""
Database seeding script with realistic synthetic patient appointment records.
Populates historical outcomes, upcoming slots, ML predictions, and simulated reminders.
"""
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
import random

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app import create_app
from app.extensions import db
from app.models.appointment import Appointment
from app.models.prediction_log import PredictionLog
from app.models.reminder_log import ReminderLog
from app.services.prediction_service import PredictionService
from app.services.reminder_service import ReminderService
from app.utils.validators import ALLOWED_DEPARTMENTS

FIRST_NAMES = [
    "James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael", "Linda",
    "David", "Elizabeth", "William", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
    "Thomas", "Sarah", "Charles", "Karen", "Christopher", "Nancy", "Daniel", "Lisa",
    "Matthew", "Betty", "Anthony", "Margaret", "Mark", "Sandra", "Donald", "Ashley",
    "Steven", "Kimberly", "Paul", "Emily", "Andrew", "Donna", "Joshua", "Michelle"
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson", "White"
]

def generate_patient_pool(num_patients=25):
    """Generate reusable synthetic patient identities."""
    patients = []
    for i in range(num_patients):
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        pat_ref = f"PAT-{2000 + i}"
        patients.append({
            "name": f"{first} {last}",
            "ref": pat_ref,
            # Assign intrinsic reliability archetype
            "archetype": random.choice(["reliable", "reliable", "occasional_miss", "high_risk"])
        })
    return patients


def seed_database(clear_existing=True):
    """Seed synthetic appointments and predictions."""
    app = create_app()
    with app.app_context():
        if clear_existing:
            print("Clearing existing database tables...")
            db.drop_all()
            db.create_all()

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        patients = generate_patient_pool(30)

        appointments_to_add = []
        apt_counter = 1001

        print("Generating historical appointments...")
        # 1. Historical appointments (30 days ago to yesterday)
        for i in range(35):
            pat = random.choice(patients)
            days_ago = random.randint(1, 30)
            hour = random.choice([9, 10, 11, 13, 14, 15, 16])
            apt_dt = (now - timedelta(days=days_ago)).replace(hour=hour, minute=0, second=0)
            created_at = apt_dt - timedelta(days=random.randint(2, 21))

            # Outcome determined by archetype
            if pat["archetype"] == "high_risk":
                status = random.choice(["no_show", "no_show", "completed", "cancelled"])
            elif pat["archetype"] == "occasional_miss":
                status = random.choice(["completed", "completed", "no_show", "cancelled"])
            else:
                status = "completed"

            apt = Appointment(
                appointment_code=f"APT-{apt_counter}",
                patient_reference=pat["ref"],
                patient_name=pat["name"],
                department=random.choice(ALLOWED_DEPARTMENTS),
                appointment_datetime=apt_dt,
                status=status,
                notes="Historical clinic visit record",
                version=1,
                created_at=created_at,
                updated_at=apt_dt
            )
            appointments_to_add.append(apt)
            apt_counter += 1

        print("Generating upcoming appointments...")
        # 2. Upcoming appointments (tomorrow to 14 days ahead)
        for i in range(25):
            pat = random.choice(patients)
            days_ahead = random.randint(1, 14)
            hour = random.choice([8, 9, 10, 11, 13, 14, 15, 16, 17])
            minute = random.choice([0, 15, 30, 45])
            apt_dt = (now + timedelta(days=days_ahead)).replace(hour=hour, minute=minute, second=0)
            created_at = now - timedelta(days=random.randint(1, 10))

            dept = random.choice(ALLOWED_DEPARTMENTS)
            notes = "Standard consultation" if random.random() > 0.3 else "Follow-up review"

            apt = Appointment(
                appointment_code=f"APT-{apt_counter}",
                patient_reference=pat["ref"],
                patient_name=pat["name"],
                department=dept,
                appointment_datetime=apt_dt,
                status="scheduled",
                notes=notes,
                version=1,
                created_at=created_at,
                updated_at=now
            )
            appointments_to_add.append(apt)
            apt_counter += 1

        db.session.add_all(appointments_to_add)
        db.session.commit()
        print(f"Successfully inserted {len(appointments_to_add)} synthetic appointments.")

        # 3. Compute initial ML predictions for all appointments
        print("Computing and logging initial ML predictions...")
        all_apts = Appointment.query.all()
        for apt in all_apts:
            try:
                PredictionService.predict_for_appointment(apt.id, log_result=True)
            except Exception as e:
                # If model not trained yet, handle gracefully
                pass

        # 4. Generate a few sample simulated reminder logs
        print("Generating sample simulated reminder logs...")
        sample_upcoming = Appointment.query.filter_by(status="scheduled").limit(3).all()
        for apt in sample_upcoming:
            try:
                msg = ReminderService.format_reminder_message(apt)
                entry = ReminderLog(
                    appointment_id=apt.id,
                    reminder_channel="simulated_sms",
                    simulated_message=msg,
                    status="sent",
                    attempt_count=1,
                    created_at=now - timedelta(hours=random.randint(2, 12)),
                    sent_at=now - timedelta(hours=random.randint(2, 12))
                )
                db.session.add(entry)
            except Exception:
                pass
        db.session.commit()

        print("Database seeding completed successfully!")

if __name__ == "__main__":
    seed_database()
