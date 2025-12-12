import shutil
import requests
import json
import base64
from datetime import datetime, timezone
from flask import Blueprint, jsonify, request, send_from_directory, send_file, Response
from core.config import get_config, set_config, get_all_config, DATA_DIR, BACKUP_DIR
from core.influx import query_api, write_api, INFLUX_BUCKET, INFLUX_ORG
from influxdb_client import Point
from services.status import get_status_dict
from services.label_maker import generate_label

api_bp = Blueprint('api', __name__)

@api_bp.route('/')
def index(): return send_from_directory('static', 'index.html')

@api_bp.route('/api/status')
def status():
    return jsonify(get_status_dict())

@api_bp.route('/api/sync_brewfather', methods=['POST'])
def sync_brewfather():
    u, k = get_config("bf_user"), get_config("bf_key")
    if not u or not k: return jsonify({"error": "Missing Credentials"}), 400
    try:
        auth = base64.b64encode(f"{u}:{k}".encode()).decode()
        r = requests.get("https://api.brewfather.app/v2/batches?status=Fermenting&include=recipe", headers={"Authorization": f"Basic {auth}"}, timeout=10)
        if r.status_code != 200: return jsonify({"error": f"API Error {r.status_code}"}), 400
        batches = r.json()
        if not batches: return jsonify({"error": "No Fermenting batch found"}), 404
        b = batches[0]
        rec = b.get('recipe', {})
        date_str = b.get('brewDate', datetime.now().strftime("%Y-%m-%d"))
        if isinstance(date_str, int): date_str = datetime.fromtimestamp(date_str/1000).strftime("%Y-%m-%d")
        set_config("batch_name", b.get('name')); set_config("og", rec.get('og')); set_config("target_fg", rec.get('fg'))
        set_config("batch_notes", b.get('notes') or rec.get('notes')); set_config("start_date", date_str)
        return jsonify({"status": "synced", "data": {"name": b.get('name')}})
    except Exception as e: return jsonify({"error": str(e)}), 500

@api_bp.route('/api/calibrate', methods=['POST'])
def calibrate():
    data = request.json
    if not data: return jsonify({"error": "No data"}), 400
    
    if data.get('action') == 'reset':
        set_config("offset", "0.0"); return jsonify({"status": "reset"})
    
    try:
        manual = float(data.get('sg'))
        source = data.get('source', 'Unknown')
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid SG value (must be number)"}), 400

    # 1. Log Manual Reading
    try:
        p = Point("manual_readings")\
            .tag("device", source)\
            .tag("type", "manual")\
            .field("sg", manual)\
            .time(datetime.now(timezone.utc))
        write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=p)
    except Exception as e:
        print(f"Manual Log Error: {e}")

    # 2. Calculate Offset from Tilt
    q = f'from(bucket: "{INFLUX_BUCKET}") |> range(start: -1h) |> filter(fn: (r) => r["_measurement"] == "sensor_data") |> filter(fn: (r) => r["_field"] == "SG") |> last()'
    tables = query_api.query(q)
    raw = None
    for t in tables:
        for r in t.records: raw = r.get_value()
    if raw:
        new_offset = manual - raw
        set_config("offset", new_offset)
        return jsonify({"status": "set", "new_offset": new_offset, "logged": True})
    
    return jsonify({"error": "No raw data from Tilt to calibrate against"}), 400

@api_bp.route('/api/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'GET':
        return jsonify(get_all_config())

    data = request.json
    if not data: return jsonify({"error": "No data"}), 400
    
    schema = {
        "og": float, "target_fg": float, "offset": float, "temp_max": float, "tilt_timeout_min": int,
        "batch_name": str, "batch_notes": str, "start_date": str,
        "test_sg_start": float, "test_temp_base": float
    }
    
    for key, value in data.items():
        if key in schema:
            try:
                schema[key](value) 
            except ValueError:
                return jsonify({"error": f"Invalid type for {key}, expected {schema[key].__name__}"}), 400
        set_config(key, value)
        
    return jsonify({"status": "saved"})

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

@api_bp.route('/api/label')
def label():
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
        return jsonify({"error": f"Label Gen Error: {e}"}), 500
