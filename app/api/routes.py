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
            
        from services.status import get_status_dict
        status_data = get_status_dict()
        cache.set("system_status", status_data, ttl=300)
        return jsonify(status_data)
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
            
        from services.status import get_maintenance_summary
        maint_data = get_maintenance_summary()
        cache.set("maintenance_summary", maint_data, ttl=3600)
        return jsonify({"status": "success", "data": maint_data})
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
            
        from services.anomaly import run_all_anomaly_checks
        batch_name = get_config("batch_name") or "Current Batch"
        anomaly_data = run_all_anomaly_checks(batch_name)
        cache.set("anomaly_status", anomaly_data, ttl=600)
        return jsonify({"status": "success", "data": anomaly_data})
    except Exception as e:
        return handle_error(e, "Anomaly Error")

