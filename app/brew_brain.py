import os
import time
import sqlite3
import threading
import shutil
import requests
import logging
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

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='static')
CORS(app)

INFLUX_URL = os.getenv("INFLUX_URL", "http://influxdb:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "my-token")
INFLUX_ORG = os.getenv("INFLUX_ORG", "homebrew")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "fermentation")
DATA_DIR = "/data"
DB_FILE = f"{DATA_DIR}/brewery.db"
BACKUP_DIR = f"{DATA_DIR}/backups"

for d in [DATA_DIR, BACKUP_DIR]:
    if not os.path.exists(d): os.makedirs(d)

alert_state = { "last_tilt_alert": 0, "last_temp_alert": 0 }
processing_state = { "last_processed_time": datetime.utcnow() - timedelta(minutes=10) }

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

def get_config(key):
    with sqlite3.connect(DB_FILE) as conn:
        res = conn.execute("SELECT value FROM config WHERE key=?", (key,)).fetchone()
        return res[0] if res else None

def set_config(key, value):
    with sqlite3.connect(DB_FILE) as conn: conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", (key, str(value)))

client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = client.write_api(write_options=SYNCHRONOUS)
query_api = client.query_api()

def get_pi_temp():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f: return round(int(f.read()) / 1000, 1)
    except: return 0.0

def send_telegram(msg):
    token = get_config("alert_telegram_token")
    chat = get_config("alert_telegram_chat")
    if not token or not chat: return
    try: requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json={"chat_id": chat, "text": f"🍺 {msg}"}, timeout=5)
    except: pass

def check_alerts():
    while True:
        time.sleep(300)
        if get_config("test_mode") == "true": continue
        try:
            now = time.time()
            COOLDOWN = 14400
            timeout_min = int(get_config("tilt_timeout_min"))
            q = f'from(bucket: "{INFLUX_BUCKET}") |> range(start: -{timeout_min}m) |> filter(fn: (r) => r["_measurement"] == "sensor_data") |> count()'
            res = query_api.query(q)
            if len(res) == 0 and (now - alert_state["last_tilt_alert"] > COOLDOWN):
                send_telegram(f"⚠️ CRITICAL: No data for {timeout_min} mins.")
                alert_state["last_tilt_alert"] = now
            
            max_temp = float(get_config("temp_max"))
            q_temp = f'from(bucket: "{INFLUX_BUCKET}") |> range(start: -15m) |> filter(fn: (r) => r["_measurement"] == "sensor_data") |> filter(fn: (r) => r["_field"] == "Temp") |> last()'
            tables = query_api.query(q_temp)
            for t in tables:
                for r in t.records:
                    if r.get_value() > max_temp and (now - alert_state["last_temp_alert"] > COOLDOWN):
                        send_telegram(f"🔥 WARNING: Temp {r.get_value()}C (Limit: {max_temp}C)")
                        alert_state["last_temp_alert"] = now
        except Exception as e: logger.error(f"Alert Error: {e}")

def sigmoid(t, L, k, t0, C):
    """
    The Fermentation Model (Logistic Function).
    """
    return C + (L / (1 + np.exp(k * (t - t0))))

def predict_fermentation(times, readings):
    """
    Fits the sigmoid curve to the data and returns predicted FG and End Time.
    Includes Median Filtering and Dynamic Guessing.
    """
    try:
        if len(times) < 50: return None, None
        
        start_time = times[0]
        x_data = np.array([(t - start_time).total_seconds() / 3600 for t in times])
        y_data = np.array(readings)

        # 1. FILTERING: Apply a 5-point median filter to remove "bubble noise"
        if len(y_data) > 10:
            y_data_smooth = medfilt(y_data, kernel_size=5)
        else:
            y_data_smooth = y_data

        current_min = min(y_data_smooth)
        current_max = max(y_data_smooth)
        
        # 2. DYNAMIC GUESSING: Estimate midpoint (t0) based on data shape
        try:
            mid_gravity = current_max - ((current_max - current_min) / 2)
            idx = (np.abs(y_data_smooth - mid_gravity)).argmin()
            estimated_midpoint = x_data[idx]
            # Safety clamp for the guess
            if estimated_midpoint < 0: estimated_midpoint = 24
        except:
            estimated_midpoint = 48

        p0 = [current_max - current_min, 0.5, estimated_midpoint, current_min]
        
        # 3. CURVE FIT
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
    """
    Main Loop: Reads raw data -> Calibrates -> Predicts -> Saves to DB
    """
    while True:
        time.sleep(60)
        try:
            offset = float(get_config("offset") or 0.0)
            test_mode = get_config("test_mode") == "true"
            
            # Use 'SG' to match standard TILTpi output
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
                    if rec_time > processing_state["last_processed_time"]:
                        meas_name = "test_readings" if test_mode else "calibrated_readings"
                        p = Point(meas_name).tag("Color", record.values.get("Color")).field("sg", val).time(rec_time)
                        points_to_write.append(p)
                        processing_state["last_processed_time"] = rec_time

            if not test_mode and len(readings) > 50:
                pred_fg, pred_date = predict_fermentation(times, readings)
                if pred_fg:
                    p_pred = Point("predictions").field("predicted_fg", pred_fg).time(datetime.utcnow())
                    if pred_date:
                        days_left = (pred_date - datetime.utcnow().replace(tzinfo=None)).days
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
    recent_sg, recent_temp = 0.0, 0.0
    try:
        q = f'from(bucket: "{INFLUX_BUCKET}") |> range(start: -2h) |> filter(fn: (r) => r["_measurement"] == "calibrated_readings") |> last()'
        for t in query_api.query(q): 
            for r in t.records: recent_sg = r.get_value()
        q_t = f'from(bucket: "{INFLUX_BUCKET}") |> range(start: -2h) |> filter(fn: (r) => r["_measurement"] == "sensor_data") |> filter(fn: (r) => r["_field"] == "Temp") |> last()'
        for t in query_api.query(q_t): 
            for r in t.records: recent_temp = r.get_value()
    except: pass
    return jsonify({
        "status": "Online", "pi_temp": get_pi_temp(), "current_sg": recent_sg, "current_temp": recent_temp,
        "test_mode": get_config("test_mode") == "true", "offset": float(get_config("offset")),
        "og": float(get_config("og") or 1.050), "target_fg": float(get_config("target_fg") or 1.010),
        "batch_name": get_config("batch_name"), "batch_notes": get_config("batch_notes"), "start_date": get_config("start_date"),
        "config": {"telegram_configured": bool(get_config("alert_telegram_token"))}
    })

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
    if request.json.get('action') == 'reset':
        set_config("offset", "0.0"); return jsonify({"status": "reset"})
    manual = float(request.json.get('sg'))
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
    for k,v in request.json.items(): set_config(k, v)
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
    return "Restored"

if __name__ == '__main__':
    init_db()
    threading.Thread(target=process_data, daemon=True).start()
    threading.Thread(target=check_alerts, daemon=True).start()
    logger.info("Starting Production Server (Waitress) on port 5000...")
    serve(app, host='0.0.0.0', port=5000)