from core.config import get_config
from core.influx import query_api, INFLUX_BUCKET

def get_pi_temp():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f: return round(int(f.read()) / 1000, 1)
    except: return 0.0

def get_status_dict():
    test_mode = get_config("test_mode") == "true"
    recent_sg, recent_temp = 0.0, 0.0
    recent_rssi = None
    last_sync = None
    
    try:
        # Source measurement depends on mode
        meas = "test_readings" if test_mode else "calibrated_readings"
        sensor_meas = "test_readings" if test_mode else "sensor_data"

        q = f'from(bucket: "{INFLUX_BUCKET}") |> range(start: -2h) |> filter(fn: (r) => r["_measurement"] == "{meas}") |> last()'
        for t in query_api.query(q): 
            for r in t.records: 
                if r.get_field() == "sg": recent_sg = r.get_value()
                if test_mode and r.get_field() == "temp": recent_temp = r.get_value()
                if test_mode and r.get_field() == "rssi": recent_rssi = r.get_value()
                last_sync = r.get_time()

        if not test_mode:
            # Normal mode: Fetch Temp/RSSI from sensor_data
            q_t = f'from(bucket: "{INFLUX_BUCKET}") |> range(start: -2h) |> filter(fn: (r) => r["_measurement"] == "{sensor_meas}") |> filter(fn: (r) => r["_field"] == "Temp") |> last()'
            for t in query_api.query(q_t): 
                for r in t.records: 
                    val = r.get_value()
                    recent_temp = (val - 32) * 5/9  # Convert F to C
                    if not last_sync: last_sync = r.get_time()

            q_rssi = f'from(bucket: "{INFLUX_BUCKET}") |> range(start: -2h) |> filter(fn: (r) => r["_measurement"] == "{sensor_meas}") |> filter(fn: (r) => r["_field"] == "rssi") |> last()'
            for t in query_api.query(q_rssi):
                for r in t.records: recent_rssi = r.get_value()
    except: pass

    return {
        "status": "Online", "pi_temp": get_pi_temp(), "sg": recent_sg, "temp": recent_temp, "rssi": recent_rssi,
        "last_sync": last_sync.isoformat() if last_sync else None,
        "test_mode": test_mode, "offset": float(get_config("offset") or 0),
        "og": float(get_config("og") or 1.050), "target_fg": float(get_config("target_fg") or 1.010),
        "batch_name": get_config("batch_name"), "batch_notes": get_config("batch_notes"), "start_date": get_config("start_date"),
        "config": {"telegram_configured": bool(get_config("alert_telegram_token"))}
    }
