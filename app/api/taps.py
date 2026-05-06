from typing import Tuple, Response
from flask import Blueprint, request
from app.core.config import get_config, set_config
from app.core.auth import require_api_token
from app.api.routes import api_response, handle_error

taps_bp = Blueprint('taps', __name__)

@taps_bp.route('/api/taps', methods=['GET'])
def get_taps() -> Tuple[Response, int]:
    """Get active kiosk tap list."""
    try:
        taps = get_config("taps") or {
            "tap1": {"name": "Empty", "style": "N/A", "abv": 0, "color": "#FFC107", "keg_date": None, "volume_remaining": 0},
            "tap2": {"name": "Empty", "style": "N/A", "abv": 0, "color": "#FFC107", "keg_date": None, "volume_remaining": 0},
            "tap3": {"name": "Empty", "style": "N/A", "abv": 0, "color": "#FFC107", "keg_date": None, "volume_remaining": 0},
            "tap4": {"name": "Empty", "style": "N/A", "abv": 0, "color": "#FFC107", "keg_date": None, "volume_remaining": 0}
        }
        return api_response(data=taps)
    except Exception as e:
        return handle_error(e, "Tap Fetch Error")


@taps_bp.route('/api/taps/<tap_id>', methods=['POST'])
@require_api_token
def update_tap(tap_id: str) -> Tuple[Response, int]:
    """Update a specific tap."""
    try:
        from models.schemas import TapUpdate
        from pydantic import ValidationError
        
        try:
            tap_data = TapUpdate(**(request.json or {}))
        except ValidationError as ve:
            return api_response(status="error", error=f"Validation Error: {str(ve)}", code=400)
            
        taps = get_config("taps") or {}
        taps[tap_id] = tap_data.model_dump()
        set_config("taps", taps)
        return api_response(status="updated")
    except Exception as e:
        return handle_error(e, "Tap Update Error")
