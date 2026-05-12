from typing import Any, Dict, Tuple, Optional
from datetime import datetime, timezone
from flask import Blueprint, jsonify, Response
from core.config import get_config, get_all_config, logger

api_bp = Blueprint('api', __name__)

def api_response(data: Optional[Dict[str, Any]] = None, status: str = "success", error: Optional[str] = None, code: int = 200) -> Tuple[Response, int]:
    body = {"status": status}
    if data is not None: body["data"] = data
    if error is not None: body["error"] = error
    return jsonify(body), code

def handle_error(e: Exception, context: str = "Error") -> Tuple[Response, int]:
    logger.error(f"{context}: {str(e)}")
    return api_response(status="error", error=f"{context}: {str(e)}", code=500)

@api_bp.route('/status')
def status():
    try:
        from core.cache import cache
        cached_status = cache.get("system_status")
        if cached_status:
            return jsonify(cached_status)
        
        # If cache empty, return stale/empty status instead of blocking
        return jsonify({
            "status": "Starting Up...",
            "message": "Telemetry is being calculated in the background",
            "batch_name": get_config("batch_name") or "Loading..."
        }), 202
    except Exception as e:
        return handle_error(e, "Status Error")

@api_bp.route('/health')
def health():
    return jsonify({"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()})

@api_bp.route('/health/maintenance')
def health_maintenance():
    try:
        from core.cache import cache
        cached_maint = cache.get("maintenance_summary")
        if cached_maint:
            return jsonify({"status": "success", "data": cached_maint})
            
        return jsonify({"status": "processing", "message": "Gathering maintenance stats"}), 202
    except Exception as e:
        return handle_error(e, "Maintenance Error")

@api_bp.route('/brew_day_check')
def brew_day_check():
    try:
        config = get_all_config()
        checks = [
            {"name": "Active Batch", "status": "ready" if config.get("batch_name") else "warning", "message": config.get("batch_name") or "None"},
            {"name": "OG", "status": "ready" if float(config.get("og") or 0) > 1.0 else "error", "message": str(config.get("og"))}
        ]
        return api_response(data={"score": 100, "checks": checks})
    except Exception as e:
        return handle_error(e, "Check Error")

@api_bp.route('/anomaly')
def anomaly_status():
    try:
        from core.cache import cache
        cached_anomaly = cache.get("anomaly_status")
        if cached_anomaly:
            return jsonify({"status": "success", "data": cached_anomaly})
            
        return jsonify({"status": "processing", "message": "Running anomaly detection"}), 202
    except Exception as e:
        return handle_error(e, "Anomaly Error")

