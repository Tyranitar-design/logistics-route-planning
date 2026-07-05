"""Advisory AI agent gateway routes."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from app.services.agent_gateway_service import get_agent_gateway_service


agent_bp = Blueprint("agent", __name__)


@agent_bp.route("/chat", methods=["POST"])
def agent_chat():
    """MiniMax-M3 advisory chat endpoint.

    Returns HTTP 200 with provider_status=degraded when the backend key is not
    configured or the provider is unavailable, so UI pages can show a helpful
    state instead of a generic network failure.
    """
    payload = request.get_json(silent=True) or {}
    return jsonify(get_agent_gateway_service().chat(payload))


@agent_bp.route("/tools/preview", methods=["POST"])
def agent_tools_preview():
    """Preview what a read-only tool would do. Does not execute the tool."""
    payload = request.get_json(silent=True) or {}
    return jsonify(get_agent_gateway_service().preview_tool(payload))


@agent_bp.route("/actions/confirm", methods=["POST"])
def agent_actions_confirm():
    """Confirm a safe advisory action. Business writes stay explicit."""
    payload = request.get_json(silent=True) or {}
    return jsonify(get_agent_gateway_service().confirm_action(payload))
