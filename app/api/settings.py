import os
import json
from datetime import datetime, timezone
from typing import Tuple
from flask import Response
from flask import Blueprint, request
from core.config import set_config, get_all_config, BACKUP_DIR
from core.auth import require_api_token
from api.routes import api_response, handle_error

settings_bp = Blueprint('settings', __name__)

@settings_bp.route('/settings', methods=['GET', 'POST'])
@require_api_token
def settings() -> Tuple[Response, int]:
    """Get or update Brew Brain settings."""
    if request.method == 'GET':
        safe_config = get_all_config()
        # Mask sensitive keys
        if "bf_key" in safe_config: safe_config["bf_key"] = "********"
        if "google_search_api" in safe_config: safe_config["google_search_api"] = "********"
        return api_response(data=safe_config)
    
    try:
        from models.schemas import SettingsUpdate
        from pydantic import ValidationError
        
        try:
            payload = SettingsUpdate(**(request.json or {}))
        except ValidationError as ve:
            return api_response(status="error", error=f"Validation Error: {str(ve)}", code=400)
            
        data = payload.model_dump(exclude_unset=True)
        for key, value in data.items():
            set_config(key, value)
        return api_response(status="updated")
    except Exception as e:
        return handle_error(e, "Settings Update Error")


@settings_bp.route('/calibrate', methods=['POST'])
@require_api_token
def calibrate() -> Tuple[Response, int]:
    """Store explicit SG/Temp points for model calibration."""
    try:
        from models.schemas import CalibrationData
        from pydantic import ValidationError
        
        try:
            data = CalibrationData(**(request.json or {}))
        except ValidationError as ve:
            return api_response(status="error", error=f"Validation Error: {str(ve)}", code=400)
            
        from core.influx import write_api, INFLUX_BUCKET, INFLUX_ORG, Point
        
        point = (Point("sensor_calibration")
            .tag("sensor_type", data.sensor_type)
            .field("actual_sg", data.actual_sg)
            .field("actual_temp", data.actual_temp)
            .field("reported_sg", data.reported_sg)
            .field("offset_sg", data.actual_sg - data.reported_sg)
            .time(datetime.now(timezone.utc)))
            
        write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)
        
        # Trigger retraining of anomaly ML models
        from ml.learning import model_builder
        model_builder.trigger_retraining('anomaly')
        
        return api_response(status="calibrated")
    except Exception as e:
        return handle_error(e, "Calibration Error")


@settings_bp.route('/backup', methods=['POST'])
@require_api_token
def backup():
    """Create a backup of current configuration."""
    try:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(BACKUP_DIR, f"config_backup_{timestamp}.json")
        
        with open(filepath, 'w') as f:
            json.dump(get_all_config(), f)
            
        return api_response(data={"backup_file": filepath})
    except Exception as e:
        return handle_error(e, "Backup Error")


@settings_bp.route('/restore', methods=['POST'])
@require_api_token
def restore():
    """Restore configuration from a backup file."""
    try:
        data = request.json
        filename = data.get('filename')
        filepath = os.path.join(BACKUP_DIR, filename)
        
        if not os.path.exists(filepath):
            return api_response(status="error", error="Backup file not found", code=404)
            
        with open(filepath, 'r') as f:
            backup_data = json.load(f)
            
        for key, value in backup_data.items():
            set_config(key, value)
            
        return api_response(status="restored")
    except Exception as e:
        return handle_error(e, "Restore Error")


@settings_bp.route('/debug/logs')
def get_debug_logs():
    """Retrieves the last 100 lines of the debug log."""
    try:
        log_path = '/data/app_debug.log'
        if not os.path.exists(log_path):
            return api_response(status="error", error="Log file not found", code=404)
            
        with open(log_path, 'r') as f:
            lines = f.readlines()
            last_lines = lines[-100:]
            
        return api_response(data={"logs": last_lines})
    except Exception as e:
        return handle_error(e, "Log Retrieval Error")
