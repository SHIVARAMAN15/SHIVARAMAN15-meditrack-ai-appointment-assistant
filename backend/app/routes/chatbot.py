from flask import Blueprint, request, jsonify
from app.services.chatbot_service import ChatbotService
from app.utils.validators import validate_chat_payload

chatbot_bp = Blueprint("chatbot", __name__)

@chatbot_bp.route("/chat", methods=["POST"])
def chat():
    """Handle clinic staff chatbot queries using deterministic intent engine."""
    data = request.get_json(silent=True) or {}
    cleaned = validate_chat_payload(data)

    result = ChatbotService.process_message(
        message=cleaned["message"],
        session_id=cleaned["session_id"]
    )
    return jsonify(result), 200
