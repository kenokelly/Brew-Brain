from typing import Tuple
from flask import Response
from flask import Blueprint
from core.config import get_all_config
from core.auth import require_api_token
from api.routes import api_response, handle_error

kiosk_bp = Blueprint('kiosk', __name__)

@kiosk_bp.route('/tanks', methods=['GET'])
@require_api_token
def get_kiosk_tanks() -> Tuple[Response, int]:
    """
    Throttled 'Streaming Mode' endpoint for wall-mounted displays.
    Returns simplified status of all active tanks to minimize RAM usage on the client.
    """
    try:
        from services.status import get_status_dict
        
        # Get raw system status
        sys_status = get_status_dict()
        
        # Build Kiosk Payload
        tanks = []
        
        # In a real multi-tank setup, we would loop over active tanks.
        # For now, Brew-Brain assumes 1 active fermentation tank based on current config.
        # We extract its data.
        
        if sys_status.get('batch_name') and sys_status['batch_name'] != "None":
            # Determine alert state based on system status
            alert_state = "normal"
            sys_state = sys_status.get('system_status', 'Unknown').lower()
            if "warning" in sys_state:
                alert_state = "warning"
            elif "critical" in sys_state or "error" in sys_state:
                alert_state = "critical"
                
            tanks.append({
                "tank_id": "fermenter_1",
                "name": sys_status.get('batch_name', 'Unknown'),
                "status": sys_status.get('phase', 'Fermenting'),
                "sg": sys_status.get('sg', 1.000),
                "temp_c": sys_status.get('temp', 20.0),
                "alert_state": alert_state
            })
            
        payload = {
            "kiosk_mode": True,
            "refresh_interval_ms": 60000, # Client should poll every 60s
            "tanks": tanks
        }
        
        return api_response(data=payload)
    except Exception as e:
        return handle_error(e, "Kiosk Fetch Error")
