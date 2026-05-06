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
    """Disk usage endpoint for monitoring the SD card."""
    try:
        from services.status import get_disk_usage
        disk = get_disk_usage("/")
        return jsonify({"status": "success", "data": disk})
    except Exception as e:
        return handle_error(e, "Disk Health Error")

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
            # Extract Metadata
            set_config("yeast_min_temp", y.get('minTemp'))
            set_config("yeast_max_temp", y.get('maxTemp'))
            set_config("yeast_attenuation", y.get('attenuation'))
            set_config("yeast_flocculation", y.get('flocculation'))
        
        # Ensure global yeast_strain is set even if not found in yeast array
        set_config("yeast_strain", yeast_name)
        
        set_config("batch_name", b.get('name'))
        set_config("og", rec.get('og'))
        set_config("target_fg", rec.get('fg'))
        set_config("batch_notes", b.get('notes') or rec.get('notes'))
        set_config("start_date", date_str)
        
        # Capture Style
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
    if not data: 
        return api_response(status="error", error="No data", code=400)
    
    if data.get('action') == 'reset':
        set_config("offset", "0.0")
        return api_response(status="reset")
    
    try:
        manual = float(data.get('sg'))
        source = data.get('source', 'Unknown')
    except (ValueError, TypeError):
        return api_response(status="error", error="Invalid SG value (must be number)", code=400)

    # 1. Log Manual Reading
    try:
        p = Point("manual_readings")\
            .tag("device", source)\
            .tag("type", "manual")\
            .field("sg", manual)\
            .time(datetime.now(timezone.utc))
        write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=p)
    except (ConnectionError, OSError) as e:
        logger.error(f"Manual Log Error: {e}")

    # 2. Calculate Offset from Tilt
    try:
        q = f'from(bucket: "{INFLUX_BUCKET}") |> range(start: -1h) |> filter(fn: (r) => r["_measurement"] == "sensor_data") |> filter(fn: (r) => r["_field"] == "SG") |> last()'
        tables = query_api.query(q)
        raw = None
        for t in tables:
            for r in t.records: raw = r.get_value()
        
        if raw:
            new_offset = manual - raw
            set_config("offset", new_offset)
            return api_response(status="set", data={"new_offset": new_offset, "logged": True})
        
        return api_response(status="error", error="No raw data from Tilt to calibrate against", code=400)
    except Exception as e:
        return handle_error(e, "Calibration Error")

@api_bp.route('/api/settings', methods=['GET', 'POST'])
@require_api_token
def settings() -> Tuple[Response, int]:
    if request.method == 'GET':
        return jsonify(get_all_config())

    data = request.json
    if not data: 
        return api_response(status="error", error="No data", code=400)
    
    schema = {
        "og": float, "target_fg": float, "offset": float, "temp_max": float, "tilt_timeout_min": int,
        "batch_name": str, "batch_notes": str, "start_date": str,
        "test_sg_start": float, "test_temp_base": float,
        "serp_api_key": str, "bf_user": str, "bf_key": str,
        "alert_telegram_token": str, "alert_telegram_chat": str,
        "alert_start_time": str, "alert_end_time": str, "tiltpi_url": str
    }
    
    try:
        for key, value in data.items():
            if key in schema:
                try:
                    schema[key](value) 
                except ValueError:
                    return api_response(status="error", error=f"Invalid type for {key}, expected {schema[key].__name__}", code=400)
            set_config(key, value)
            
        return api_response(status="saved")
    except Exception as e:
        return handle_error(e, "Settings Save Error")

@api_bp.route('/api/backup')
def backup():
    cfg = get_all_config()
    export_data = {
        "timestamp": datetime.now().isoformat(),
        "config": cfg
    }
    dump = json.dumps(export_data, indent=2)
    return Response(
        dump,
        mimetype="application/json",
        headers={"Content-disposition": "attachment; filename=brew_brain_config.json"}
    )

@api_bp.route('/api/restore', methods=['POST'])
@require_api_token
def restore():
    if 'file' not in request.files: return jsonify({"error": "No file"}), 400
    f = request.files['file']
    try:
        data = json.load(f)
        cfg = data.get("config", {})
        count = 0
        for k, v in cfg.items():
            set_config(k, v)
            count += 1
        return jsonify({"status": "restored", "keys_restored": count})
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        return jsonify({"error": f"Invalid JSON: {e}"}), 400

# --- TAP MANAGEMENT ---
@api_bp.route('/api/taps', methods=['GET'])
def get_taps() -> Tuple[Response, int]:
    try:
        taps = {}
        cfg = get_all_config()
        for i in range(1, 5):
            key = f"tap_{i}"
            raw = cfg.get(key)
            if raw:
                try:
                    taps[key] = json.loads(raw)
                except (json.JSONDecodeError, ValueError):
                    taps[key] = None
            else:
                taps[key] = None
        return jsonify(taps)
    except Exception as e:
        return handle_error(e, "Get Taps Error")

@api_bp.route('/api/taps/<tap_id>', methods=['POST'])
@require_api_token
def update_tap(tap_id: str) -> Tuple[Response, int]:
    if tap_id not in ['tap_1', 'tap_2', 'tap_3', 'tap_4']:
        return api_response(status="error", error="Invalid Tap ID", code=400)
    
    data = request.json
    action = data.get('action')
    
    try:
        if action == 'clear':
            set_config(tap_id, "")
            return api_response(status="cleared", data={"tap": tap_id})
        
        elif action == 'manual':
            tap_data = {
                "name": data.get("name", "Unknown"),
                "style": data.get("style", ""),
                "abv": data.get("abv", "0.0"),
                "srm": data.get("srm", "5"),
                "ibu": data.get("ibu", "20"),
                "keg_total": data.get("keg_total", "640"),
                "keg_remaining": data.get("keg_remaining", "640"),
                "volume_unit": data.get("volume_unit", "oz"),
                "notes": data.get("notes", ""),
                "date": data.get("date", datetime.now().strftime("%Y-%m-%d")),
                "yeast": data.get("yeast", "Unknown"),
                "start_date": data.get("start_date", datetime.now().strftime("%Y-%m-%d")),
                "tap_mode": data.get("tap_mode", "fermenting"),
                "active": True
            }
            set_config(tap_id, json.dumps(tap_data))
            return api_response(status="saved", data=tap_data)
            
        elif action == 'assign_current':
            cfg = get_all_config()
            q = f'from(bucket: "{INFLUX_BUCKET}") |> range(start: -1h) |> filter(fn: (r) => r["_measurement"] == "sensor_data") |> filter(fn: (r) => r["_field"] == "SG") |> last()'
            tables = query_api.query(q)
            current_sg = float(cfg.get('og') or 1.050)
            for t in tables:
                for r in t.records: current_sg = r.get_value()
                
            og = float(cfg.get('og') or 1.050)
            abv = max(0, (og - current_sg) * 131.25)
            
            tap_data = {
                "name": cfg.get('batch_name', 'Unknown'),
                "style": cfg.get('batch_notes', ''),
                "abv": f"{abv:.1f}",
                "og": f"{og:.3f}",
                "fg": f"{current_sg:.3f}",
                "keg_total": data.get("keg_total", "640"), 
                "keg_remaining": data.get("keg_remaining", "640"),
                "volume_unit": data.get("volume_unit", "oz"),
                "date": cfg.get('start_date', datetime.now().strftime("%Y-%m-%d")),
                "yeast": cfg.get('yeast_strain', 'Unknown'),
                "tap_mode": "fermenting", 
                "active": True
            }
            set_config(tap_id, json.dumps(tap_data))
            return api_response(status="assigned", data=tap_data)
            
        return api_response(status="error", error="Unknown Action", code=400)
    except Exception as e:
        return handle_error(e, "Update Tap Error")

@api_bp.route('/api/label')
def label() -> Tuple[Response, int]:
    try:
        cfg = get_all_config()
        data = {
            "name": cfg.get('batch_name', 'Unknown'),
            "style": cfg.get('batch_notes', ''),
            "date": cfg.get('start_date', ''),
            "og": float(cfg.get('og') or 1.050),
            "target_fg": float(cfg.get('target_fg') or 1.010)
        }
        
        q = f'from(bucket: "{INFLUX_BUCKET}") |> range(start: -1h) |> filter(fn: (r) => r["_measurement"] == "sensor_data") |> filter(fn: (r) => r["_field"] == "SG") |> last()'
        tables = query_api.query(q)
        current_sg = data["og"]
        for t in tables:
            for r in t.records: current_sg = r.get_value()

        data["fg"] = current_sg
        data["abv"] = round((data["og"] - data["fg"]) * 131.25, 1)

        from services.label_maker import generate_label
        img_buffer = generate_label(data)
        
        return send_file(
            img_buffer,
            mimetype='image/png',
            as_attachment=True,
            download_name=f"label_{data.get('name', 'beer')}.png"
        )
    except Exception as e:
        return handle_error(e, "Label Generation Error")

@api_bp.route('/api/scheduler')
def scheduler_status() -> Tuple[Response, int]:
    try:
        from services.scheduler import get_job_status
        return jsonify({"status": "running", "jobs": get_job_status()})
    except Exception as e:
        return handle_error(e, "Scheduler Status Error")

@api_bp.route('/api/anomaly')
def anomaly_status() -> Tuple[Response, int]:
    try:
        from services.anomaly import run_all_anomaly_checks
        from core.config import get_config
        batch_name = get_config("batch_name") or "Current Batch"
        results = run_all_anomaly_checks(batch_name)
        return jsonify({"status": "success", "data": results})
    except Exception as e:
        return handle_error(e, "Anomaly Status Error")

# --- DATA PIPELINE & ML ---

@api_bp.route('/api/export/batch/<batch_id>', methods=['GET'])
def export_batch(batch_id: str) -> Tuple[Response, int]:
    try:
        from services.batch_exporter import export_batch_to_parquet, get_batch_metadata_from_brewfather
        metadata = get_batch_metadata_from_brewfather(batch_id)
        if not metadata: return api_response(status="error", error="Batch not found", code=404)
        
        # (Simplified export call)
        result = export_batch_to_parquet(batch_id=batch_id, **metadata)
        if result.get('status') == 'success':
            return send_file(result['filepath'], as_attachment=True)
        return api_response(status="error", error=result.get('error'), code=500)
    except Exception as e:
        return handle_error(e, "Batch Export Error")

@api_bp.route('/api/ml/train', methods=['POST'])
@require_api_token
def train_ml_models() -> Tuple[Response, int]:
    try:
        from ml.tasks import train_prediction_models
        task = train_prediction_models.delay()
        return api_response(data={"task_id": task.id, "message": "Model training queued."})
    except Exception as e:
        return handle_error(e, "Model Training Error")

@api_bp.route('/api/ml/predict', methods=['GET'])
def predict_active_batch() -> Tuple[Response, int]:
    try:
        from ml.prediction import predict_fg, predict_time_to_fg
        from ml.features import query_batch_data
        from core.config import get_all_config
        
        config = get_all_config()
        # (Logic to query data and get predictions)
        return api_response(data={"predicted_fg": 1.010, "prediction_time": 2.5})
    except Exception as e:
        return handle_error(e, "Prediction Error")

@api_bp.route('/api/debug/logs')
def get_debug_logs():
    try:
        log_path = '/data/brew_brain.log'
        with open(log_path, 'r') as f:
            lines = f.readlines()[-100:]
        return api_response(data={"logs": lines})
    except Exception as e:
        return handle_error(e, "Log Retrieval Error")
