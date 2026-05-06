from app.core.config import get_config
from app.core.influx import query_api, INFLUX_BUCKET

def get_pi_temp():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f: return round(int(f.read()) / 1000, 1)
    except (FileNotFoundError, OSError): return 0.0

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
    except (ConnectionError, OSError, KeyError) as e:
        # Fail gracefully — status page should never crash
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

def get_disk_usage(path: str = "/") -> dict:
    """Returns disk usage stats for the given mount point."""
    import shutil
    try:
        usage = shutil.disk_usage(path)
        pct = round((usage.used / usage.total) * 100, 1)
        return {
            "total_bytes": usage.total,
            "used_bytes": usage.used,
            "free_bytes": usage.free,
            "used_percent": pct,
            "total_gb": round(usage.total / (1024**3), 2),
            "used_gb": round(usage.used / (1024**3), 2),
            "free_gb": round(usage.free / (1024**3), 2),
            "warning": pct >= 80.0
        }
    except OSError as e:
        return {"error": str(e)}

def get_sd_io_stats() -> dict:
    """Reads SD card I/O counters from /sys/block/mmcblk0/stat."""
    try:
        with open("/sys/block/mmcblk0/stat", "r") as f:
            parts = f.read().split()
        # Kernel doc: reads_completed, reads_merged, sectors_read, ms_reading,
        #             writes_completed, writes_merged, sectors_written, ms_writing, ...
        return {
            "reads_completed": int(parts[0]),
            "sectors_read": int(parts[2]),
            "read_ms": int(parts[3]),
            "writes_completed": int(parts[4]),
            "sectors_written": int(parts[6]),
            "write_ms": int(parts[7]),
        }
    except (FileNotFoundError, OSError, IndexError):
        return {"error": "SD card stats not available (not running on Pi)"}

def get_daily_telemetry() -> dict:
    """Calculates a 24-hour snapshot of fermentation progress."""
    try:
        from app.services.prediction import get_predicted_fg
        
        batch_name = get_config("batch_name") or "Unknown"
        og = float(get_config("og") or 1.050)
        
        # 1. Get Latest and 24h ago data
        q_now = f'from(bucket: "{INFLUX_BUCKET}") |> range(start: -1h) |> filter(fn: (r) => r["_measurement"] == "calibrated_readings") |> last()'
        q_24h = f'from(bucket: "{INFLUX_BUCKET}") |> range(start: -25h, stop: -23h) |> filter(fn: (r) => r["_measurement"] == "calibrated_readings") |> last()'
        
        res_now = query_api.query(q_now)
        res_24h = query_api.query(q_24h)
        
        sg_now, sg_24h = None, None
        temp_min, temp_max = 99.0, 0.0
        
        # Parse current
        for t in res_now:
            for r in t.records:
                if r.get_field() == "sg": sg_now = r.get_value()
        
        # Parse 24h ago and get temp range for stability check
        for t in res_24h:
            for r in t.records:
                if r.get_field() == "sg": sg_24h = r.get_value()
        
        # Temp stability check (24h window)
        q_temp = f'from(bucket: "{INFLUX_BUCKET}") |> range(start: -24h) |> filter(fn: (r) => r["_measurement"] == "calibrated_readings" and r["_field"] == "temp")'
        res_temp = query_api.query(q_temp)
        for t in res_temp:
            for r in t.records:
                val = r.get_value()
                if val < temp_min: temp_min = val
                if val > temp_max: temp_max = val
        
        if not sg_now or not sg_24h:
            return {"error": "Insufficient data for 24h diff"}
            
        sg_diff = sg_24h - sg_now
        abv_gain = round(sg_diff * 131.25, 2)
        total_abv = round((og - sg_now) * 131.25, 2)
        
        # Prediction update
        pred = get_predicted_fg()
        
        return {
            "batch_name": batch_name,
            "sg_now": round(sg_now, 3),
            "sg_24h_ago": round(sg_24h, 3),
            "sg_diff": round(sg_diff, 3),
            "abv_gain": abv_gain,
            "total_abv": total_abv,
            "temp_range": f"{temp_min:.1f} - {temp_max:.1f}°C",
            "is_stable": (temp_max - temp_min) < 1.5,
            "predicted_fg": pred.get("fg", 1.010),
            "predicted_date": pred.get("date", "Unknown")
        }
    except Exception as e:
        return {"error": str(e)}

def get_maintenance_summary() -> dict:
    """Aggregates all maintenance metrics into a single dict."""
    return {
        "disk": get_disk_usage("/"),
        "data_volume": get_disk_usage("/data"),
        "pi_temp": get_pi_temp(),
        "sd_io": get_sd_io_stats(),
    }
