from typing import Tuple
from flask import Blueprint, request, Response
from core.config import get_config
from services.ai import generate_narrative
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
    Experimental 'Brewmaster' chat endpoint.
    """
    try:
        user_msg = request.json.get("message")
        if not user_msg:
            return api_response(status="error", error="Missing message", code=400)
            
        from services.ai import generate_chat_response
        result = generate_chat_response(user_msg)
        return api_response(data=result)
    except Exception as e:
        return handle_error(e, "Chat Error")
