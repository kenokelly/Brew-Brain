import time
import numpy as np
from datetime import datetime, timezone, timedelta
from scipy.optimize import curve_fit
from scipy.signal import medfilt
import logging
from influxdb_client import Point
from core.config import get_config, set_config
from core.influx import write_api, query_api, INFLUX_BUCKET, INFLUX_ORG
from services.telegram import send_telegram

logger = logging.getLogger("BrewBrain")

alert_state = { "last_tilt_alert": 0, "last_temp_alert": 0 }
processing_state = { "last_processed_time": datetime.now(timezone.utc) - timedelta(minutes=10) }

def sigmoid(t, L, k, t0, C):
    return C + (L / (1 + np.exp(k * (t - t0))))

def predict_fermentation(times, readings):
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
        
        try:
            mid_gravity = current_max - ((current_max - current_min) / 2)
            idx = (np.abs(y_data_smooth - mid_gravity)).argmin()
            estimated_midpoint = x_data[idx]
            if estimated_midpoint < 0: estimated_midpoint = 24
        except:
            estimated_midpoint = 48

        p0 = [current_max - current_min, 0.5, estimated_midpoint, current_min]
        
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
                
                p = Point("test_readings")\
                    .tag("Color", "TEST")\
                    .field("sg", fake_sg)\
                    .field("temp", fake_temp)\
                    .field("rssi", fake_rssi)\
                    .time(now)
                points_to_write.append(p)
                
            else:
                query = f'from(bucket: "{INFLUX_BUCKET}") |> range(start: -21d) |> filter(fn: (r) => r["_measurement"] == "sensor_data") |> filter(fn: (r) => r["_field"] == "SG")'
                tables = query_api.query(query)
                readings = []
                times = []
                
                for table in tables:
                    for record in table.records:
                        rec_time = record.get_time()
                        val = record.get_value() + offset
                        times.append(rec_time)
                        readings.append(val)
                        if rec_time.tzinfo is None: rec_time = rec_time.replace(tzinfo=timezone.utc)
                        if processing_state["last_processed_time"].tzinfo is None: processing_state["last_processed_time"] = processing_state["last_processed_time"].replace(tzinfo=timezone.utc)
                        if rec_time > processing_state["last_processed_time"]:
                            p = Point("calibrated_readings").tag("Color", record.values.get("Color")).field("sg", val).time(rec_time)
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
