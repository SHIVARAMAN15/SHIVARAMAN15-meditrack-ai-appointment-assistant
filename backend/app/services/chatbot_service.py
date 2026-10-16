"""
Deterministic intent parsing and assistant service for clinic staff queries.
Uses structured pattern matching and entity extraction without requiring external LLM APIs.
"""
import os
import json
import logging
import urllib.request
from datetime import datetime, timezone, timedelta
import re
from flask import current_app
from app.models.appointment import Appointment
from app.services.appointment_service import AppointmentService
from app.services.prediction_service import PredictionService
from app.services.reminder_service import ReminderService
from app.services.analytics_service import AnalyticsService
from app.services.logging_service import LoggingService
from app.utils.exceptions import NotFoundError, ConflictError, BusinessRuleError, ValidationError

logger = logging.getLogger("meditrack.chatbot")

MONTH_MAP = {
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12
}

class ChatbotService:
    @staticmethod
    def get_default_clinic_context() -> dict:
        """Provide current clinic operational state for LLM grounding."""
        try:
            from flask import has_app_context
            if not has_app_context():
                return {"system_date": "2026-10-16"}
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            upcoming = Appointment.query.filter(
                Appointment.status == "scheduled",
                Appointment.appointment_datetime >= now.replace(hour=0, minute=0, second=0)
            ).order_by(Appointment.appointment_datetime.asc()).limit(10).all()
            return {
                "system_date": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
                "operational_calendar_year": now.year,
                "total_appointments_in_system": Appointment.query.count(),
                "upcoming_appointments_sample": [
                    {
                        "code": a.appointment_code,
                        "patient": a.patient_name,
                        "datetime": a.appointment_datetime.strftime("%Y-%m-%d %H:%M"),
                        "department": a.department,
                        "status": a.status
                    }
                    for a in upcoming
                ]
            }
        except Exception:
            return {"system_date": "2026-10-16"}

    @staticmethod
    def call_openrouter_llm(user_message: str, clinic_context: dict = None) -> str:
        """Call OpenRouter LLM with clinic context and guardrails."""
        try:
            api_key = (
                current_app.config.get("OPENROUTER_API_KEY")
                if current_app
                else os.getenv("OPENROUTER_API_KEY")
            )
        except Exception:
            api_key = os.getenv("OPENROUTER_API_KEY")

        if not api_key:
            return None

        try:
            model = (
                current_app.config.get("OPENROUTER_MODEL", "openai/gpt-4o")
                if current_app
                else os.getenv("OPENROUTER_MODEL", "openai/gpt-4o")
            )
        except Exception:
            model = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o")

        if clinic_context is None:
            clinic_context = ChatbotService.get_default_clinic_context()

        now_dt = datetime.now(timezone.utc).replace(tzinfo=None)
        current_date_str = now_dt.strftime("%B %d, %Y")
        system_prompt = (
            "You are MediTrack AI, the live clinical appointment assistant for MediTrack Clinic staff. "
            f"The clinic system current operational date is {current_date_str} (calendar year 2026). "
            "You have direct real-time access to the clinic's schedules and patient data provided in the Clinic Context below. "
            "CRITICAL INSTRUCTIONS: Never state that your knowledge cutoff is 2023 or that you cannot access 2026 or future appointments. "
            "If staff asks about appointments, schedules, patients, or no-show risks, answer using the provided clinic context, "
            "or guide them to ask for specific dates, patient names, or appointment IDs (e.g. APT-1001). "
            "Keep your responses concise, professional, accurate, and formatted in clean markdown."
        )
        if clinic_context:
            system_prompt += f"\n\nClinic Context:\n{json.dumps(clinic_context, indent=2)}"

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "temperature": 0.3,
            "max_tokens": 500
        }

        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:5173",
                "X-Title": "MediTrack AI Clinical Assistant"
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.warning(f"OpenRouter API call failed or timed out: {e}")
            return None

    @staticmethod
    def parse_date_token(token: str, default_year: int = 2026):
        """Parse varied date formats (DD.MM.YYYY, YYYY-MM-DD, Month DD YYYY)."""
        if not token:
            return None
        token = token.strip()

        # 1. DD.MM.YYYY, DD/MM/YYYY, DD-MM-YYYY
        m = re.match(r"^(\d{1,2})[\.\/\-](\d{1,2})[\.\/\-](\d{2,4})$", token)
        if m:
            p1, p2, yr = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if yr < 100:
                yr += 2000
            # If p2 > 12 >= p1 -> MM/DD, else DD/MM (European / standard clinic convention)
            if p2 > 12 >= p1:
                mth, day = p1, p2
            else:
                day, mth = p1, p2
            try:
                return datetime(yr, mth, day)
            except ValueError:
                pass

        # 2. YYYY-MM-DD, YYYY/MM/DD
        m = re.match(r"^(\d{4})[\.\/\-](\d{1,2})[\.\/\-](\d{1,2})$", token)
        if m:
            try:
                return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            except ValueError:
                pass

        # 3. Month DD, YYYY or Month DD
        m = re.match(r"^(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)\s+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s+(\d{4}))?$", token, re.I)
        if m:
            mth = MONTH_MAP[m.group(1).lower()]
            day = int(m.group(2))
            yr = int(m.group(3)) if m.group(3) else default_year
            try:
                return datetime(yr, mth, day)
            except ValueError:
                pass

        # 4. DD Month YYYY or DD Month
        m = re.match(r"^(\d{1,2})(?:st|nd|rd|th)?\s+(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)(?:,?\s+(\d{4}))?$", token, re.I)
        if m:
            day = int(m.group(1))
            mth = MONTH_MAP[m.group(2).lower()]
            yr = int(m.group(3)) if m.group(3) else default_year
            try:
                return datetime(yr, mth, day)
            except ValueError:
                pass

        return None

    @staticmethod
    def extract_date_range(text: str):
        """Extract start and end datetime bounds from user text."""
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        lower = text.lower()

        # Relative shortcuts
        if "tomorrow" in lower:
            t = now + timedelta(days=1)
            return datetime(t.year, t.month, t.day, 0, 0, 0), datetime(t.year, t.month, t.day, 23, 59, 59)
        if "today" in lower:
            return datetime(now.year, now.month, now.day, 0, 0, 0), datetime(now.year, now.month, now.day, 23, 59, 59)
        if "yesterday" in lower:
            y = now - timedelta(days=1)
            return datetime(y.year, y.month, y.day, 0, 0, 0), datetime(y.year, y.month, y.day, 23, 59, 59)
        if "this week" in lower:
            start = now - timedelta(days=now.weekday())
            end = start + timedelta(days=6)
            return datetime(start.year, start.month, start.day, 0, 0, 0), datetime(end.year, end.month, end.day, 23, 59, 59)
        if "next week" in lower:
            start = now - timedelta(days=now.weekday()) + timedelta(days=7)
            end = start + timedelta(days=6)
            return datetime(start.year, start.month, start.day, 0, 0, 0), datetime(end.year, end.month, end.day, 23, 59, 59)

        # 1. Range with numbers: e.g. 16.10.2026 to 20.10.2026 or 16.10.2026 - 20.10.2026
        date_pat = r"(?:\d{1,2}[\.\/\-]\d{1,2}[\.\/\-]\d{2,4}|\d{4}[\.\/\-]\d{1,2}[\.\/\-]\d{1,2})"
        range_match = re.search(rf"({date_pat})\s*(?:to|until|through|-|\sand\s)\s*({date_pat})", text, re.I)
        if range_match:
            d1 = ChatbotService.parse_date_token(range_match.group(1), now.year)
            d2 = ChatbotService.parse_date_token(range_match.group(2), now.year)
            if d1 and d2:
                start = datetime(d1.year, d1.month, d1.day, 0, 0, 0)
                end = datetime(d2.year, d2.month, d2.day, 23, 59, 59)
                if start > end:
                    start, end = end, start
                return start, end

        # 2. Range with words: e.g. Oct 16 to Oct 20
        word_date_pat = r"(?:[a-zA-Z]+\s+\d{1,2}(?:st|nd|rd|th)?(?:,?\s*\d{4})?|\d{1,2}(?:st|nd|rd|th)?\s+[a-zA-Z]+(?:,?\s*\d{4})?)"
        range_word_match = re.search(rf"({word_date_pat})\s*(?:to|until|through|-|\sand\s)\s*({word_date_pat})", text, re.I)
        if range_word_match:
            d1 = ChatbotService.parse_date_token(range_word_match.group(1), now.year)
            d2 = ChatbotService.parse_date_token(range_word_match.group(2), now.year)
            if d1 and d2:
                start = datetime(d1.year, d1.month, d1.day, 0, 0, 0)
                end = datetime(d2.year, d2.month, d2.day, 23, 59, 59)
                if start > end:
                    start, end = end, start
                return start, end

        # 3. Single numeric date: e.g. 16.10.2026
        single_num = re.search(rf"({date_pat})", text, re.I)
        if single_num:
            d = ChatbotService.parse_date_token(single_num.group(1), now.year)
            if d:
                return datetime(d.year, d.month, d.day, 0, 0, 0), datetime(d.year, d.month, d.day, 23, 59, 59)

        # 4. Single word date: e.g. October 16, 2026
        single_word = re.search(rf"({word_date_pat})", text, re.I)
        if single_word:
            d = ChatbotService.parse_date_token(single_word.group(1), now.year)
            if d:
                return datetime(d.year, d.month, d.day, 0, 0, 0), datetime(d.year, d.month, d.day, 23, 59, 59)

        return None, None

    @staticmethod
    def extract_appointment_code(text: str) -> str:
        """Find APT-XXXX pattern."""
        match = re.search(r"\b(APT-\d{4})\b", text, re.IGNORECASE)
        return match.group(1).upper() if match else None

    @staticmethod
    def extract_patient_reference(text: str) -> str:
        """Find PAT-XXXX pattern."""
        match = re.search(r"\b(PAT-\d{4})\b", text, re.IGNORECASE)
        return match.group(1).upper() if match else None

    @staticmethod
    def extract_datetime(text: str) -> datetime:
        """
        Parse natural date/time strings such as:
        - 'October 22, 2026 at 10:30 AM'
        - '2026-10-22 14:00'
        - 'tomorrow at 11:00 AM'
        - 'today at 3:00 PM'
        """
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        lower = text.lower()

        # Check relative days
        target_date = None
        if "tomorrow" in lower:
            target_date = (now + timedelta(days=1)).date()
        elif "today" in lower:
            target_date = now.date()
        elif "in 2 days" in lower or "in two days" in lower:
            target_date = (now + timedelta(days=2)).date()

        # Check ISO format YYYY-MM-DD
        iso_match = re.search(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", text)
        if iso_match:
            try:
                target_date = datetime(int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3))).date()
            except ValueError:
                pass

        # Check Month Day, Year (e.g. October 22, 2026 or Oct 22 2026)
        month_match = re.search(
            r"\b(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)\s+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s+(\d{4}))?\b",
            lower
        )
        if month_match and not target_date:
            m_str, d_str, y_str = month_match.group(1), month_match.group(2), month_match.group(3)
            m = MONTH_MAP.get(m_str, 10)
            d = int(d_str)
            y = int(y_str) if y_str else now.year
            try:
                target_date = datetime(y, m, d).date()
            except ValueError:
                pass

        # Check Time (e.g. 10:30 AM, 14:00, 9am, 2:30 pm)
        hour = 10
        minute = 0
        time_match = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", lower)
        # Verify it's preceded by 'at' or contains am/pm or has colon
        time_explicit = re.search(r"(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)", lower) or re.search(r"(?:at\s+)(\d{1,2}):(\d{2})", lower)
        if time_explicit:
            raw_h = int(time_explicit.group(1))
            raw_m = int(time_explicit.group(2)) if time_explicit.group(2) else 0
            meridiem = time_explicit.group(3) if len(time_explicit.groups()) >= 3 else None

            if meridiem:
                if meridiem.lower() == "pm" and raw_h < 12:
                    raw_h += 12
                elif meridiem.lower() == "am" and raw_h == 12:
                    raw_h = 0
            hour = raw_h
            minute = raw_m

        if target_date:
            return datetime(target_date.year, target_date.month, target_date.day, hour, minute)

        return None

    @staticmethod
    def process_message(message: str, session_id: str = "staff_session") -> dict:
        """
        Process a staff message using deterministic intent matching.
        Executes real backend services and returns structured response.
        """
        raw_msg = (message or "").strip()
        lower = raw_msg.lower()

        intent = "UNKNOWN"
        response_text = ""
        data_payload = None
        status = "success"
        error_category = None
        date_range_start, date_range_end = ChatbotService.extract_date_range(raw_msg)
        has_appt_keyword = bool(re.search(r"\b(appoint|appoinment|apointment|appt|schedule)\b", lower))
        has_view_action = bool(re.search(r"\b(show|view|list|get|see|check|display|fetch|recent|upcoming|latest)\b", lower))

        try:
            # 1. HELP / GREETING
            if lower in ("hi", "hello", "hey", "help", "commands") or "what can you do" in lower:
                intent = "HELP"
                response_text = (
                    "Hello! I am your MediTrack Clinic Assistant. I can help you manage appointments, "
                    "check attendance probabilities, and review reminder recommendations. Here are some things you can ask me:\n\n"
                    "• **View upcoming appointments**: `Show tomorrow's appointments` or `List upcoming appointments`\n"
                    "• **Search appointments**: `Find appointment for Sarah` or `Look up APT-1001`\n"
                    "• **Check no-show risk**: `What is the attendance probability for APT-1001?`\n"
                    "• **Identify high risk**: `Which appointments have a high no-show risk?`\n"
                    "• **Recommend reminders**: `Show reminder recommendations`\n"
                    "• **Reschedule appointment**: `Reschedule appointment APT-1001 to October 25, 2026 at 10:30 AM`\n"
                    "• **Cancel appointment**: `Cancel appointment APT-1001`\n"
                    "• **Clinic statistics**: `Summarize appointment statistics`"
                )

            # 2. CHECK PREDICTION / ATTENDANCE PROBABILITY
            elif (
                "attendance probability" in lower or
                "show up" in lower or
                "likelihood" in lower or
                "no-show risk" in lower or
                "no show risk" in lower or
                "risk for" in lower
            ) and ChatbotService.extract_appointment_code(raw_msg):
                intent = "CHECK_PREDICTION"
                code = ChatbotService.extract_appointment_code(raw_msg)
                apt = AppointmentService.get_appointment(code)
                pred = PredictionService.get_latest_prediction(apt.id)

                attend_pct = f"{pred['attendance_probability'] * 100:.1f}%"
                noshow_pct = f"{pred['no_show_probability'] * 100:.1f}%"
                risk_cat = pred["risk_category"].upper()

                response_text = (
                    f"**Attendance Prediction for {apt.appointment_code}** ({apt.patient_name}):\n\n"
                    f"• **Estimated Attendance Probability**: **{attend_pct}**\n"
                    f"• **Predicted No-Show Probability**: **{noshow_pct}**\n"
                    f"• **Risk Category**: **{risk_cat} RISK**\n"
                    f"• **Department**: {apt.department}\n"
                    f"• **Scheduled Date**: {apt.appointment_datetime.strftime('%B %d, %Y at %I:%M %p')}\n\n"
                    f"_Note: This is an empirical ML statistical estimate based on lead time, previous visits, and historical clinic trends, not a clinical certainty._"
                )
                data_payload = {"appointment": apt.to_dict(), "prediction": pred}

            # 3. LIST HIGH-RISK APPOINTMENTS
            elif (
                "high risk" in lower or
                "high no-show" in lower or
                "high no show" in lower or
                "at risk" in lower
            ):
                intent = "LIST_HIGH_RISK"
                recommendations = ReminderService.get_recommendations()
                high_risk = [r for r in recommendations if r.get("risk_category") == "high"]

                if not high_risk:
                    response_text = "Good news! There are currently no upcoming appointments flagged with high no-show risk (>= 60%)."
                else:
                    response_text = f"Found **{len(high_risk)} upcoming appointment(s)** with high predicted no-show risk:\n\n"
                    for r in high_risk[:5]:
                        dt = datetime.fromisoformat(r["appointment_datetime"])
                        response_text += (
                            f"• **{r['appointment_code']}** - {r['patient_name']} ({r['department']})\n"
                            f"  Date: {dt.strftime('%b %d, %Y %I:%M %p')} | No-Show Risk: **{r['no_show_probability']*100:.1f}%** (HIGH)\n"
                        )
                    if len(high_risk) > 5:
                        response_text += f"\n_...and {len(high_risk) - 5} more. View the Reminder Center or Appointments tab for full details._"
                data_payload = {"high_risk_appointments": high_risk}

            # 4. RECOMMEND REMINDERS
            elif "remind" in lower or "recommendation" in lower:
                intent = "RECOMMEND_REMINDERS"
                recs = ReminderService.get_recommendations()
                if not recs:
                    response_text = "There are currently no upcoming appointments requiring automated reminders based on risk thresholds."
                else:
                    response_text = f"**Reminder Recommendations ({len(recs)} appointment(s) identified)**:\n\n"
                    for r in recs[:4]:
                        response_text += (
                            f"• **{r['appointment_code']}** ({r['patient_name']}): {r['reason']}\n"
                            f"  Status: {'Already notified recently' if r['already_reminded_recently'] else 'Ready to send simulation'}\n"
                        )
                    response_text += "\nYou can preview and trigger simulated reminders directly in the **Reminder Center** tab."
                data_payload = {"recommendations": recs}

            # 5. RESCHEDULE APPOINTMENT
            elif "reschedule" in lower or "move appointment" in lower or "postpone" in lower:
                intent = "RESCHEDULE_APPOINTMENT"
                code = ChatbotService.extract_appointment_code(raw_msg)
                new_dt = ChatbotService.extract_datetime(raw_msg)

                if not code:
                    status = "ambiguous"
                    response_text = (
                        "Which appointment would you like to reschedule? "
                        "Please provide the appointment code (e.g., `APT-1001`) and the desired new date and time."
                    )
                elif not new_dt:
                    apt = AppointmentService.get_appointment(code)
                    status = "ambiguous"
                    response_text = (
                        f"I located appointment **{apt.appointment_code}** for **{apt.patient_name}** "
                        f"(currently {apt.appointment_datetime.strftime('%B %d, %Y at %I:%M %p')}).\n\n"
                        "What new date and time would you like to move it to? (e.g., `October 28, 2026 at 10:30 AM`)"
                    )
                else:
                    # Execute actual rescheduling
                    updated_apt = AppointmentService.reschedule_appointment(code, new_dt)
                    formatted_dt = updated_apt.appointment_datetime.strftime("%B %d, %Y at %I:%M %p")
                    response_text = (
                        f"✅ **Appointment {updated_apt.appointment_code} successfully rescheduled!**\n\n"
                        f"• **Patient**: {updated_apt.patient_name}\n"
                        f"• **New Date & Time**: **{formatted_dt}**\n"
                        f"• **Department**: {updated_apt.department}\n"
                        f"• **Status**: {updated_apt.status.capitalize()}\n\n"
                        f"Attendance probabilities and lead-time features have been refreshed automatically."
                    )
                    data_payload = {"appointment": updated_apt.to_dict()}

            # 6. CANCEL APPOINTMENT
            elif (
                ("cancel" in lower or "cancellation" in lower) and
                not any(w in lower for w in ["what", "how", "why", "policy", "protocol", "procedure", "guideline", "advise"])
            ) or (
                ("cancel" in lower or "cancellation" in lower) and
                ChatbotService.extract_appointment_code(raw_msg)
            ):
                intent = "CANCEL_APPOINTMENT"
                code = ChatbotService.extract_appointment_code(raw_msg)

                if not code:
                    status = "ambiguous"
                    response_text = (
                        "Which appointment would you like to cancel? "
                        "Please specify the appointment code (e.g., `APT-1001`)."
                    )
                else:
                    cancelled_apt = AppointmentService.cancel_appointment(code, reason="Cancelled via staff chat assistant")
                    response_text = (
                        f"🛑 **Appointment {cancelled_apt.appointment_code} has been cancelled.**\n\n"
                        f"• **Patient**: {cancelled_apt.patient_name}\n"
                        f"• **Department**: {cancelled_apt.department}\n"
                        f"• **Scheduled Time**: {cancelled_apt.appointment_datetime.strftime('%B %d, %Y at %I:%M %p')}\n"
                        f"• **Status**: Cancelled\n\n"
                        f"The slot is now freed in the schedule and excluded from future reminder queues."
                    )
                    data_payload = {"appointment": cancelled_apt.to_dict()}

            # 7. VIEW APPOINTMENTS (Upcoming, Recent, Date Range, Specific Date)
            elif (
                (date_range_start is not None and (has_appt_keyword or has_view_action or "between" in lower or "from" in lower or "to" in lower)) or
                ("upcoming" in lower or "tomorrow" in lower or "today" in lower or "this week" in lower or "next week" in lower) or
                ("recent" in lower and (has_appt_keyword or has_view_action)) or
                ("latest" in lower and (has_appt_keyword or has_view_action)) or
                (has_view_action and has_appt_keyword)
            ):
                intent = "VIEW_UPCOMING"
                now = datetime.now(timezone.utc).replace(tzinfo=None)

                if date_range_start and date_range_end:
                    apts = Appointment.query.filter(
                        Appointment.appointment_datetime.between(date_range_start, date_range_end)
                    ).order_by(Appointment.appointment_datetime.asc()).limit(15).all()

                    if date_range_start.date() == date_range_end.date():
                        period_label = f"on {date_range_start.strftime('%B %d, %Y')}"
                    else:
                        period_label = f"between {date_range_start.strftime('%b %d, %Y')} and {date_range_end.strftime('%b %d, %Y')}"
                elif "recent" in lower or "latest" in lower:
                    # Look for appointments from start of today (October 16, 2026) onwards or recent records
                    today_start = datetime(now.year, now.month, now.day, 0, 0, 0)
                    apts = Appointment.query.filter(
                        Appointment.appointment_datetime >= today_start
                    ).order_by(Appointment.appointment_datetime.asc()).limit(8).all()
                    period_label = f"from today ({now.strftime('%b %d, %Y')}) onwards"

                    if not apts:
                        # Fallback to most recent in DB
                        apts = Appointment.query.order_by(Appointment.appointment_datetime.desc()).limit(8).all()
                        period_label = "in recent clinic records"
                else:
                    apts = Appointment.query.filter(
                        Appointment.status == "scheduled",
                        Appointment.appointment_datetime > now
                    ).order_by(Appointment.appointment_datetime.asc()).limit(8).all()
                    period_label = "upcoming"

                if not apts:
                    response_text = f"No scheduled appointments found {period_label}."
                else:
                    response_text = f"Found **{len(apts)} appointment(s)** {period_label}:\n\n"
                    for apt in apts:
                        dt_str = apt.appointment_datetime.strftime("%b %d, %Y at %I:%M %p")
                        pred = PredictionService.get_latest_prediction(apt.id)
                        risk_tag = f"[{pred['risk_category'].upper()} RISK]" if pred else ""
                        status_tag = f"({apt.status.capitalize()})" if apt.status != "scheduled" else ""
                        response_text += f"• **{apt.appointment_code}**: {apt.patient_name} — {dt_str} | {apt.department} {status_tag} {risk_tag}\n"
                    if len(apts) >= 15:
                        response_text += "\n_Showing first 15 matches. Refine your query or check the Appointments tab to see full records._"

                data_payload = {"appointments": [a.to_dict() for a in apts]}

            # 8. SEARCH FOR APPOINTMENT
            elif "search" in lower or "find" in lower or "look up" in lower or "who is" in lower:
                intent = "SEARCH_APPOINTMENT"
                code = ChatbotService.extract_appointment_code(raw_msg)
                pat_ref = ChatbotService.extract_patient_reference(raw_msg)

                # Clean search phrase
                cleaned_query = re.sub(r"\b(search|find|look up|for|patient|appointment)\b", "", lower).strip()

                if code:
                    apt = AppointmentService.get_appointment(code)
                    results = [apt]
                elif pat_ref:
                    results = Appointment.query.filter_by(patient_reference=pat_ref).all()
                elif cleaned_query:
                    results = Appointment.query.filter(
                        Appointment.patient_name.ilike(f"%{cleaned_query}%")
                    ).limit(5).all()
                else:
                    results = []

                if not results:
                    response_text = f"No appointments matching '{raw_msg}' were found in the clinic database."
                else:
                    response_text = f"Found **{len(results)} matching appointment(s)**:\n\n"
                    for a in results:
                        response_text += (
                            f"• **{a.appointment_code}** ({a.patient_reference}) — **{a.patient_name}**\n"
                            f"  {a.appointment_datetime.strftime('%B %d, %Y at %I:%M %p')} | {a.department} | Status: {a.status.capitalize()}\n"
                        )
                data_payload = {"results": [a.to_dict() for a in results]}

            # 9. SUMMARIZE CLINIC STATS
            elif (
                "statistic" in lower or
                "clinic summary" in lower or
                "appointment summary" in lower or
                "overview of appointments" in lower or
                lower in ("stats", "summary", "overview", "metrics", "clinic stats")
            ):
                intent = "SUMMARIZE_STATS"
                summary = AnalyticsService.get_dashboard_summary()
                response_text = (
                    "📊 **MediTrack Clinic Appointment Summary**:\n\n"
                    f"• **Total Recorded Appointments**: {summary['total_appointments']}\n"
                    f"• **Scheduled (Active)**: {summary['scheduled_appointments']}\n"
                    f"• **Completed**: {summary['completed_appointments']}\n"
                    f"• **Cancelled**: {summary['cancelled_appointments']}\n"
                    f"• **Recorded No-Shows**: {summary['no_show_appointments']}\n"
                    f"• **Historical No-Show Rate**: **{summary['historical_no_show_rate']}%**\n"
                    f"• **Upcoming Appointments**: {summary['upcoming_appointments']}\n"
                    f"• **High-Risk Upcoming**: **{summary['high_risk_appointments']}**\n"
                    f"• **Simulated Reminders Dispatched**: {summary['total_reminders_sent']}"
                )
                data_payload = {"summary": summary}

            # 10. OPENROUTER AI OR FALLBACK
            else:
                llm_reply = ChatbotService.call_openrouter_llm(raw_msg)
                if llm_reply:
                    intent = "AI_ASSISTANT"
                    status = "success"
                    response_text = llm_reply
                else:
                    intent = "UNSUPPORTED"
                    status = "ambiguous"
                    response_text = (
                        "I didn't quite catch that. As the MediTrack Staff Assistant, I can help you view upcoming appointments, "
                        "search by patient name or ID, check no-show probability, reschedule or cancel appointments, and review reminder recommendations.\n\n"
                        "Try asking: `Show tomorrow's appointments`, `Reschedule APT-1001 to next Monday at 10 AM`, or `Which appointments have high risk?`"
                    )

        except NotFoundError as e:
            status = "failure"
            error_category = "NOT_FOUND"
            response_text = f"🔍 {e.message}"
        except ConflictError as e:
            status = "failure"
            error_category = "CONFLICT"
            response_text = f"⚠️ Conflict: {e.message}"
        except (BusinessRuleError, ValidationError) as e:
            status = "failure"
            error_category = "VALIDATION"
            response_text = f"❌ Request rejected: {e.message}"
        except Exception as e:
            status = "failure"
            error_category = "SYSTEM_ERROR"
            response_text = f"An unexpected error occurred while processing your request. Please try again or check system status."

        # Audit log interaction
        LoggingService.log_interaction(
            session_id=session_id,
            actor="staff_demo",
            intent=intent,
            sanitized_user_message=raw_msg,
            response_summary=response_text[:400],
            status=status,
            error_category=error_category
        )

        return {
            "intent": intent,
            "status": status,
            "message": response_text,
            "data": data_payload,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
