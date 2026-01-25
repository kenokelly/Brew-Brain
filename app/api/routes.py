import shutil
import requests
import json
import base64
from typing import Any, Dict, Tuple, Optional, Union
from datetime import datetime, timezone
from flask import Blueprint, jsonify, request, send_from_directory, send_file, Response
from app.core.config import get_config, set_config, get_all_config, DATA_DIR, BACKUP_DIR, logger
from app.core.influx import query_api, write_api, INFLUX_BUCKET, INFLUX_ORG
from influxdb_client import Point
from services.status import get_status_dict
from services.label_maker import generate_label

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
    return jsonify(get_status_dict())

@api_bp.route('/api/health')
def health():
    """Health check endpoint for Docker/Kubernetes probes."""
    import time
    try:
        # Check InfluxDB connectivity
        q = f'from(bucket: "{INFLUX_BUCKET}") |> range(start: -1m) |> limit(n: 1)'
        query_api.query(q)
        influx_status = "healthy"
    except Exception as e:
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
        set_config("yeast_strain", yeast_name)
        
        return api_response(status="synced", data={"name": b.get('name'), "yeast": yeast_name})
            
    except Exception as e:
        return handle_error(e, "Sync Error")

@api_bp.route('/api/calibrate', methods=['POST'])
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
    except Exception as e:
        logger.error(f"Manual Log Error: {e}")
        # Continue execution, logging failure shouldn't block calibration

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
    # Export Config as JSON
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
    except Exception as e:
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
                except:
                    taps[key] = None
            else:
                taps[key] = None
        return jsonify(taps)
    except Exception as e:
        return handle_error(e, "Get Taps Error")

@api_bp.route('/api/taps/<tap_id>', methods=['POST'])
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
            # Save exact data provided
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
                
                # Preserve details
                "yeast": data.get("yeast", "Unknown"),
                "start_date": data.get("start_date", datetime.now().strftime("%Y-%m-%d")),
                "finish_date": data.get("finish_date", "Active"),
                "tap_mode": data.get("tap_mode", "fermenting"), # fermenting vs serving

                "active": True
            }
            set_config(tap_id, json.dumps(tap_data))
            return api_response(status="saved", data=tap_data)
            
        elif action == 'assign_current':
            # Snapshot current batch
            cfg = get_all_config()
            
            # Get Current SG from Influx for FG
            q = f'from(bucket: "{INFLUX_BUCKET}") |> range(start: -1h) |> filter(fn: (r) => r["_measurement"] == "sensor_data") |> filter(fn: (r) => r["_field"] == "SG") |> last()'
            tables = query_api.query(q)
            current_sg = float(cfg.get('og') or 1.050)
            for t in tables:
                for r in t.records: current_sg = r.get_value()
                
            og = float(cfg.get('og') or 1.050)
            abv = max(0, (og - current_sg) * 131.25)
            
            tap_data = {
                "name": cfg.get('batch_name', 'Unknown'),
                "style": cfg.get('batch_notes', ''), # Using notes as style for now
                "notes": "",
                "abv": f"{abv:.1f}",
                "og": f"{og:.3f}",
                "fg": f"{current_sg:.3f}",
                "srm": cfg.get('srm', '5'),
                "ibu": cfg.get('ibu', '20'),
                
                # Use provided volume/unit or default
                "keg_total": data.get("keg_total", "640"), 
                "keg_remaining": data.get("keg_remaining", "640"),
                "volume_unit": data.get("volume_unit", "oz"), # 'oz' or 'L'
                
                "date": cfg.get('start_date', datetime.now().strftime("%Y-%m-%d")),
                
                # Enhanced Data for Tap Details
                "yeast": cfg.get('yeast_strain', 'Unknown'),
                "start_date": cfg.get('start_date', datetime.now().strftime("%Y-%m-%d")),
                "finish_date": datetime.now().strftime("%Y-%m-%d"),
                "tap_mode": "fermenting", 
                
                "active": True
            }
            set_config(tap_id, json.dumps(tap_data))
            return api_response(status="assigned", data=tap_data)
            
        elif action == 'pour':
            # Decrement Volume
            tap_json = get_config(tap_id)
            if not tap_json: 
                return api_response(status="error", error="Tap not configured", code=404)
            
            tap = json.loads(tap_json)
            if not tap.get("active"): 
                return api_response(status="error", error="Tap inactive", code=400)
            
            volume_to_pour = float(data.get("volume", 0.0))
            current_vol = float(tap.get("keg_remaining", 0.0))
            
            new_vol = max(0.0, current_vol - volume_to_pour)
            tap["keg_remaining"] = f"{new_vol:.2f}"
            
            set_config(tap_id, json.dumps(tap))
            return api_response(status="poured", data={"remaining": new_vol, "unit": tap.get("volume_unit", "oz")})
            
        return api_response(status="error", error="Unknown Action", code=400)
    except Exception as e:
        return handle_error(e, "Update Tap Error")

@api_bp.route('/api/label')
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
        
        img_buffer = generate_label(data)
        
        return Response(
            img_buffer,
            mimetype="image/png",
            headers={"Content-disposition": f"attachment; filename={name}_label.png"}
        )
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
def export_batch(batch_id: str) -> Tuple[Response, int]:
    """
    Export a batch to Parquet format for ML training.
    Requires batch metadata in query params or fetches from Brewfather.
    """
    try:
        from app.services.batch_exporter import export_batch_to_parquet, get_batch_metadata_from_brewfather
        from datetime import datetime
        from flask import send_file
        
        # Try to get metadata from Brewfather
        metadata = get_batch_metadata_from_brewfather(batch_id)
        
        if not metadata:
            return api_response(status="error", error="Batch not found in Brewfather", code=404)
        
        # Extract required fields
        batch_name = metadata.get('name', 'Unknown')
        recipe = metadata.get('recipe', {})
        
        # Parse dates
        brew_date = metadata.get('brewDate')
        if isinstance(brew_date, int):
            start_time = datetime.fromtimestamp(brew_date / 1000)
        else:
            start_time = datetime.fromisoformat(brew_date) if brew_date else datetime.now()
        
        # Use bottling date as end time, or now if not bottled
        bottling_date = metadata.get('bottlingDate')
        if bottling_date:
            if isinstance(bottling_date, int):
                end_time = datetime.fromtimestamp(bottling_date / 1000)
            else:
                end_time = datetime.fromisoformat(bottling_date)
        else:
            end_time = datetime.now()
        
        og = recipe.get('og', 1.050)
        fg = recipe.get('fg', 1.010)
        
        # Get yeast
        yeasts = recipe.get('yeasts', [])
        yeast = yeasts[0].get('name', 'Unknown') if yeasts else 'Unknown'
        
        style = recipe.get('style', {}).get('name', 'Unknown')
        
        # Export to Parquet
        result = export_batch_to_parquet(
            batch_id=batch_id,
            batch_name=batch_name,
            start_time=start_time,
            end_time=end_time,
            og=og,
            fg=fg,
            yeast=yeast,
            style=style
        )
        
        if result.get('status') == 'success':
            # Return the Parquet file
            return send_file(
                result['filepath'],
                mimetype='application/octet-stream',
                as_attachment=True,
                download_name=f"{batch_name}.parquet"
            )
        else:
            return api_response(status="error", error=result.get('error'), code=500)
            
    except Exception as e:
        return handle_error(e, "Batch Export Error")


@api_bp.route('/api/batches/history', methods=['GET'])
def batches_history() -> Tuple[Response, int]:
    """
    List all completed batches from Brewfather.
    """
    try:
        from app.services.batch_exporter import get_completed_batches
        
        batches = get_completed_batches()
        
        # Format response
        formatted = []
        for batch in batches:
            formatted.append({
                "id": batch.get('_id'),
                "name": batch.get('name'),
                "status": batch.get('status'),
                "brewDate": batch.get('brewDate'),
                "style": batch.get('recipe', {}).get('style', {}).get('name')
            })
        
        return api_response(data={"batches": formatted, "count": len(formatted)})
        
    except Exception as e:
        return handle_error(e, "Batch History Error")


@api_bp.route('/api/batches/aggregate', methods=['POST'])
def aggregate_batches() -> Tuple[Response, int]:
    """
    Aggregate multiple batches into a single training dataset.
    
    Request body (optional):
        {"batch_ids": ["id1", "id2", ...]}
    """
    try:
        from app.services.batch_exporter import aggregate_training_data
        
        data = request.json or {}
        batch_ids = data.get('batch_ids')
        
        result = aggregate_training_data(batch_ids)
        
        if result.get('status') == 'success':
            return api_response(data=result)
        else:
            return api_response(status="error", error=result.get('error'), code=500)
            
    except Exception as e:
        return handle_error(e, "Batch Aggregation Error")


@api_bp.route('/api/features/batch/<batch_id>', methods=['GET'])
def batch_features(batch_id: str) -> Tuple[Response, int]:
    """
    Extract features from a batch for ML training.
    """
    try:
        from app.services.batch_exporter import get_batch_metadata_from_brewfather
        from app.ml.features import extract_features_from_batch
        from datetime import datetime
        
        # Get metadata
        metadata = get_batch_metadata_from_brewfather(batch_id)
        
        if not metadata:
            return api_response(status="error", error="Batch not found", code=404)
        
        # Extract fields (similar to export_batch)
        batch_name = metadata.get('name', 'Unknown')
        recipe = metadata.get('recipe', {})
        
        brew_date = metadata.get('brewDate')
        if isinstance(brew_date, int):
            start_time = datetime.fromtimestamp(brew_date / 1000)
        else:
            start_time = datetime.fromisoformat(brew_date) if brew_date else datetime.now()
        
        bottling_date = metadata.get('bottlingDate')
        if bottling_date:
            if isinstance(bottling_date, int):
                end_time = datetime.fromtimestamp(bottling_date / 1000)
            else:
                end_time = datetime.fromisoformat(bottling_date)
        else:
            end_time = datetime.now()
        
        og = recipe.get('og', 1.050)
        fg = recipe.get('fg', 1.010)
        yeasts = recipe.get('yeasts', [])
        yeast = yeasts[0].get('name', 'Unknown') if yeasts else 'Unknown'
        style = recipe.get('style', {}).get('name', 'Unknown')
        
        # Extract features
        features = extract_features_from_batch(
            batch_name=batch_name,
            start_time=start_time,
            end_time=end_time,
            og=og,
            fg=fg,
            yeast=yeast,
            style=style
        )
        
        return api_response(data=features)
        
    except Exception as e:
        return handle_error(e, "Feature Extraction Error")

