"""
Analytics service computing clinic appointment metrics, no-show trends, and risk distributions.
"""
from datetime import datetime, timezone, timedelta
from sqlalchemy import func
from app.extensions import db
from app.models.appointment import Appointment
from app.models.prediction_log import PredictionLog
from app.models.reminder_log import ReminderLog
from app.services.prediction_service import PredictionService

class AnalyticsService:
    @staticmethod
    def get_dashboard_summary() -> dict:
        """Calculate real-time operational KPI summary metrics."""
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        # Basic counts
        total_apts = Appointment.query.count()
        scheduled_apts = Appointment.query.filter_by(status="scheduled").count()
        completed_apts = Appointment.query.filter_by(status="completed").count()
        cancelled_apts = Appointment.query.filter_by(status="cancelled").count()
        no_show_apts = Appointment.query.filter_by(status="no_show").count()

        # Historical completed outcomes denominator: completed + no_show
        historical_resolved = completed_apts + no_show_apts
        historical_no_show_rate = (
            round((no_show_apts / historical_resolved) * 100, 1)
            if historical_resolved > 0 else 0.0
        )

        # Upcoming appointments
        upcoming_count = Appointment.query.filter(
            Appointment.status == "scheduled",
            Appointment.appointment_datetime > now
        ).count()

        # Total reminders sent
        total_reminders_sent = ReminderLog.query.filter_by(status="sent").count()

        # Calculate high-risk upcoming appointments
        upcoming_scheduled = Appointment.query.filter(
            Appointment.status == "scheduled",
            Appointment.appointment_datetime > now
        ).all()

        high_risk_count = 0
        for apt in upcoming_scheduled:
            pred = PredictionService.get_latest_prediction(apt.id)
            if pred and pred.get("risk_category") == "high":
                high_risk_count += 1

        return {
            "total_appointments": total_apts,
            "scheduled_appointments": scheduled_apts,
            "completed_appointments": completed_apts,
            "cancelled_appointments": cancelled_apts,
            "no_show_appointments": no_show_apts,
            "historical_no_show_rate": historical_no_show_rate,
            "upcoming_appointments": upcoming_count,
            "high_risk_appointments": high_risk_count,
            "total_reminders_sent": total_reminders_sent
        }

    @staticmethod
    def get_trends() -> dict:
        """Calculate trend data for charts (attendance vs no-show, risk breakdown, timeline)."""
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        # 1. Outcomes breakdown (historical)
        completed = Appointment.query.filter_by(status="completed").count()
        no_show = Appointment.query.filter_by(status="no_show").count()
        scheduled = Appointment.query.filter_by(status="scheduled").count()
        cancelled = Appointment.query.filter_by(status="cancelled").count()

        outcomes = [
            {"name": "Completed", "value": completed, "color": "#10b981"},
            {"name": "No-Show", "value": no_show, "color": "#ef4444"},
            {"name": "Scheduled", "value": scheduled, "color": "#3b82f6"},
            {"name": "Cancelled", "value": cancelled, "color": "#94a3b8"}
        ]

        # 2. Risk distribution across upcoming scheduled appointments
        upcoming = Appointment.query.filter(
            Appointment.status == "scheduled",
            Appointment.appointment_datetime > now
        ).all()

        risk_counts = {"low": 0, "medium": 0, "high": 0}
        for apt in upcoming:
            pred = PredictionService.get_latest_prediction(apt.id)
            cat = pred.get("risk_category", "low")
            if cat in risk_counts:
                risk_counts[cat] += 1
            else:
                risk_counts["low"] += 1

        risk_distribution = [
            {"category": "Low Risk (<30%)", "count": risk_counts["low"], "color": "#10b981"},
            {"category": "Medium Risk (30-60%)", "count": risk_counts["medium"], "color": "#f59e0b"},
            {"category": "High Risk (>=60%)", "count": risk_counts["high"], "color": "#ef4444"}
        ]

        # 3. 7-Day daily appointment volume trends
        # Gather appointments in the window (-3 days to +4 days)
        start_win = (now - timedelta(days=3)).replace(hour=0, minute=0, second=0)
        end_win = (now + timedelta(days=5)).replace(hour=23, minute=59, second=59)

        apts_in_window = Appointment.query.filter(
            Appointment.appointment_datetime.between(start_win, end_win)
        ).all()

        daily_map = {}
        # Prepopulate days
        for i in range(-3, 5):
            d = (now + timedelta(days=i)).strftime("%Y-%m-%d")
            daily_map[d] = {"date": d, "scheduled": 0, "completed": 0, "no_show": 0, "cancelled": 0}

        for apt in apts_in_window:
            d_str = apt.appointment_datetime.strftime("%Y-%m-%d")
            if d_str in daily_map:
                st = apt.status
                if st in daily_map[d_str]:
                    daily_map[d_str][st] += 1

        daily_trends = sorted(list(daily_map.values()), key=lambda x: x["date"])

        # 4. Department breakdown
        dept_counts = db.session.query(
            Appointment.department,
            func.count(Appointment.id)
        ).group_by(Appointment.department).all()

        department_breakdown = [
            {"department": dept, "count": count} for dept, count in dept_counts
        ]

        return {
            "outcomes": outcomes,
            "risk_distribution": risk_distribution,
            "daily_trends": daily_trends,
            "department_breakdown": department_breakdown
        }
