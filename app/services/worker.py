import time
import numpy as np
from datetime import datetime, timezone, timedelta
from scipy.optimize import curve_fit
from scipy.signal import medfilt
import logging
from influxdb_client import Point
from app.core.config import get_config, set_config
from app.core.influx import write_api, query_api, INFLUX_BUCKET, INFLUX_ORG
from services.telegram import send_telegram
from services.ai import analyze_yeast_history
from app.services.tilt_monitor import get_tilt_state

logger = logging.getLogger("BrewBrain")

alert_state = { "last_tilt_alert": 0, "last_temp_alert": 0 }
processing_state = { "last_processed_time": datetime.now(timezone.utc) - timedelta(minutes=10) }

def sigmoid(t, L, k, t0, C):
    return C + (L / (1 + np.exp(k * (t - t0))))

def predict_fg_from_curve(times, readings, og=None, attenuation=None):
    try:
        if len(times) < 50: return None, None
        
        clean_data = []
        for t, r in zip(times, readings):
            if 0.900 <= r <= 1.200:
                clean_data.append((t, r))
        
        if len(clean_data) < 50: return None, None
        
        clean_times, clean_readings = zip(*clean_data)
        
        start_time = clean_times[0]
        x_data = np.array([(t - start_time).total_seconds() / 3600 for t in clean_times])
        y_data = np.array(clean_readings)

        if len(y_data) > 10:
            y_data_smooth = medfilt(y_data, kernel_size=5)
        else:
            y_data_smooth = y_data

        current_min = min(y_data_smooth)
        current_max = max(y_data_smooth)
        
        # --- PHYSICS-INFORMED INITIAL GUESS ---
        # Default Guesses
        guess_L = current_max - current_min
        guess_C = current_min
        guess_k = 0.5
        
        # If we have metadata, refine the guess
        if og and attenuation:
            try:
                # Calculate expected FG based on physics
                # OG is e.g. 1.050, Attenuation is e.g. 80.0 (%)
                # Formula: Apparent Attenuation = (OG - FG) / (OG - 1)
                # So: FG = OG - (Apparent_Atten * (OG - 1))
                
                # Check for sane values
                og_val = float(og)
                att_val = float(attenuation)
                
                if og_val > 1.0 and 50 < att_val < 100:
                    expected_fg = og_val - ((att_val / 100.0) * (og_val - 1.0))
                    
                    # Log logic (if we had access to logger here)
                    # Use this expected_fg as the Asymptote (C) guess
                    guess_C = expected_fg
                    
                    # Refine L (Total Drop) guess based on OG
                    # L = OG - FG
                    guess_L = og_val - expected_fg
            except Exception as e:
                logger.debug(f"Physics guess failed, using data-driven: {e}")

        try:
            mid_gravity = current_max - ((current_max - current_min) / 2)
            idx = (np.abs(y_data_smooth - mid_gravity)).argmin()
            estimated_midpoint = x_data[idx]
            if estimated_midpoint < 0: estimated_midpoint = 24
        except Exception as e:
            logger.debug(f"Midpoint estimation failed: {e}")
            estimated_midpoint = 48

        p0 = [guess_L, guess_k, estimated_midpoint, guess_C]
        
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


def process_data_once():
    """Single execution of data processing for APScheduler."""
    try:
        offset = float(get_config("offset") or 0.0)
        test_mode = get_config("test_mode") == "true"
        target_temp = float(get_config("target_temp") or 20.0)
        current_temp = None
        points_to_write = []
        
        if test_mode:
            # Load Configurable Parameters
            sg_start = float(get_config("test_sg_start") or 1.060)
            temp_base = float(get_config("test_temp_base") or 20.0)
            
            now = datetime.now(timezone.utc)
            # progress goes from 0 to 1 over 60 seconds for demo loop
            progress = (now.minute + now.second/60) / 60
            
            # Simulate drop from sg_start by up to 0.040 points
            fake_sg = sg_start - (0.040 * progress) 
            
            # Simulate temp wave around base
            fake_temp = temp_base + (np.sin(now.timestamp()/100) * 0.5)
            fake_rssi = -60 + int(np.sin(now.timestamp()/50) * 10)
            
            current_temp = fake_temp # For Controller
            
            p = Point("test_readings")\
                .tag("Color", "TEST")\
                .field("sg", fake_sg)\
                .field("temp", fake_temp)\
                .field("rssi", fake_rssi)\
                .time(now)
            points_to_write.append(p)
            
        else:
            # Normal Processing: Calibrate existing sensor data
            # 1. Get latest temp for controller
            try:
                q_t = f'from(bucket: "{INFLUX_BUCKET}") |> range(start: -15m) |> filter(fn: (r) => r["_measurement"] == "sensor_data") |> filter(fn: (r) => r["_field"] == "Temp") |> last()'
                t_res = query_api.query(q_t)
                for t in t_res:
                    for r in t.records:
                        val = r.get_value()
                        current_temp = (val - 32) * 5/9 if val > 40 else val
            except Exception as e:
                logger.debug(f"Temp query issue: {e}")

            # 2. Process Readings for calibration/prediction
            # Query both SG and Temp in one go for efficiency
            query = f'from(bucket: "{INFLUX_BUCKET}") |> range(start: -21d) |> filter(fn: (r) => r["_measurement"] == "sensor_data") |> filter(fn: (r) => r["_field"] == "SG" or r["_field"] == "Temp")'
            tables = query_api.query(query)
            
            # Map by timestamp to align SG and Temp
            readings_map = {}
            for table in tables:
                for record in table.records:
                    ts = record.get_time()
                    if ts not in readings_map: readings_map[ts] = {"time": ts, "tags": record.values}
                    
                    if record.get_field() == "SG":
                        readings_map[ts]["sg"] = record.get_value() + offset
                    elif record.get_field() == "Temp":
                        raw_val = record.get_value()
                        readings_map[ts]["temp"] = (raw_val - 32) * 5/9 if raw_val > 40 else raw_val
            
            # Sort and filter for processing
            sorted_times = sorted(readings_map.keys())
            readings = [readings_map[t].get("sg") for t in sorted_times if "sg" in readings_map[t]]
            times = [t for t in sorted_times if "sg" in readings_map[t]]
            
            for t in sorted_times:
                data = readings_map[t]
                rec_time = data["time"]
                
                if rec_time.tzinfo is None: rec_time = rec_time.replace(tzinfo=timezone.utc)
                if processing_state["last_processed_time"].tzinfo is None: processing_state["last_processed_time"] = processing_state["last_processed_time"].replace(tzinfo=timezone.utc)
                
                if rec_time > processing_state["last_processed_time"]:
                    yeast = get_config("yeast_strain") or "Unknown"
                    p = Point("calibrated_readings")\
                        .tag("Color", data["tags"].get("Color"))\
                        .tag("yeast", yeast)
                    
                    if "sg" in data: p.field("sg", data["sg"])
                    if "temp" in data: p.field("temp", data["temp"])
                    
                    points_to_write.append(p)
                    processing_state["last_processed_time"] = rec_time

            if len(readings) > 50:
                # Gather Metadata for Informed Prediction
                og = get_config("og")
                attenuation = get_config("yeast_attenuation")
                
                pred_fg, pred_date = predict_fg_from_curve(times, readings, og, attenuation)
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


def process_data():
    while True:
        time.sleep(60)
        try:
            offset = float(get_config("offset") or 0.0)
            test_mode = get_config("test_mode") == "true"
            target_temp = float(get_config("target_temp") or 20.0)
            current_temp = None
            points_to_write = []
            
            if test_mode:
                # Load Configurable Parameters
                sg_start = float(get_config("test_sg_start") or 1.060)
                temp_base = float(get_config("test_temp_base") or 20.0)
                
                now = datetime.now(timezone.utc)
                # progress goes from 0 to 1 over 60 seconds for demo loop
                progress = (now.minute + now.second/60) / 60
                
                # Simulate drop from sg_start by up to 0.040 points
                fake_sg = sg_start - (0.040 * progress) 
                
                # Simulate temp wave around base
                fake_temp = temp_base + (np.sin(now.timestamp()/100) * 0.5)
                fake_rssi = -60 + int(np.sin(now.timestamp()/50) * 10)
                
                current_temp = fake_temp # For Controller
                
                p = Point("test_readings")\
                    .tag("Color", "TEST")\
                    .field("sg", fake_sg)\
                    .field("temp", fake_temp)\
                    .field("rssi", fake_rssi)\
                    .time(now)
                points_to_write.append(p)
                
            else:
                # Normal Processing: Calibrate existing sensor data
                # 1. Get latest temp for controller
                try:
                    q_t = f'from(bucket: "{INFLUX_BUCKET}") |> range(start: -15m) |> filter(fn: (r) => r["_measurement"] == "sensor_data") |> filter(fn: (r) => r["_field"] == "Temp") |> last()'
                    t_res = query_api.query(q_t)
                    for t in t_res:
                        for r in t.records:
                            val = r.get_value()
                            current_temp = (val - 32) * 5/9 if val > 40 else val
                except Exception as e:
                    logger.debug(f"Temp query issue: {e}")

                # 2. Process Readings for calibration/prediction
                query = f'from(bucket: "{INFLUX_BUCKET}") |> range(start: -21d) |> filter(fn: (r) => r["_measurement"] == "sensor_data") |> filter(fn: (r) => r["_field"] == "SG" or r["_field"] == "Temp")'
                tables = query_api.query(query)
                
                readings_map = {}
                for table in tables:
                    for record in table.records:
                        ts = record.get_time()
                        if ts not in readings_map: readings_map[ts] = {"time": ts, "tags": record.values}
                        
                        if record.get_field() == "SG":
                            readings_map[ts]["sg"] = record.get_value() + offset
                        elif record.get_field() == "Temp":
                            raw_val = record.get_value()
                            readings_map[ts]["temp"] = (raw_val - 32) * 5/9 if raw_val > 40 else raw_val

                sorted_times = sorted(readings_map.keys())
                readings = [readings_map[t].get("sg") for t in sorted_times if "sg" in readings_map[t]]
                times = [t for t in sorted_times if "sg" in readings_map[t]]
                
                for t in sorted_times:
                    data = readings_map[t]
                    rec_time = data["time"]
                    
                    if rec_time.tzinfo is None: rec_time = rec_time.replace(tzinfo=timezone.utc)
                    if processing_state["last_processed_time"].tzinfo is None: processing_state["last_processed_time"] = processing_state["last_processed_time"].replace(tzinfo=timezone.utc)
                    
                    if rec_time > processing_state["last_processed_time"]:
                        yeast = get_config("yeast_strain") or "Unknown"
                        p = Point("calibrated_readings")\
                            .tag("Color", data["tags"].get("Color"))\
                            .tag("yeast", yeast)
                        
                        if "sg" in data: p.field("sg", data["sg"])
                        if "temp" in data: p.field("temp", data["temp"])
                        
                        points_to_write.append(p)
                        processing_state["last_processed_time"] = rec_time


            if not test_mode and len(readings) > 50:
                # Gather Metadata for Informed Prediction
                og = get_config("og")
                attenuation = get_config("yeast_attenuation")
                
                pred_fg, pred_date = predict_fg_from_curve(times, readings, og, attenuation)
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
            time.sleep(60)

def perform_signal_loss_check(now, timeout_min, cooldown=14400):
    """
    Consolidated logic for signal loss detection with high-frequency direct monitoring.
    Fixes the '1000 minutes ago' bug by ensuring we only report recent context.
    """
    try:
        tilt_state = get_tilt_state()
        last_seen = tilt_state.get("last_seen")
        rssi = tilt_state.get("rssi")
        
        # 1. State Normalization
        has_data = False
        last_reading_str = "No Signal Data"
        
        # If we have it in memory and it's fresh, we are golden
        if last_seen:
            last_ts = last_seen.timestamp()
            elapsed_min = (now - last_ts) / 60
            if elapsed_min < timeout_min:
                has_data = True
            last_reading_str = f"{last_seen.strftime('%H:%M:%S')} UTC ({int(elapsed_min)}m ago)"

        # 2. InfluxDB Fallback (Only if memory is empty)
        if not has_data:
            # Check last 24h for any proof of life
            q_last = f'from(bucket: "{INFLUX_BUCKET}") |> range(start: -24h) |> filter(fn: (r) => r["_measurement"] == "sensor_data") |> last()'
            res = query_api.query(q_last)
            
            influx_last_ts = 0
            if res:
                for t in res:
                    for r in t.records:
                        ts = r.get_time().timestamp()
                        if ts > influx_last_ts:
                            influx_last_ts = ts
            
            if influx_last_ts > 0:
                elapsed_min_influx = (now - influx_last_ts) / 60
                if elapsed_min_influx < timeout_min:
                    has_data = True
                
                # Update string only if memory was empty or this is newer
                # (Prevents the 1000 minute bug if Influx returns old data while memory is newer or vice-versa)
                if not last_seen or influx_last_ts > last_seen.timestamp():
                    dt = datetime.fromtimestamp(influx_last_ts, tz=timezone.utc)
                    last_reading_str = f"{dt.strftime('%H:%M:%S')} UTC ({int(elapsed_min_influx)}m ago)"
        
        # 3. Alert Trigger
        if not has_data:
            if (now - alert_state["last_tilt_alert"] > cooldown):
                signal_info = f"\n*Signal Strength:* {rssi} dBm" if rssi else ""
                msg = (
                    f"⚠️ *SIGNAL LOSS ALERT*\n\n"
                    f"No Tilt signal detected for over {timeout_min} minutes.\n"
                    f"*Last Seen:* {last_reading_str}\n{signal_info}\n\n"
                    f"Check TiltPi power and orientation."
                )
                send_telegram(msg)
                alert_state["last_tilt_alert"] = now
                logger.warning(f"Signal Loss Alert: {last_reading_str}")
            
    except Exception as e:
        logger.error(f"Signal Loss Check Error: {e}")

def check_alerts():
    while True:
        time.sleep(300)
        if get_config("test_mode") == "true": continue
        try:
            now = time.time()
            local_hour = time.localtime(now).tm_hour
            
            # Quiet Hours Check
            start_str = get_config("alert_start_time") or "08:00"
            end_str = get_config("alert_end_time") or "22:00"
            try:
                start_h = int(start_str.split(":")[0])
                end_h = int(end_str.split(":")[0])
                
                # If start < end (e.g. 08 to 22), we alert if start < now < end
                # If start > end (e.g. 22 to 08), we alert if now > start OR now < end (night shift)
                # ... Wait, user wants "Quiet Hours" or "Active Hours"?
                # Request said: "not disturbed during the night". So we define ACTIVE hours.
                # Default 08:00 to 22:00 are ACTIVE hours.
                
                is_active_time = False
                if start_h < end_h:
                    if start_h <= local_hour < end_h: is_active_time = True
                else:
                    # Spans midnight (e.g. 22:00 to 08:00 active? Unlikely for "Quiet Night")
                    # Assuming inputs are ACTIVE hours.
                    if local_hour >= start_h or local_hour < end_h: is_active_time = True
                    
                if not is_active_time:
                    # It is quiet time, skip alerts
                    continue

            except Exception as e:
                logger.error(f"Time Check Error: {e}")
                # Fail open (allow alerts) if config is bad
            
            COOLDOWN = 14400 # 4 hours
            timeout_min = int(get_config("tilt_timeout_min") or 60)
            perform_signal_loss_check(now, timeout_min, COOLDOWN)
            
            max_temp = float(get_config("temp_max") or 28.0)
            yeast_max = get_config("yeast_max_temp")
            
            q_temp = f'from(bucket: "{INFLUX_BUCKET}") |> range(start: -15m) |> filter(fn: (r) => r["_measurement"] == "sensor_data") |> filter(fn: (r) => r["_field"] == "Temp") |> last()'
            tables = query_api.query(q_temp)
            for t in tables:
                for r in t.records:
                    raw_val = r.get_value()
                    val = (raw_val - 32) * 5/9 if raw_val > 40 else raw_val
                    
                    # Global Max Check
                    if val > max_temp and (now - alert_state["last_temp_alert"] > COOLDOWN):
                        send_telegram(f"🔥 WARNING: Temp {val:.1f}°C (Limit: {max_temp}°C)")
                        alert_state["last_temp_alert"] = now
                    # Yeast Specific Check
                    elif yeast_max and val > float(yeast_max) and (now - alert_state["last_temp_alert"] > COOLDOWN):
                        send_telegram(f"🔥 YEAST WARNING: Temp {val:.1f}°C exceeds {get_config('yeast_strain')} limit of {yeast_max}°C!")
                        alert_state["last_temp_alert"] = now
        except Exception as e: logger.error(f"Alert Error: {e}")

        # --- STALL DETECTION ---
        try:
            now = time.time()
            STALL_COOLDOWN = 43200 # 12 hours
            
            if (now - alert_state.get("last_stall_alert", 0)) > STALL_COOLDOWN:
                # 1. Get Current SG
                q_curr = f'from(bucket: "{INFLUX_BUCKET}") |> range(start: -1h) |> filter(fn: (r) => r["_measurement"] == "sensor_data") |> filter(fn: (r) => r["_field"] == "SG") |> last()'
                res_curr = query_api.query(q_curr)
                sg_current = None
                for t in res_curr:
                    for r in t.records: sg_current = r.get_value()

                # 2. Get SG from 24h ago
                q_prev = f'from(bucket: "{INFLUX_BUCKET}") |> range(start: -25h, stop: -24h) |> filter(fn: (r) => r["_measurement"] == "sensor_data") |> filter(fn: (r) => r["_field"] == "SG") |> last()'
                res_prev = query_api.query(q_prev)
                sg_yesterday = None
                for t in res_prev:
                    for r in t.records: sg_yesterday = r.get_value()

                if sg_current and sg_yesterday:
                    daily_drop = sg_yesterday - sg_current
                    target_fg = float(get_config("target_fg") or 1.010)
                    
                    # Log for debugging
                    logger.info(f"Stall Check: Drop={daily_drop:.4f}, Curr={sg_current:.3f}, Target={target_fg:.3f}")

                    if (daily_drop < 0.002) and (sg_current > (target_fg + 0.005)):
                        send_telegram(f"⚠️ Stall Detected! Gravity dropped only {daily_drop:.3f} points in 24h. Current: {sg_current:.3f}")
                        alert_state["last_stall_alert"] = now

        except Exception as e:
            logger.error(f"Stall Check Error: {e}")
            
        # --- YEAST ANOMALY CHECK ---
        try:
            now = time.time()
            ANOMALY_COOLDOWN = 43200 # 12 hours
            
            if (now - alert_state.get("last_anomaly_alert", 0)) > ANOMALY_COOLDOWN:
                yeast_name = get_config("yeast_strain")
                # Only check if we have a valid yeast
                if yeast_name and yeast_name != "Unknown":
                    history = analyze_yeast_history(yeast_name)
                    if history and history.get("avg_rate"):
                        # Calculate Current Rate (last 24h)
                        # Re-use queries from Stall Check for efficiency if possible
                        # But simpler to just run logic:
                        q_now = f'from(bucket: "{INFLUX_BUCKET}") |> range(start: -1h) |> filter(fn: (r) => r["_measurement"] == "calibrated_readings") |> filter(fn: (r) => r["_field"] == "sg") |> last()'
                        q_24h = f'from(bucket: "{INFLUX_BUCKET}") |> range(start: -25h, stop: -24h) |> filter(fn: (r) => r["_measurement"] == "calibrated_readings") |> filter(fn: (r) => r["_field"] == "sg") |> last()'
                        
                        curr_sg = None
                        prev_sg = None
                        
                        r1 = query_api.query(q_now)
                        for t in r1: 
                            for r in t.records: curr_sg = r.get_value()
                            
                        r2 = query_api.query(q_24h)
                        for t in r2:
                            for r in t.records: prev_sg = r.get_value()
                            
                        if curr_sg and prev_sg:
                            drop_24h = prev_sg - curr_sg
                            avg_rate = history["avg_rate"] # points/day
                            
                            logger.info(f"Anomaly Check: Drop={drop_24h:.4f}, HistRate={avg_rate:.4f} for {yeast_name}")
                            
                            # Logic: If current speed > 2.5x historical average
                            # Filter: Only if drop is significant (> 0.010) to avoid noise at start/end
                            if drop_24h > 0.010 and drop_24h > (avg_rate * 2.5):
                                send_telegram(f"⚠️ Anomaly Detected! {yeast_name} is dropping {drop_24h:.3f}/day (Normal: ~{avg_rate:.3f}). Check for Infection.")
                                alert_state["last_anomaly_alert"] = now
                                
        except Exception as e:
            logger.error(f"Anomaly Check Error: {e}")


def check_alerts_once():
    """Single execution of alert checking for APScheduler."""
    if get_config("test_mode") == "true": 
        return
    try:
        now = time.time()
        local_hour = time.localtime(now).tm_hour
        
        # Quiet Hours Check
        start_str = get_config("alert_start_time") or "08:00"
        end_str = get_config("alert_end_time") or "22:00"
        try:
            start_h = int(start_str.split(":")[0])
            end_h = int(end_str.split(":")[0])
            
            is_active_time = False
            if start_h < end_h:
                if start_h <= local_hour < end_h: is_active_time = True
            else:
                if local_hour >= start_h or local_hour < end_h: is_active_time = True
                
            if not is_active_time:
                return  # Quiet time, skip alerts

        except Exception as e:
            logger.error(f"Time Check Error: {e}")
        
        COOLDOWN = 14400
        timeout_min = int(get_config("tilt_timeout_min") or 60)
        perform_signal_loss_check(now, timeout_min, COOLDOWN)
        
        max_temp = float(get_config("temp_max") or 28.0)
        yeast_max = get_config("yeast_max_temp")
        
        q_temp = f'from(bucket: "{INFLUX_BUCKET}") |> range(start: -15m) |> filter(fn: (r) => r["_measurement"] == "sensor_data") |> filter(fn: (r) => r["_field"] == "Temp") |> last()'
        tables = query_api.query(q_temp)
        for t in tables:
            for r in t.records:
                raw_val = r.get_value()
                # Auto-detect scale: If > 40 assumption is F, else C
                val = (raw_val - 32) * 5/9 if raw_val > 40 else raw_val
                
                if val > max_temp and (now - alert_state["last_temp_alert"] > COOLDOWN):
                    send_telegram(f"🔥 WARNING: Temp {val:.1f}°C (Limit: {max_temp}°C)")
                    alert_state["last_temp_alert"] = now
                elif yeast_max and val > float(yeast_max) and (now - alert_state["last_temp_alert"] > COOLDOWN):
                    send_telegram(f"🔥 YEAST WARNING: Temp {val:.1f}°C exceeds {get_config('yeast_strain')} limit of {yeast_max}°C!")
                    alert_state["last_temp_alert"] = now
    except Exception as e: 
        logger.error(f"Alert Error: {e}")

    # Stall Detection
    try:
        now = time.time()
        STALL_COOLDOWN = 43200
        
        if (now - alert_state.get("last_stall_alert", 0)) > STALL_COOLDOWN:
            q_curr = f'from(bucket: "{INFLUX_BUCKET}") |> range(start: -1h) |> filter(fn: (r) => r["_measurement"] == "sensor_data") |> filter(fn: (r) => r["_field"] == "SG") |> last()'
            res_curr = query_api.query(q_curr)
            sg_current = None
            for t in res_curr:
                for r in t.records: sg_current = r.get_value()

            q_prev = f'from(bucket: "{INFLUX_BUCKET}") |> range(start: -25h, stop: -24h) |> filter(fn: (r) => r["_measurement"] == "sensor_data") |> filter(fn: (r) => r["_field"] == "SG") |> last()'
            res_prev = query_api.query(q_prev)
            sg_yesterday = None
            for t in res_prev:
                for r in t.records: sg_yesterday = r.get_value()

            if sg_current and sg_yesterday:
                daily_drop = sg_yesterday - sg_current
                target_fg = float(get_config("target_fg") or 1.010)
                
                if (daily_drop < 0.002) and (sg_current > (target_fg + 0.005)):
                    send_telegram(f"⚠️ Stall Detected! Gravity dropped only {daily_drop:.3f} points in 24h. Current: {sg_current:.3f}")
                    alert_state["last_stall_alert"] = now

    except Exception as e:
        logger.error(f"Stall Check Error: {e}")
