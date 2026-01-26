from app.core.config import get_config
from app.core.influx import query_api, INFLUX_BUCKET

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
        from app.services.tilt_monitor import get_tilt_state
        tilt_state = get_tilt_state()
        
        # Source measurement depends on mode
        meas = "test_readings" if test_mode else "calibrated_readings"

        q = f'from(bucket: "{INFLUX_BUCKET}") |> range(start: -2h) |> filter(fn: (r) => r["_measurement"] == "{meas}") |> last()'
        for t in query_api.query(q): 
            for r in t.records: 
                if r.get_field() == "sg": recent_sg = r.get_value()
                if r.get_field() == "temp": recent_temp = r.get_value()
                if test_mode and r.get_field() == "rssi": recent_rssi = r.get_value()
                last_sync = r.get_time()

        if not test_mode:
            # PRIORITIZE Real-Time Memory State (TILT_STATE)
            # This ensures we see exactly what the TiltPi API sees right now
            if tilt_state.get("rssi") is not None:
                recent_rssi = tilt_state["rssi"]
            if tilt_state.get("last_seen"):
                last_sync = tilt_state["last_seen"]
            
            # Use raw API values if available, applying local calibration
            if tilt_state.get("sg"):
                raw_sg = tilt_state["sg"]
                offset = float(get_config("offset") or 0.0)
                recent_sg = raw_sg + offset
                
            if tilt_state.get("display_temp"):
                # Use User-Requested API value directly without conversion
                recent_temp = float(tilt_state["display_temp"])
                recent_unit = tilt_state.get("temp_unit") or "C" # Default to C, never convert
            elif tilt_state.get("temp"):
                # Fallback to raw Temp
                raw_temp = tilt_state["temp"]
                if raw_temp > 40:
                    recent_temp = (raw_temp - 32) * 5/9
                    recent_unit = "C" # Converted
                else:
                    recent_temp = raw_temp
                    recent_unit = "C" # Assumed C

            # If Memory State is empty/stale, fall back to InfluxDB (e.g. on fresh restart before first poll)
            if recent_sg == 0.0 or recent_temp == 0.0:
                 # Original Influx Fallback Logic...
                 pass # We keep the query logic above, this just overrides it if TILT_STATE is good.
    except Exception as e:
        # logger.error(f"Status Error: {e}")
        pass


    return {
        "status": "Online", "pi_temp": get_pi_temp(), 
        "sg": recent_sg if recent_sg > 0 else None, 
        "temp": recent_temp if recent_temp > 0 else None, 
        "temp_unit": locals().get("recent_unit", "C"), 
        "rssi": recent_rssi,
        "last_sync": last_sync.isoformat() if last_sync else None,
        "test_mode": test_mode, "offset": float(get_config("offset") or 0),
        "og": float(get_config("og") or 1.050), "target_fg": float(get_config("target_fg") or 1.010),
        "batch_name": get_config("batch_name"), "batch_notes": get_config("batch_notes"), "start_date": get_config("start_date"),
        "config": {"telegram_configured": bool(get_config("alert_telegram_token"))}
    }
