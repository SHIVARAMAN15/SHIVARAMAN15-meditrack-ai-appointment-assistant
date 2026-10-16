from app.routes.health import health_bp
from app.routes.appointments import appointments_bp
from app.routes.chatbot import chatbot_bp
from app.routes.predictions import predictions_bp
from app.routes.reminders import reminders_bp
from app.routes.analytics import analytics_bp

__all__ = [
    "health_bp",
    "appointments_bp",
    "chatbot_bp",
    "predictions_bp",
    "reminders_bp",
    "analytics_bp"
]
