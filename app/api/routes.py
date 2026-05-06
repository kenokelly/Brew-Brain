import shutil
import requests
import json
import base64
from typing import Any, Dict, Tuple, Optional, Union
import numpy as np
from datetime import datetime, timezone, timedelta
from flask import Blueprint, jsonify, request, send_from_directory, send_file, Response
from core.config import get_config, set_config, get_all_config, DATA_DIR, BACKUP_DIR, logger
from core.influx import query_api, write_api, INFLUX_BUCKET, INFLUX_ORG
from core.auth import require_api_token
from influxdb_client import Point
# DELAYING IMPORT of services to prevent startup crashes if dependencies fail
# from services.status import get_status_dict
# from services.label_maker import generate_label

api_bp = Blueprint('api', __name__)

# --- HELPERS ---
def api_response(data: Optional[Dict[str, Any]] = None, status: str = "success", error: Optional[str] = None, code: int = 200) -> Tuple[Response, int]:
    """Standardized API Response Helper."""
    body = {"status": status}
    if data is not None:
        body["data"] = data
    if error is not None:
        body["error"] = error
    return jsonify(body), code

def handle_error(e: Exception, context: str = "Error") -> Tuple[Response, int]:
    """Logs error and returns standardized error response."""
    logger.error(f"{context}: {str(e)}")
    return api_response(status="error", error=f"{context}: {str(e)}", code=500)

@api_bp.route('/')
def index(): return send_from_directory('static', 'index.html')

@api_bp.route('/taplist')
def taplist(): return send_from_directory('static', 'kiosk.html')

@api_bp.route('/api/status')
def status():
    try:
        from services.status import get_status_dict
        return jsonify(get_status_dict())
    except Exception as e:
        logger.error(f"Status Endpoint Failed: {e}")
        return jsonify({
            "status": "Error", "sg": 0, "temp": 0, 
            "error": str(e)
        })

@api_bp.route('/api/health')
def health():
    """Health check endpoint for Docker/Kubernetes probes."""
    try:
        # Check InfluxDB connectivity
        q = f'from(bucket: "{INFLUX_BUCKET}") |> range(start: -1m) |> limit(n: 1)'
        query_api.query(q)
        influx_status = "healthy"
    except (ConnectionError, OSError) as e:
        influx_status = f"unhealthy: {str(e)}"
    
    return jsonify({
        "status": "healthy" if influx_status == "healthy" else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": {
            "api": "healthy",
            "influxdb": influx_status,
        }
    })

@api_bp.route('/api/health/disk')
def health_disk():
    """Disk usage endpoint for monitoring the SD card."""
    try:
        from services.status import get_disk_usage
        disk = get_disk_usage("/")
        return jsonify({"status": "success", "data": disk})
    except Exception as e:
        return handle_error(e, "Disk Health Error")

@api_bp.route('/api/health/maintenance')
def health_maintenance():
    """Aggregated maintenance metrics for the SRE dashboard."""
    try:
        from services.status import get_maintenance_summary
        return jsonify({"status": "success", "data": get_maintenance_summary()})
    except Exception as e:
        return handle_error(e, "Maintenance Health Error")

@api_bp.route('/api/brew_day_check', methods=['GET'])
def brew_day_check() -> Tuple[Response, int]:
    """
    Checks and Balances: Verifies all metadata and sensor data is correct for the current brew day.
    """
    try:
        config = get_all_config()
        checks = []
        
        # 1. Metadata Checks
        checks.append({
            "name": "Active Batch Name",
            "status": "ready" if config.get("batch_name") else "warning",
            "message": f"Currently brewing: {config.get('batch_name')}" if config.get("batch_name") else "No active batch name set."
        })
        
        checks.append({
            "name": "Original Gravity (OG)",
            "status": "ready" if config.get("og") and float(config.get("og")) > 1.0 else "error",
            "message": f"Target OG: {config.get('og')}" if config.get("og") else "OG is missing! AI predictions will be inaccurate."
        })
        
        # 2. Sensor Health Checks
        try:
            q = f'from(bucket: "{INFLUX_BUCKET}") |> range(start: -60m) |> filter(fn: (r) => r["_measurement"] == "sensor_data") |> filter(fn: (r) => r["_field"] == "SG") |> last()'
            tables = query_api.query(q)
            last_reading = None
            for t in tables:
                for rec in t.records: last_reading = rec.get_time()
            
            if last_reading:
                last_ts = last_reading.timestamp()
                now_ts = datetime.now(timezone.utc).timestamp()
                diff_min = (now_ts - last_ts) / 60
                
                checks.append({
                    "name": "Sensor Signal (Tilt/iSpindel)",
                    "status": "ready" if diff_min < 20 else "warning",
                    "message": f"Last signal received {int(diff_min)} minutes ago." if diff_min < 60 else "Signal is stale (> 1 hour)."
                })
            else:
                checks.append({
                    "name": "Sensor Signal",
                    "status": "error",
                    "message": "No sensor data found in InfluxDB for the last hour."
                })
        except Exception as e:
            checks.append({"name": "Sensor Health Check", "status": "error", "message": f"Database error: {str(e)}"})

        # 3. Overall Readiness Score
        readiness_score = sum(100 for c in checks if c["status"] == "ready") / len(checks) if checks else 0
        
        return api_response(data={
            "score": round(readiness_score),
            "checks": checks,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        return handle_error(e, "Brew Day Check Error")


@api_bp.route('/api/debug/logs')
def get_debug_logs():
    try:
        log_path = '/data/brew_brain.log'
        with open(log_path, 'r') as f:
            lines = f.readlines()[-100:]
        return api_response(data={"logs": lines})
    except Exception as e:
        return handle_error(e, "Log Error")
