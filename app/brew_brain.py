import os
import time
import sqlite3
import threading
import shutil
import requests
import logging
from logging.handlers import RotatingFileHandler
import base64
import numpy as np
from scipy.optimize import curve_fit
from scipy.signal import medfilt
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from waitress import serve

# --- CONFIGURATION & LOGGING ---
DATA_DIR = "/data"
LOG_FILE = f"{DATA_DIR}/brew_brain.log"
DB_FILE = f"{DATA_DIR}/brewery.db"
BACKUP_DIR = f"{DATA_DIR}/backups"

for d in [DATA_DIR, BACKUP_DIR]:
    if not os.path.exists(d): os.makedirs(d)

# Setup Structured Logging (Rotating File Handler)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("BrewBrain")
file_handler = RotatingFileHandler(LOG_FILE, maxBytes=1_000_000, backupCount=5)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

app = Flask(__name__, static_folder='static')
CORS(app)

INFLUX_URL = os.getenv("INFLUX_URL", "http://influxdb:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "my-token")
INFLUX_ORG = os.getenv("INFLUX_ORG", "homebrew")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "fermentation")

# Config Cache (Reduces SD Card I/O)
_config_cache = {}

alert_state = { "last_tilt_alert": 0, "last_temp_alert": 0 }
from datetime import timezone
processing_state = { "last_processed_time": datetime.now(timezone.utc) - timedelta(minutes=10) }

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT)''')
        defaults = {
            "offset": "0.0", "test_mode": "false", "og": "1.050", "target_fg": "1.010",
            "batch_name": "New Batch", "batch_notes": "", "start_date": datetime.now().strftime("%Y-%m-%d"),
            "bf_user": "", "bf_key": "", "alert_telegram_token": "", "alert_telegram_chat": "",
            "temp_max": "28.0", "tilt_timeout_min": "60"
        }
        for k, v in defaults.items(): conn.execute("INSERT OR IGNORE INTO config (key, value) VALUES (?, ?)", (k, v))
        
    # Prime the cache
    refresh_config_cache()

def refresh_config_cache():
    """Reads all config from DB into memory."""
    global _config_cache
    with sqlite3.connect(DB_FILE) as conn:
        rows = conn.execute("SELECT key, value FROM config").fetchall()
        _config_cache = {k: v for k, v in rows}

def get_config(key):
    """Reads from memory cache."""
    return _config_cache.get(key)

def set_config(key, value):
    """Writes to DB and updates cache."""
    global _config_cache
    str_val = str(value)
    with sqlite3.connect(DB_FILE) as conn: 
        conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", (key, str_val))
    _config_cache[key] = str_val  # Update cache immediately

client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = client.write_api(write_options=SYNCHRONOUS)
query_api = client.query_api()

def get_pi_temp():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f: return round(int(f.read()) / 1000, 1)
    except: return 0.0

def send_telegram(msg, target_chat=None):
    token = get_config("alert_telegram_token")
    chat = target_chat or get_config("alert_telegram_chat")
    if not token or not chat: return
    try: 
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage", 
            json={"chat_id": chat, "text": msg, "parse_mode": "Markdown"}, 
            timeout=5
        )
    except Exception as e:
        logger.error(f"Failed to send Telegram: {e}")

def get_status_dict():
    recent_sg, recent_temp = 0.0, 0.0
    try:
        q = f'from(bucket: "{INFLUX_BUCKET}") |> range(start: -2h) |> filter(fn: (r) => r["_measurement"] == "calibrated_readings") |> last()'
        for t in query_api.query(q): 
            for r in t.records: recent_sg = r.get_value()
        q_t = f'from(bucket: "{INFLUX_BUCKET}") |> range(start: -2h) |> filter(fn: (r) => r["_measurement"] == "sensor_data") |> filter(fn: (r) => r["_field"] == "Temp") |> last()'
        for t in query_api.query(q_t): 
            for r in t.records: 
                val = r.get_value()
                recent_temp = (val - 32) * 5/9  # Convert F to C
    except: pass

    return {
        "status": "Online", "pi_temp": get_pi_temp(), "sg": recent_sg, "temp": recent_temp,
        "test_mode": get_config("test_mode") == "true", "offset": float(get_config("offset") or 0),
        "og": float(get_config("og") or 1.050), "target_fg": float(get_config("target_fg") or 1.010),
        "batch_name": get_config("batch_name"), "batch_notes": get_config("batch_notes"), "start_date": get_config("start_date"),
        "config": {"telegram_configured": bool(get_config("alert_telegram_token"))}
    }

def handle_telegram_command(chat_id, command, text):
    cmd = command.lower().strip()
    if cmd == "/status":
        s = get_status_dict()
        sg = s.get('sg', 0) or 0
        temp = s.get('temp', 0) or 0
        og = s.get('og', 0)
        fg = s.get('target_fg', 0)
        abv = (og - sg) * 131.25 if sg > 0 else 0
        
        msg = (
            f"🍺 *Brew Brain Status*\n"
            f"🏷 *Batch:* {s.get('batch_name')}\n"
            f"🌡 *Temp:* {temp}°C\n"
            f"⚖️ *Gravity:* {sg:.3f} (Target: {fg:.3f})\n"
            f"📊 *ABV:* {abv:.1f}%\n"
            f"💾 *CPU:* {s.get('pi_temp')}°C"
        )
        send_telegram(msg, chat_id)
    elif cmd == "/help":
        send_telegram("🤖 *Commands:*\n/status - Current readings\n/ping - Check connectivity", chat_id)
    elif cmd == "/ping":
        send_telegram("🏓 Pong! I am online.", chat_id)

def telegram_poller():
    logger.info("Telegram Poller Started")
    last_update_id = 0
    while True:
        token = get_config("alert_telegram_token")
        if not token:
            time.sleep(30)
            continue
        try:
            url = f"https://api.telegram.org/bot{token}/getUpdates"
            params = {"offset": last_update_id + 1, "timeout": 30}
            resp = requests.get(url, params=params, timeout=35)
            if resp.status_code == 200:
                data = resp.json()
                for result in data.get("result", []):
                    last_update_id = result["update_id"]
                    message = result.get("message", {})
                    text = message.get("text", "")
                    chat_id = message.get("chat", {}).get("id")
                    
                    configured_chat = get_config("alert_telegram_chat")
                    if str(chat_id) != str(configured_chat):
                        continue
                    if text.startswith("/"):
                        parts = text.split(" ", 1)
                        cmd = parts[0]
                        payload = parts[1] if len(parts) > 1 else ""
                        handle_telegram_command(chat_id, cmd, payload)
        except Exception as e:
            logger.error(f"Telegram Poll Error: {e}")
            time.sleep(15)

def check_alerts():
    while True:
        time.sleep(300)
        if get_config("test_mode") == "true": continue
        try:
            now = time.time()
            COOLDOWN = 14400
            timeout_min = int(get_config("tilt_timeout_min") or 60)
            q = f'from(bucket: "{INFLUX_BUCKET}") |> range(start: -{timeout_min}m) |> filter(fn: (r) => r["_measurement"] == "sensor_data") |> count()'
            res = query_api.query(q)
            if len(res) == 0 and (now - alert_state["last_tilt_alert"] > COOLDOWN):
                send_telegram(f"⚠️ CRITICAL: No data for {timeout_min} mins.")
                alert_state["last_tilt_alert"] = now
            
            max_temp = float(get_config("temp_max") or 28.0)
            q_temp = f'from(bucket: "{INFLUX_BUCKET}") |> range(start: -15m) |> filter(fn: (r) => r["_measurement"] == "sensor_data") |> filter(fn: (r) => r["_field"] == "Temp") |> last()'
            tables = query_api.query(q_temp)
            for t in tables:
                for r in t.records:
                    if r.get_value() > max_temp and (now - alert_state["last_temp_alert"] > COOLDOWN):
                        send_telegram(f"🔥 WARNING: Temp {r.get_value()}C (Limit: {max_temp}C)")
                        alert_state["last_temp_alert"] = now
        except Exception as e: logger.error(f"Alert Error: {e}")

def sigmoid(t, L, k, t0, C):
    return C + (L / (1 + np.exp(k * (t - t0))))

def predict_fermentation(times, readings):
    try:
        if len(times) < 50: return None, None
        
        # 1. ROBUST FILTERING: Discard impossible beer values
        # Specific Gravity should generally be between 0.900 (dry spirit) and 1.200 (syrup)
        clean_data = []
        for t, r in zip(times, readings):
            if 0.900 <= r <= 1.200:
                clean_data.append((t, r))
        
        if len(clean_data) < 50: return None, None # Not enough valid data
        
        clean_times, clean_readings = zip(*clean_data)
        
        start_time = clean_times[0]
        x_data = np.array([(t - start_time).total_seconds() / 3600 for t in clean_times])
        y_data = np.array(clean_readings)

        # 2. Median Filter for Bubble Noise
        if len(y_data) > 10:
            y_data_smooth = medfilt(y_data, kernel_size=5)
        else:
            y_data_smooth = y_data

        current_min = min(y_data_smooth)
        current_max = max(y_data_smooth)
        
        # 3. Dynamic Guessing
        try:
            mid_gravity = current_max - ((current_max - current_min) / 2)
            idx = (np.abs(y_data_smooth - mid_gravity)).argmin()
            estimated_midpoint = x_data[idx]
            if estimated_midpoint < 0: estimated_midpoint = 24
        except:
            estimated_midpoint = 48

        p0 = [current_max - current_min, 0.5, estimated_midpoint, current_min]
        
        # 4. Curve Fit
        popt, _ = curve_fit(sigmoid, x_data, y_data_smooth, p0=p0, maxfev=20000, 
                           bounds=([0, 0, 0, 0.900], [0.2, 5, 1000, 1.200]))
        
        L_fit, k_fit, t0_fit, C_fit = popt
        predicted_fg = round(C_fit, 3)
        hours_to_completion = t0_fit - (1/k_fit) * np.log(0.001 / (L_fit - 0.001))
        
        if np.isnan(hours_to_completion) or hours_to_completion < 0:
            return predicted_fg, None
            
        completion_date = start_time + timedelta(hours=hours_to_completion)
        return predicted_fg, completion_date

    except Exception as e:
        logger.error(f"Prediction Math Error: {e}")
        return None, None

def process_data():
    while True:
        time.sleep(60)
        try:
            offset = float(get_config("offset") or 0.0)
            test_mode = get_config("test_mode") == "true"
            
            query = f'from(bucket: "{INFLUX_BUCKET}") |> range(start: -21d) |> filter(fn: (r) => r["_measurement"] == "sensor_data") |> filter(fn: (r) => r["_field"] == "SG")'
            tables = query_api.query(query)
            
            times = []
            readings = []
            points_to_write = []
            
            for table in tables:
                for record in table.records:
                    rec_time = record.get_time()
                    val = record.get_value() + offset
                    times.append(rec_time)
                    readings.append(val)
                    if rec_time.tzinfo is None: rec_time = rec_time.replace(tzinfo=timezone.utc)
                    if processing_state["last_processed_time"].tzinfo is None: processing_state["last_processed_time"] = processing_state["last_processed_time"].replace(tzinfo=timezone.utc)
                    if rec_time > processing_state["last_processed_time"]:
                        meas_name = "test_readings" if test_mode else "calibrated_readings"
                        p = Point(meas_name).tag("Color", record.values.get("Color")).field("sg", val).time(rec_time)
                        points_to_write.append(p)
                        processing_state["last_processed_time"] = rec_time

            if not test_mode and len(readings) > 50:
                pred_fg, pred_date = predict_fermentation(times, readings)
                if pred_fg:
                    p_pred = Point("predictions").field("predicted_fg", pred_fg).time(datetime.now(timezone.utc))
                    if pred_date:
                        days_left = (pred_date - datetime.now(timezone.utc)).days
                        p_pred.field("days_remaining", days_left)
                        set_config("prediction_end_date", pred_date.strftime("%Y-%m-%d %H:%M"))
                    points_to_write.append(p_pred)

            if points_to_write:
                write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=points_to_write)
                logger.info(f"Wrote {len(points_to_write)} points")
                
        except Exception as e:
            logger.error(f"Sync Loop Error: {e}")
            time.sleep(60)

@app.route('/')
def index(): return send_from_directory('static', 'index.html')

@app.route('/api/status')
def status():
    return jsonify(get_status_dict())

@app.route('/api/sync_brewfather', methods=['POST'])
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

@app.route('/api/calibrate', methods=['POST'])
def calibrate():
    # Input Validation
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

@app.route('/api/settings', methods=['POST'])
def settings():
    data = request.json
    if not data: return jsonify({"error": "No data"}), 400
    
    # TYPE VALIDATION
    # Defines simple schema for critical fields
    schema = {
        "og": float, "target_fg": float, "offset": float, "temp_max": float, "tilt_timeout_min": int,
        "batch_name": str, "batch_notes": str, "start_date": str
    }
    
    for key, value in data.items():
        if key in schema:
            try:
                # Attempt cast to validate
                schema[key](value) 
            except ValueError:
                return jsonify({"error": f"Invalid type for {key}, expected {schema[key].__name__}"}), 400
        set_config(key, value)
        
    return jsonify({"status": "saved"})

@app.route('/api/backup')
def backup():
    shutil.make_archive(f"{BACKUP_DIR}/brew_backup", 'zip', DATA_DIR)
    return send_file(f"{BACKUP_DIR}/brew_backup.zip", as_attachment=True)

@app.route('/api/restore', methods=['POST'])
def restore():
    f = request.files['file']
    f.save(f"{BACKUP_DIR}/restore.zip")
    shutil.unpack_archive(f"{BACKUP_DIR}/restore.zip", DATA_DIR)
    # Refresh cache after restore
    refresh_config_cache()
    return "Restored"

if __name__ == '__main__':
    init_db()
    threading.Thread(target=process_data, daemon=True).start()
    threading.Thread(target=check_alerts, daemon=True).start()
    threading.Thread(target=telegram_poller, daemon=True).start()
    
    logger.info("Starting Production Server (Waitress) on port 5000...")
    serve(app, host='0.0.0.0', port=5000)