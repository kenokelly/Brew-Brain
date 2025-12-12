import shutil
import requests
import base64
from datetime import datetime
from flask import Blueprint, jsonify, request, send_from_directory, send_file
from core.config import get_config, set_config, get_all_config, DATA_DIR, BACKUP_DIR
from core.influx import query_api, INFLUX_BUCKET
from services.status import get_status_dict

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
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid SG value (must be number)"}), 400

    q = f'from(bucket: "{INFLUX_BUCKET}") |> range(start: -1h) |> filter(fn: (r) => r["_measurement"] == "sensor_data") |> filter(fn: (r) => r["_field"] == "SG") |> last()'
    tables = query_api.query(q)
    raw = None
    for t in tables:
        for r in t.records: raw = r.get_value()
    if raw:
        set_config("offset", manual - raw); return jsonify({"status": "set"})
    return jsonify({"error": "No raw data"}), 400

@api_bp.route('/api/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'GET':
        return jsonify(get_all_config())

    data = request.json
    if not data: return jsonify({"error": "No data"}), 400
    
    schema = {
        "og": float, "target_fg": float, "offset": float, "temp_max": float, "tilt_timeout_min": int,
        "batch_name": str, "batch_notes": str, "start_date": str
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
    shutil.make_archive(f"{BACKUP_DIR}/brew_backup", 'zip', DATA_DIR)
    return send_file(f"{BACKUP_DIR}/brew_backup.zip", as_attachment=True)

@api_bp.route('/api/restore', methods=['POST'])
def restore():
    f = request.files['file']
    f.save(f"{BACKUP_DIR}/restore.zip")
    shutil.unpack_archive(f"{BACKUP_DIR}/restore.zip", DATA_DIR)
    from core.config import refresh_config_cache
    refresh_config_cache()
    return "Restored"
