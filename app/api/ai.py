from typing import Tuple
from flask import Blueprint, request, Response
from core.config import get_config
from services.ai import generate_narrative, analyze_anomaly, get_proactive_advice
from api.routes import api_response, handle_error

ai_bp = Blueprint('ai', __name__)

@ai_bp.route('/narrative', methods=['GET'])
def get_batch_narrative() -> Tuple[Response, int]:
    """
    Get an AI-generated narrative for the current batch.
    """
    try:
        from services.status import get_status_dict
        status = get_status_dict()
        
        batch_data = {
            "name": status.get("batch_name", "Unknown"),
            "style": get_config("style") or "Beer",
            "og": status.get("og", 1.050),
            "fg": status.get("sg", 1.010),
            "temp_avg": status.get("temp", 20.0),
            "status": "active" if status.get("status") == "Online" else "unknown"
        }
        
        result = generate_narrative(batch_data)
        return api_response(data=result)
        
    except Exception as e:
        return handle_error(e, "Narrative Generation Error")

@ai_bp.route('/chat', methods=['POST'])
def brewmaster_chat() -> Tuple[Response, int]:
    """
    Experimental 'Brewmaster' chat endpoint with history support.
    """
    try:
        data = request.json or {}
        user_msg = data.get("message")
        history = data.get("history")
        
        if not user_msg:
            return api_response(status="error", error="Missing message", code=400)
            
        if len(str(user_msg)) > 2000:
            return api_response(status="error", error="Message too long", code=400)
        if not isinstance(history, list):
            history = []
        # Keep the prompt (and CPU time) bounded on the Pi
        history = history[-10:]

        # Replies take minutes on the Pi's CPU; run as a background job and
        # let the client poll /chat/status/<task_id> (see run_chat_task).
        from services.tasks import run_chat_task
        task = run_chat_task.delay(user_msg, history)
        return api_response(data={"status": "queued", "task_id": task.id}, code=202)
    except Exception as e:
        return handle_error(e, "Chat Error")


@ai_bp.route('/chat/status/<task_id>', methods=['GET'])
def brewmaster_chat_status(task_id: str) -> Tuple[Response, int]:
    """Poll a queued chat reply: queued / thinking / success / fallback / error."""
    try:
        from extensions import celery
        from celery.result import AsyncResult

        task = AsyncResult(task_id, app=celery)
        if task.state == 'PENDING':
            return api_response(data={"status": "queued"})
        if task.state == 'STARTED':
            return api_response(data={"status": "thinking"})
        if task.state == 'FAILURE':
            return api_response(data={"status": "error", "message": str(task.info)})
        if task.state == 'SUCCESS':
            return api_response(data=task.get())
        return api_response(data={"status": task.state.lower()})
    except Exception as e:
        return handle_error(e, "Chat Status Error")

@ai_bp.route('/troubleshoot', methods=['POST'])
def troubleshoot_anomaly() -> Tuple[Response, int]:
    """
    AI Anomaly Analysis endpoint.
    """
    try:
        anomaly_data = request.json.get("anomaly")
        if not anomaly_data:
            return api_response(status="error", error="Missing anomaly data", code=400)
            
        result = analyze_anomaly(anomaly_data)
        return api_response(data=result)
    except Exception as e:
        return handle_error(e, "Troubleshoot Error")

@ai_bp.route('/advice', methods=['GET'])
def get_advice() -> Tuple[Response, int]:
    """
    AI Proactive Advice endpoint.
    """
    try:
        result = get_proactive_advice()
        return api_response(data=result)
    except Exception as e:
        return handle_error(e, "Advice Error")
