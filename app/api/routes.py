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

@api_bp.route('/api/sync_brewfather', methods=['POST'])
@require_api_token
def sync_brewfather() -> Tuple[Response, int]:
    u, k = get_config("bf_user"), get_config("bf_key")
    if not u or not k: 
        return api_response(status="error", error="Missing Credentials", code=400)
    
    try:
        auth = base64.b64encode(f"{u}:{k}".encode()).decode()
        r = requests.get("https://api.brewfather.app/v2/batches?status=Fermenting&include=recipe", headers={"Authorization": f"Basic {auth}"}, timeout=10)
        
        if r.status_code != 200: 
            return api_response(status="error", error=f"API Error {r.status_code}", code=400)
        
        batches = r.json()
        if not batches: 
            return api_response(status="error", error="No Fermenting batch found", code=404)
        
        b = batches[0]
        rec = b.get('recipe', {})
        date_str = b.get('brewDate', datetime.now().strftime("%Y-%m-%d"))
        if isinstance(date_str, int): date_str = datetime.fromtimestamp(date_str/1000).strftime("%Y-%m-%d")
        
        # Capture Yeast
        yeasts = rec.get('yeasts', [])
        yeast_name = "Unknown"
        if yeasts and len(yeasts) > 0:
            y = yeasts[0]
            yeast_name = y.get('name', 'Unknown')
            set_config("yeast_min_temp", y.get('minTemp'))
            set_config("yeast_max_temp", y.get('maxTemp'))
            set_config("yeast_attenuation", y.get('attenuation'))
            set_config("yeast_flocculation", y.get('flocculation'))
        
        set_config("yeast_strain", yeast_name)
        set_config("batch_name", b.get('name'))
        set_config("og", rec.get('og'))
        set_config("target_fg", rec.get('fg'))
        set_config("batch_notes", b.get('notes') or rec.get('notes'))
        set_config("start_date", date_str)
        
        style_obj = rec.get('style', {})
        style_name_val = style_obj.get('name') or "Unknown"
        set_config("style", style_name_val)
        
        return api_response(status="synced", data={"name": b.get('name'), "style": style_name_val, "yeast": yeast_name})
    except Exception as e:
        return handle_error(e, "Sync Error")

@api_bp.route('/api/calibrate', methods=['POST'])
@require_api_token
def calibrate() -> Tuple[Response, int]:
    data = request.json
    if not data: return api_response(status="error", error="No data", code=400)
    if data.get('action') == 'reset':
        set_config("offset", "0.0")
        return api_response(status="reset")
    try:
        manual = float(data.get('sg'))
        source = data.get('source', 'Unknown')
        p = Point("manual_readings").tag("device", source).tag("type", "manual").field("sg", manual).time(datetime.now(timezone.utc))
        write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=p)
        q = f'from(bucket: "{INFLUX_BUCKET}") |> range(start: -1h) |> filter(fn: (r) => r["_measurement"] == "sensor_data") |> filter(fn: (r) => r["_field"] == "SG") |> last()'
        tables = query_api.query(q)
        raw = None
        for t in tables:
            for r in t.records: raw = r.get_value()
        if raw:
            new_offset = manual - raw
            set_config("offset", new_offset)
            return api_response(status="set", data={"new_offset": new_offset, "logged": True})
        return api_response(status="error", error="No raw data from Tilt", code=400)
    except Exception as e:
        return handle_error(e, "Calibration Error")

@api_bp.route('/api/settings', methods=['GET', 'POST'])
@require_api_token
def settings() -> Tuple[Response, int]:
    if request.method == 'GET': return jsonify(get_all_config())
    data = request.json
    if not data: return api_response(status="error", error="No data", code=400)
    for key, value in data.items():
        set_config(key, value)
    return api_response(status="saved")

@api_bp.route('/api/backup')
def backup():
    cfg = get_all_config()
    export_data = {"timestamp": datetime.now().isoformat(), "config": cfg}
    return Response(json.dumps(export_data, indent=2), mimetype="application/json", headers={"Content-disposition": "attachment; filename=brew_brain_config.json"})

@api_bp.route('/api/taps', methods=['GET'])
def get_taps() -> Tuple[Response, int]:
    taps = {}
    cfg = get_all_config()
    for i in range(1, 5):
        key = f"tap_{i}"
        raw = cfg.get(key)
        taps[key] = json.loads(raw) if raw else None
    return jsonify(taps)

@api_bp.route('/api/taps/<tap_id>', methods=['POST'])
@require_api_token
def update_tap(tap_id: str) -> Tuple[Response, int]:
    data = request.json
    set_config(tap_id, json.dumps(data))
    return api_response(status="saved")

@api_bp.route('/api/label')
def label() -> Tuple[Response, int]:
    try:
        cfg = get_all_config()
        from services.label_maker import generate_label
        data = {"name": cfg.get('batch_name'), "style": cfg.get('style'), "og": cfg.get('og'), "fg": 1.010, "abv": 5.5, "date": cfg.get('start_date')}
        img_buffer = generate_label(data)
        return send_file(img_buffer, mimetype='image/png', as_attachment=True, download_name=f"label.png")
    except Exception as e:
        return handle_error(e, "Label Error")

@api_bp.route('/api/scheduler')
def scheduler_status() -> Tuple[Response, int]:
    from services.scheduler import get_job_status
    return jsonify({"status": "running", "jobs": get_job_status()})

@api_bp.route('/api/anomaly')
def anomaly_status() -> Tuple[Response, int]:
    from services.anomaly import run_all_anomaly_checks
    batch_name = get_config("batch_name") or "Current Batch"
    return jsonify({"status": "success", "data": run_all_anomaly_checks(batch_name)})

# --- DATA PIPELINE ENDPOINTS ---

@api_bp.route('/api/export/batch/<batch_id>', methods=['GET'])
def export_batch(batch_id: str) -> Tuple[Response, int]:
    try:
        from services.batch_exporter import export_batch_to_parquet, get_batch_metadata_from_brewfather
        metadata = get_batch_metadata_from_brewfather(batch_id)
        if not metadata: return api_response(status="error", error="Batch not found", code=404)
        result = export_batch_to_parquet(batch_id=batch_id, **metadata)
        if result.get('status') == 'success':
            return send_file(result['filepath'], as_attachment=True)
        return api_response(status="error", error=result.get('error'), code=500)
    except Exception as e:
        return handle_error(e, "Export Error")

@api_bp.route('/api/batches/history', methods=['GET'])
def batches_history() -> Tuple[Response, int]:
    try:
        from services.batch_exporter import get_completed_batches
        return api_response(data={"batches": get_completed_batches()})
    except Exception as e:
        return handle_error(e, "History Error")

@api_bp.route('/api/ml/train', methods=['POST'])
@require_api_token
def train_ml_models() -> Tuple[Response, int]:
    try:
        from ml.tasks import train_prediction_models
        task = train_prediction_models.delay()
        return api_response(data={"status": "Task Queued", "task_id": task.id})
    except Exception as e:
        return handle_error(e, "ML Train Error")

@api_bp.route('/api/ml/models', methods=['GET'])
def get_ml_models_info() -> Tuple[Response, int]:
    try:
        from ml.prediction import get_model_info
        return api_response(data=get_model_info())
    except Exception as e:
        return handle_error(e, "Model Info Error")

@api_bp.route('/api/ml/predict', methods=['GET'])
def predict_active_batch() -> Tuple[Response, int]:
    try:
        from ml.prediction import predict_fg, predict_time_to_fg
        from core.config import get_all_config
        return api_response(data={"prediction_fg": 1.010, "prediction_time": 2.0})
    except Exception as e:
        return handle_error(e, "ML Predict Error")

@api_bp.route('/api/debug/logs')
def get_debug_logs():
    try:
        with open('/data/brew_brain.log', 'r') as f:
            return api_response(data={"logs": f.readlines()[-100:]})
    except Exception as e:
        return handle_error(e, "Log Error")
