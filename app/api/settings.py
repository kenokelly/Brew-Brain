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

@settings_bp.route('/settings', methods=['GET', 'PATCH'])
@require_api_token
def settings() -> Tuple[Response, int]:
    """Get or update Brew Brain settings."""
    if request.method == 'GET':
        safe_config = get_all_config()
        # Mask sensitive keys
        if "bf_key" in safe_config and safe_config["bf_key"]: safe_config["bf_key"] = "********"
        if "alert_telegram_token" in safe_config and safe_config["alert_telegram_token"]: safe_config["alert_telegram_token"] = "********"
        if "serp_api_key" in safe_config and safe_config["serp_api_key"]: safe_config["serp_api_key"] = "********"
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

import requests

@settings_bp.route('/settings/test', methods=['POST'])
@require_api_token
def test_integration() -> Tuple[Response, int]:
    """Test a 3rd-party integration with unsaved credentials."""
    try:
        data = request.json or {}
        integration = data.get('integration')
        config = data.get('config', {})
        
        if integration == 'telegram':
            token = config.get('alert_telegram_token')
            chat_id = config.get('alert_telegram_chat')
            if not token or not chat_id:
                return api_response(status="error", error="Missing Telegram Token or Chat ID", code=400)
            
            # Mask token in output for safety
            safe_token = f"{token[:4]}...{token[-4:]}" if len(token) > 8 else "****"
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = {"chat_id": chat_id, "text": "🧪 *Brew Brain Test*\nConnection successful!", "parse_mode": "Markdown"}
            
            try:
                res = requests.post(url, json=payload, timeout=5)
                if res.status_code == 200:
                    return api_response(status="success", message=f"Telegram connected! Test message sent to {chat_id}.")
                else:
                    return api_response(status="error", error=f"Telegram Error ({res.status_code}): {res.text}", code=400)
            except requests.exceptions.RequestException as e:
                return api_response(status="error", error=f"Telegram Network Error: {str(e)}", code=400)
                
        elif integration == 'brewfather':
            user_id = config.get('bf_user')
            api_key = config.get('bf_key')
            if not user_id or not api_key:
                return api_response(status="error", error="Missing Brewfather User ID or API Key", code=400)
            
            import base64
            auth_str = base64.b64encode(f"{user_id}:{api_key}".encode()).decode()
            try:
                res = requests.get("https://api.brewfather.app/v2/batches?limit=1", headers={"Authorization": f"Basic {auth_str}"}, timeout=5)
                if res.status_code == 200:
                    return api_response(status="success", message="Brewfather authenticated successfully!")
                else:
                    return api_response(status="error", error=f"Brewfather Error ({res.status_code}): {res.text}", code=400)
            except requests.exceptions.RequestException as e:
                return api_response(status="error", error=f"Brewfather Network Error: {str(e)}", code=400)
                
        elif integration == 'serpapi':
            api_key = config.get('serp_api_key')
            if not api_key:
                return api_response(status="error", error="Missing SerpApi Key", code=400)
            try:
                res = requests.get(f"https://serpapi.com/search.json?q=test&api_key={api_key}", timeout=5)
                if res.status_code == 200:
                    return api_response(status="success", message="SerpApi authenticated successfully!")
                else:
                    return api_response(status="error", error=f"SerpApi Error ({res.status_code}): {res.text}", code=400)
            except requests.exceptions.RequestException as e:
                return api_response(status="error", error=f"SerpApi Network Error: {str(e)}", code=400)
                
        elif integration == 'ollama':
            host = config.get('ollama_host', 'localhost')
            model = config.get('ollama_model', 'llama3')
            
            if not host.startswith('http'):
                host = f"http://{host}:11434"
            else:
                host = host.rstrip('/')
                
            try:
                res = requests.get(f"{host}/api/tags", timeout=5)
                if res.status_code == 200:
                    models = res.json().get('models', [])
                    if any(m.get('name', '').startswith(model) for m in models):
                        return api_response(status="success", message=f"Ollama connected. Model '{model}' is installed and ready.")
                    else:
                        installed = ", ".join([m.get('name') for m in models]) or "None"
                        return api_response(status="error", error=f"Connected to Ollama, but model '{model}' not found. Installed models: {installed}", code=400)
                else:
                    return api_response(status="error", error=f"Ollama Error ({res.status_code}): {res.text}", code=400)
            except requests.exceptions.ConnectionError:
                 return api_response(status="error", error=f"Could not connect to Ollama at {host}. Is the service running?", code=400)
            except requests.exceptions.RequestException as e:
                 return api_response(status="error", error=f"Ollama Network Error: {str(e)}", code=400)
        
        else:
            return api_response(status="error", error=f"Unknown integration target: {integration}", code=400)
            
    except Exception as e:
        return handle_error(e, "Integration Test Error")
