"""
Appointment service managing CRUD operations, conflict checks, and optimistic locking.
"""
from datetime import datetime, timezone, timedelta
import random
from sqlalchemy import or_, and_, desc, asc
from app.extensions import db
from app.models.appointment import Appointment
from app.models.prediction_log import PredictionLog
from app.services.prediction_service import PredictionService
from app.services.logging_service import LoggingService
from app.utils.exceptions import NotFoundError, ConflictError, BusinessRuleError, ValidationError

class AppointmentService:
    @staticmethod
    def generate_appointment_code() -> str:
        """Generate a unique human-readable appointment reference code (e.g., APT-1042)."""
        while True:
            code = f"APT-{random.randint(1000, 9999)}"
            existing = Appointment.query.filter_by(appointment_code=code).first()
            if not existing:
                return code

    @staticmethod
    def generate_patient_reference() -> str:
        """Generate a synthetic patient reference (e.g., PAT-5281)."""
        return f"PAT-{random.randint(2000, 9999)}"

    @staticmethod
    def get_appointments(
        status: str = None,
        department: str = None,
        search: str = None,
        risk_category: str = None,
        page: int = 1,
        per_page: int = 15,
        sort_by: str = "appointment_datetime",
        sort_dir: str = "asc"
    ) -> dict:
        """Retrieve paginated, filterable, and searchable list of appointments."""
        query = Appointment.query

        if status:
            query = query.filter(Appointment.status == status)

        if department:
            query = query.filter(Appointment.department == department)

        if search:
            search_term = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Appointment.patient_name.ilike(search_term),
                    Appointment.appointment_code.ilike(search_term),
                    Appointment.patient_reference.ilike(search_term)
                )
            )

        # Sorting
        sort_column = getattr(Appointment, sort_by, Appointment.appointment_datetime)
        if sort_dir.lower() == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))

        total = query.count()
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        items = []
        for apt in pagination.items:
            apt_dict = apt.to_dict(include_latest_prediction=True)
            # If filtering by risk_category
            if risk_category:
                pred = apt_dict.get("latest_prediction")
                if not pred or pred.get("risk_category") != risk_category:
                    continue
            items.append(apt_dict)

        return {
            "appointments": items,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": pagination.pages or 1,
            "has_next": pagination.has_next,
            "has_prev": pagination.has_prev
        }

    @staticmethod
    def get_appointment(id_or_code) -> Appointment:
        """Find an appointment by integer ID or public appointment_code."""
        if isinstance(id_or_code, int) or (isinstance(id_or_code, str) and id_or_code.isdigit()):
            apt = db.session.get(Appointment, int(id_or_code))
            if apt:
                return apt

        if isinstance(id_or_code, str):
            clean_code = id_or_code.strip().upper()
            apt = Appointment.query.filter(
                or_(
                    Appointment.appointment_code == clean_code,
                    Appointment.patient_reference == clean_code
                )
            ).first()
            if apt:
                return apt

        raise NotFoundError(f"Appointment '{id_or_code}' not found.")

    @staticmethod
    def check_conflicts(patient_ref: str, dt: datetime, exclude_apt_id: int = None, window_minutes: int = 30):
        """Prevent double-booking for the same patient within time window."""
        start_win = dt - timedelta(minutes=window_minutes)
        end_win = dt + timedelta(minutes=window_minutes)

        query = Appointment.query.filter(
            Appointment.patient_reference == patient_ref,
            Appointment.status == "scheduled",
            Appointment.appointment_datetime.between(start_win, end_win)
        )
        if exclude_apt_id:
            query = query.filter(Appointment.id != exclude_apt_id)

        conflicting = query.first()
        if conflicting:
            raise ConflictError(
                f"Patient has a conflicting scheduled appointment ({conflicting.appointment_code}) "
                f"at {conflicting.appointment_datetime.strftime('%Y-%m-%d %H:%M')}."
            )

    @staticmethod
    def create_appointment(data: dict) -> Appointment:
        """Create a new appointment with transaction safety and conflict detection."""
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
        apt_datetime = data["appointment_datetime"]

        if apt_datetime <= now_utc:
            raise ValidationError("Appointment datetime must be in the future.")

        patient_ref = data.get("patient_reference") or AppointmentService.generate_patient_reference()
        code = AppointmentService.generate_appointment_code()

        # Check conflicting appointments for the patient
        AppointmentService.check_conflicts(patient_ref, apt_datetime)

        appointment = Appointment(
            appointment_code=code,
            patient_reference=patient_ref,
            patient_name=data["patient_name"],
            department=data["department"],
            appointment_datetime=apt_datetime,
            status="scheduled",
            notes=data.get("notes", ""),
            version=1
        )

        try:
            db.session.add(appointment)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise BusinessRuleError(f"Database error creating appointment: {str(e)}")

        # Calculate initial prediction for new appointment
        try:
            PredictionService.predict_for_appointment(appointment.id, log_result=True)
        except Exception:
            # Non-blocking if ML model artifact is not yet ready during setup
            pass

        return appointment

    @staticmethod
    def reschedule_appointment(id_or_code, new_datetime: datetime, client_version: int = None) -> Appointment:
        """Reschedule an existing appointment with optimistic locking and validation."""
        appointment = AppointmentService.get_appointment(id_or_code)

        if appointment.status != "scheduled":
            raise BusinessRuleError(f"Cannot reschedule an appointment that is already '{appointment.status}'.")

        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
        if new_datetime <= now_utc:
            raise ValidationError("Appointment datetime must be in the future.")

        # Optimistic concurrency check
        if client_version is not None and appointment.version != client_version:
            raise ConflictError(
                "Appointment was modified by another session. Please refresh and retry."
            )

        # Conflict check
        AppointmentService.check_conflicts(
            appointment.patient_reference,
            new_datetime,
            exclude_apt_id=appointment.id
        )

        appointment.appointment_datetime = new_datetime
        appointment.version += 1
        appointment.updated_at = datetime.now(timezone.utc)

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise BusinessRuleError(f"Database error rescheduling appointment: {str(e)}")

        # Refresh attendance prediction with updated lead-time and timing
        try:
            PredictionService.predict_for_appointment(appointment.id, log_result=True)
        except Exception:
            pass

        return appointment

    @staticmethod
    def cancel_appointment(id_or_code, reason: str = None, client_version: int = None) -> Appointment:
        """Cancel an appointment safely with state validation and optimistic locking."""
        appointment = AppointmentService.get_appointment(id_or_code)

        if appointment.status == "cancelled":
            raise BusinessRuleError("Appointment is already cancelled.")

        if appointment.status in ("completed", "no_show"):
            raise BusinessRuleError(f"Cannot cancel an appointment marked as '{appointment.status}'.")

        # Optimistic concurrency check
        if client_version is not None and appointment.version != client_version:
            raise ConflictError(
                "Appointment was modified by another session. Please refresh and retry."
            )

        appointment.status = "cancelled"
        appointment.version += 1
        appointment.updated_at = datetime.now(timezone.utc)
        if reason:
            curr_notes = appointment.notes or ""
            appointment.notes = (curr_notes + f" [Cancellation Reason: {reason}]").strip()

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise BusinessRuleError(f"Database error cancelling appointment: {str(e)}")

        return appointment
