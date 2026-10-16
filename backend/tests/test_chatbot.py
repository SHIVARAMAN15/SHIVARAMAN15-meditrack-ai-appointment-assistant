from app.services.chatbot_service import ChatbotService
from app.models.interaction_log import InteractionLog

def test_chat_intent_help():
    """Verify help and greeting intent."""
    res = ChatbotService.process_message("hello, what can you do?")
    assert res["intent"] == "HELP"
    assert "MediTrack Clinic Assistant" in res["message"]


def test_chat_intent_check_prediction(sample_appointment):
    """Verify check prediction intent."""
    msg = f"What is the attendance probability for {sample_appointment.appointment_code}?"
    res = ChatbotService.process_message(msg)
    assert res["intent"] == "CHECK_PREDICTION"
    assert sample_appointment.appointment_code in res["message"]
    assert "Estimated Attendance Probability" in res["message"]
    assert "RISK" in res["message"]


def test_chat_intent_view_upcoming(sample_appointment):
    """Verify view upcoming appointments intent."""
    res = ChatbotService.process_message("Show upcoming appointments")
    assert res["intent"] == "VIEW_UPCOMING"
    assert sample_appointment.appointment_code in res["message"]


def test_chat_intent_search_appointment(sample_appointment):
    """Verify search appointment intent."""
    res = ChatbotService.process_message("Find appointment for Sarah Connor")
    assert res["intent"] == "SEARCH_APPOINTMENT"
    assert sample_appointment.appointment_code in res["message"]


def test_chat_intent_reschedule_success(sample_appointment):
    """Verify rescheduling via chatbot intent."""
    msg = f"Reschedule appointment {sample_appointment.appointment_code} to October 28, 2026 at 10:30 AM"
    res = ChatbotService.process_message(msg)
    assert res["intent"] == "RESCHEDULE_APPOINTMENT"
    assert "successfully rescheduled" in res["message"].lower()
    assert sample_appointment.appointment_code in res["message"]


def test_chat_intent_reschedule_ambiguous(sample_appointment):
    """Requirement 11: Ambiguous requests prompt clarifying questions."""
    # Missing date and time
    msg = f"Reschedule appointment {sample_appointment.appointment_code}"
    res = ChatbotService.process_message(msg)
    assert res["status"] == "ambiguous"
    assert "what new date and time" in res["message"].lower()

    # Missing appointment code
    msg2 = "Reschedule to tomorrow at 10 AM"
    res2 = ChatbotService.process_message(msg2)
    assert res2["status"] == "ambiguous"
    assert "which appointment" in res2["message"].lower()


def test_chat_intent_cancel_appointment(sample_appointment):
    """Verify cancellation via chatbot intent."""
    msg = f"Cancel appointment {sample_appointment.appointment_code}"
    res = ChatbotService.process_message(msg)
    assert res["intent"] == "CANCEL_APPOINTMENT"
    assert "has been cancelled" in res["message"].lower()


def test_chat_intent_recommend_reminders():
    """Verify reminder recommendation intent."""
    res = ChatbotService.process_message("Show reminder recommendations")
    assert res["intent"] == "RECOMMEND_REMINDERS"
    assert "reminder" in res["message"].lower()


def test_chat_intent_summarize_stats(sample_appointment):
    """Verify summary statistics intent."""
    res = ChatbotService.process_message("Summarize appointment statistics")
    assert res["intent"] == "SUMMARIZE_STATS"
    assert "MediTrack Clinic Appointment Summary" in res["message"]


def test_chat_unknown_intent_fallback():
    """Verify fallback for unsupported intent."""
    res = ChatbotService.process_message("Who won the soccer world cup?")
    assert res["intent"] == "UNSUPPORTED"
    assert res["status"] == "ambiguous"
    assert "Try asking" in res["message"]


def test_interaction_logging(db_session):
    """Requirement 17: Interactions are audited in InteractionLog."""
    initial = InteractionLog.query.count()
    ChatbotService.process_message("What can you do?", session_id="test_sess_42")
    after = InteractionLog.query.count()
    assert after == initial + 1

    entry = InteractionLog.query.order_by(InteractionLog.timestamp.desc()).first()
    assert entry.session_id == "test_sess_42"
    assert entry.intent == "HELP"
    assert "What can you do?" in entry.sanitized_user_message
