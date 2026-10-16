from flask import Blueprint, jsonify, request
from app.services.analytics_service import AnalyticsService
from app.models.interaction_log import InteractionLog

analytics_bp = Blueprint("analytics", __name__)

@analytics_bp.route("/analytics/summary", methods=["GET"])
def get_summary():
    """Retrieve high-level clinic KPI counts and historical no-show rates."""
    summary = AnalyticsService.get_dashboard_summary()
    return jsonify(summary), 200


@analytics_bp.route("/analytics/trends", methods=["GET"])
def get_trends():
    """Retrieve chart trend data: outcomes breakdown, risk distribution, daily trends."""
    trends = AnalyticsService.get_trends()
    return jsonify(trends), 200


@analytics_bp.route("/logs", methods=["GET"])
def get_interaction_logs():
    """Retrieve audit trail of chat and staff interactions."""
    limit = request.args.get("limit", 50, type=int)
    intent = request.args.get("intent")

    query = InteractionLog.query
    if intent:
        query = query.filter_by(intent=intent)

    logs = query.order_by(InteractionLog.timestamp.desc()).limit(limit).all()
    return jsonify({
        "logs": [log.to_dict() for log in logs],
        "count": len(logs)
    }), 200
