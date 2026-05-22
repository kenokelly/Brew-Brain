from typing import Tuple
from flask import Response
from flask import Blueprint, request
from core.config import get_config, set_config
from core.auth import require_api_token
from api.routes import api_response, handle_error

taps_bp = Blueprint('taps', __name__)

@taps_bp.route('/taps', methods=['GET'])
def get_taps() -> Tuple[Response, int]:
    """Get active kiosk tap list with dynamic QR codes."""
    try:
        from services.taps import get_tap_list
        base_url = request.host_url.rstrip('/')
        taps_data = get_tap_list(base_url)
        return api_response(data={"taps": taps_data})
    except Exception as e:
        return handle_error(e, "Tap Fetch Error")

@taps_bp.route('/taps/config', methods=['GET'])
@require_api_token
def get_taps_config() -> Tuple[Response, int]:
    """Get raw tap configuration for Settings menu."""
    try:
        taps_config = get_config("taps") or {}
        return api_response(data=taps_config)
    except Exception as e:
        return handle_error(e, "Tap Config Fetch Error")


@taps_bp.route('/taps/<tap_id>/init', methods=['POST'])
@require_api_token
def init_tap_endpoint(tap_id: str) -> Tuple[Response, int]:
    """Admin endpoint to initialize a new keg on a tap."""
    try:
        data = request.json or {}
        batch_id = data.get('batch_id')
        keg_volume_l = data.get('keg_volume_l', 19.0)
        
        if not batch_id:
            return api_response(status="error", error="batch_id is required", code=400)
            
        from services.taps import init_tap
        result = init_tap(tap_id, batch_id, float(keg_volume_l))
        
        if "error" in result:
             return api_response(status="error", error=result["error"], code=400)
             
        return api_response(status="success", data={"message": result.get("message")})
    except Exception as e:
        return handle_error(e, "Tap Init Error")


@taps_bp.route('/taps/<tap_id>/pour', methods=['POST'])
@require_api_token
def pour_tap_endpoint(tap_id: str) -> Tuple[Response, int]:
    """Decrement volume from a tap."""
    try:
        data = request.json or {}
        amount_ml = data.get('amount_ml')
        
        if not amount_ml:
             return api_response(status="error", error="amount_ml is required", code=400)
             
        from services.taps import pour_tap
        result = pour_tap(tap_id, float(amount_ml))
        
        if "error" in result:
            return api_response(status="error", error=result["error"], code=400)
            
        return api_response(status="success", data={"new_remaining_pct": result.get("new_remaining_pct")})
    except Exception as e:
        return handle_error(e, "Tap Pour Error")


@taps_bp.route('/taps/<tap_id>', methods=['POST'])
@require_api_token
def manage_tap_endpoint(tap_id: str) -> Tuple[Response, int]:
    """Handle manual assignments, snapshots, and clearing taps from UI."""
    try:
        data = request.json or {}
        from services.taps import update_tap
        result = update_tap(tap_id, data)
        
        if "error" in result:
            return api_response(status="error", error=result["error"], code=400)
            
        return api_response(status="success", data=result)
    except Exception as e:
        return handle_error(e, "Tap Management Error")

