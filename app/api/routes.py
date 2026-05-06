import shutil
import requests
import json
import base64
from typing import Any, Dict, Tuple, Optional, Union
import numpy as np
from datetime import datetime, timezone, timedelta
from flask import Blueprint, jsonify, request, send_from_directory, send_file, Response
from app.core.config import get_config, set_config, get_all_config, DATA_DIR, BACKUP_DIR, logger
from app.core.influx import query_api, write_api, INFLUX_BUCKET, INFLUX_ORG
from app.core.auth import require_api_token
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
        # Return partial/empty status to prevent frontend crash
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
    """Disk usage endpoint for monitoring the 32 GB SD card."""
    try:
        from services.status import get_disk_usage
        disk = get_disk_usage("/")

        if disk.get("warning"):
            try:
                from services.notifications import send_telegram_alert
                send_telegram_alert(
                    f"⚠️ Brew Brain Disk Warning: {disk['used_percent']}% used "
                    f"({disk['free_gb']} GB free of {disk['total_gb']} GB)"
                )
            except Exception as e:
                logger.warning(f"Telegram disk alert failed: {e}")

        return jsonify({"status": "success", "data": disk})
    except Exception as e:
        return handle_error(e, "Disk Health Error")

@api_bp.route('/api/health/maintenance')
def health_maintenance():
    """Full maintenance summary: disk, SD I/O, Pi temp, data volume."""
    try:
        from services.status import get_maintenance_summary
        summary = get_maintenance_summary()
        return jsonify({"status": "success", "data": summary})
    except Exception as e:
        return handle_error(e, "Maintenance Summary Error")

@api_bp.route('/api/sync_brewfather', methods=['POST'])
@require_api_token
def label() -> Tuple[Response, int]:
    try:
        # Gather Data
        cfg = get_all_config()
        name = cfg.get('batch_name', 'Unknown')
        notes = cfg.get('batch_notes', '')
        date = cfg.get('start_date', '')
        og = float(cfg.get('og') or 1.050)
        target_fg = float(cfg.get('target_fg') or 1.010)
        
        # Get Current SG from Influx
        q = f'from(bucket: "{INFLUX_BUCKET}") |> range(start: -1h) |> filter(fn: (r) => r["_measurement"] == "sensor_data") |> filter(fn: (r) => r["_field"] == "SG") |> last()'
        tables = query_api.query(q)
        current_sg = og # Default if no reading
        for t in tables:
            for r in t.records: current_sg = r.get_value()

        # Calc Stats
        abv = max(0, (og - current_sg) * 131.25)
        
        data = {
            "name": name,
            "style": notes,
            "abv": f"{abv:.1f}",
            "og": f"{og:.3f}",
            "fg": f"{current_sg:.3f}",
            "date": date
        }
        if 'abv' not in data and 'og' in data and 'fg' in data:
            data['abv'] = round((float(data['og']) - float(data['fg'])) * 131.25, 1)

        try:
            from services.label_maker import generate_label
            img_buffer = generate_label(data)
            
            return send_file(
                img_buffer,
                mimetype='image/png',
                as_attachment=True,
                download_name=f"label_{data.get('name', 'beer')}.png"
            )
        except ImportError as e:
            return api_response(status="error", error=f"Label Maker Missing: {e}", code=500)
    except Exception as e:
        logger.error(f"Label Gen Error: {e}")
        return jsonify({"error": f"Label Gen Error: {e}"}), 500


@api_bp.route('/api/scheduler')
def scheduler_status() -> Tuple[Response, int]:
    """Get status of all scheduled jobs."""
    try:
        from services.scheduler import get_job_status
        return jsonify({
            "status": "running",
            "jobs": get_job_status()
        })
    except Exception as e:
        return handle_error(e, "Scheduler Status Error")


@api_bp.route('/api/scheduler/<job_id>/pause', methods=['POST'])
def pause_job_endpoint(job_id: str) -> Tuple[Response, int]:
    """Pause a scheduled job."""
    try:
        from services.scheduler import pause_job
        pause_job(job_id)
        return api_response(status="paused", data={"job_id": job_id})
    except Exception as e:
        return handle_error(e, "Pause Job Error")


@api_bp.route('/api/scheduler/<job_id>/resume', methods=['POST'])
def resume_job_endpoint(job_id: str) -> Tuple[Response, int]:
    """Resume a paused scheduled job."""
    try:
        from services.scheduler import resume_job
        resume_job(job_id)
        return api_response(status="resumed", data={"job_id": job_id})
    except Exception as e:
        return handle_error(e, "Resume Job Error")


@api_bp.route('/api/anomaly')
def anomaly_status() -> Tuple[Response, int]:
    """
    Get current anomaly detection status including Z-score analysis.
    Returns anomaly_score (0.0-1.0+), individual check results, and alerts.
    """
    try:
        from app.services.anomaly import run_all_anomaly_checks, calculate_anomaly_score
        from app.core.config import get_config
        
        batch_name = get_config("batch_name") or "Current Batch"
        
        # Get full anomaly check results
        results = run_all_anomaly_checks(batch_name)
        
        return jsonify({
            "status": "success",
            "data": {
                "batch": batch_name,
                "anomaly_score": results.get("anomaly_score", 0.0),
                "anomaly_status": results.get("anomaly_status", "ok"),
                "alerts_sent": results.get("alerts_sent", 0),
                "checks": results.get("checks", {}),
                "timestamp": results.get("timestamp")
            }
        })
    except Exception as e:
        return handle_error(e, "Anomaly Status Error")


@api_bp.route('/api/anomaly/score')
def anomaly_score_only() -> Tuple[Response, int]:
    """
    Get just the statistical anomaly score (lightweight endpoint for polling).
    """
    try:
        from app.services.anomaly import calculate_anomaly_score
        
        result = calculate_anomaly_score()
        
        return jsonify({
            "status": "success",
            "anomaly_score": result.get("anomaly_score", 0.0),
            "anomaly_status": result.get("status", "normal"),
            "temp_zscore": result.get("temp_zscore"),
            "sg_rate_zscore": result.get("sg_rate_zscore")
        })
    except Exception as e:
        return handle_error(e, "Anomaly Score Error")


# --- DATA PIPELINE ENDPOINTS ---

@api_bp.route('/api/export/batch/<batch_id>', methods=['GET'])
def brew_day_check() -> Tuple[Response, int]:
    """
    Checks and Balances: Verifies all metadata and sensor data is correct for the current brew day.
    """
    try:
        from core.config import get_all_config
        from core.influx import query_api, INFLUX_BUCKET
        from datetime import datetime, timezone, timedelta
        
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
        
        checks.append({
            "name": "Target Final Gravity (FG)",
            "status": "ready" if config.get("target_fg") and float(config.get("target_fg")) > 0.0 else "warning",
            "message": f"Estimated FG: {config.get('target_fg')}" if config.get("target_fg") else "Estimated FG not set. AI will use a default formula."
        })
        
        checks.append({
            "name": "Beer Style Correlation",
            "status": "ready" if config.get("style") else "warning",
            "message": f"Style: {config.get('style')}" if config.get("style") else "Style unknown. Style intelligence is disabled."
        })
        
        # 2. Sensor Health Checks
        try:
            q = f'from(bucket: "{INFLUX_BUCKET}") |> range(start: -60m) |> filter(fn: (r) => r["_measurement"] == "sensor_data") |> filter(fn: (r) => r["_field"] == "SG") |> last()'
            tables = query_api.query(q)
            last_reading = None
            for t in tables:
                for r in t.records: last_reading = r.get_time()
            
            if last_reading:
                last_ts = last_reading.timestamp()
                now_ts = datetime.now(timezone.utc).timestamp()
                diff_min = (now_ts - last_ts) / 60
                
                checks.append({
                    "name": "Sensor Signal (Tilt/iSpindel)",
                    "status": "ready" if diff_min < 20 else "warning",
                    "message": f"Last signal received {int(diff_min)} minutes ago." if diff_min < 60 else "Signal is stale (> 1 hour). Check your battery or Stream URL."
                })
            else:
                checks.append({
                    "name": "Sensor Signal (Tilt/iSpindel)",
                    "status": "error",
                    "message": "No sensor data found in InfluxDB for the last hour."
                })
        except Exception as e:
            checks.append({"name": "Sensor Health Check", "status": "error", "message": f"Database error: {str(e)}"})

        # 3. Overall Readiness Score
        readiness_score = sum(100 for c in checks if c["status"] == "ready") / len(checks)
        
        return api_response(data={
            "score": round(readiness_score),
            "checks": checks,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        return handle_error(e, "Brew Day Check Error")
@api_bp.route('/api/sourcing/compare-by-tag/<tag>')
def compare_prices_by_tag(tag):
    """
    Compares prices for a recipe found by tag.
    """
    try:
        try:
            from app.services.sourcing import compare_recipe_prices
        except ImportError as e:
            return api_response(status="error", error=f"Dependency Error: {str(e)}", code=500)
            
        # Decode tag (handle spaces/special chars)
        from urllib.parse import unquote
        import flask
        decoded_tag = unquote(tag)
        
        # Check for debug flag
        debug_mode = flask.request.args.get('debug', '').lower() == 'true'
        
        # Run Comparison (logic inside sourcing.py now handles tag lookup)
        # We pass empty dict for recipe_details as we are relying on tag lookup
        result = compare_recipe_prices({}, recipe_tag=decoded_tag, debug_mode=debug_mode)
        
        if "error" in result:
             return api_response(status="error", error=result["error"], code=400)
             
        return api_response(data=result)
        
    except Exception as e:
        return handle_error(e, "Price Comparison Error")

# --- EXTERNAL RECIPE DATABASE ---

