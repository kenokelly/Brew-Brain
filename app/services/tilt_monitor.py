import requests
import logging
from datetime import datetime, timezone
from app.core.config import get_config
from app.core.influx import write_api, INFLUX_BUCKET, INFLUX_ORG
from influxdb_client import Point

logger = logging.getLogger("BrewBrain")

# Shared state for real-time monitoring
# This will be updated every 15 seconds
TILT_STATE = {
    "last_seen": None,
    "rssi": None,
    "sg": None,
    "temp": None,
    "color": None,
    "last_check_status": "startup",
    "last_error": None
}

def poll_tilt_api():
    """
    Directly poll the TiltPi Node-RED API for the latest sensor metrics.
    Updates the global TILT_STATE.
    """
    global TILT_STATE
    
    # Use the static IP of the Pi as the target
    url = "http://192.168.155.226:1880/macid/all"
    
    try:
        # logger.info(f"Polling TiltAPI at {url}")
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list) and len(data) > 0:
                # Assuming the first device is the target Tilt
                first_device = data[0]
                
                # Extract essential metrics
                TILT_STATE["rssi"] = first_device.get("rssi")
                
                # Try common keys for SG/Temp (TiltPi varies sometimes)
                raw_sg = first_device.get("SG") or first_device.get("SpecificGravity")
                raw_temp = first_device.get("Temp") or first_device.get("Temperature")
                
                if raw_sg: TILT_STATE["sg"] = float(raw_sg)
                if raw_temp: TILT_STATE["temp"] = float(raw_temp)
                
                # User Requested: Trust displayTemp and tempUnits from API
                TILT_STATE["display_temp"] = first_device.get("displayTemp") or first_device.get("Temp")
                TILT_STATE["temp_unit"] = first_device.get("tempUnits") or first_device.get("tempUnit") or "F" # Default to F if missing as per Tilt standard
                
                TILT_STATE["color"] = first_device.get("Color")
                
                # Debug Log
                # logger.info(f"Tilt Poll Success: Temp={TILT_STATE.get('temp')}, Display={TILT_STATE.get('display_temp')}, Unit={TILT_STATE.get('temp_unit')}")
                
                TILT_STATE["last_seen"] = datetime.now(timezone.utc)
                TILT_STATE["last_check_status"] = "healthy"
                TILT_STATE["last_error"] = None
                
                # Write RSSI to InfluxDB for historical tracking
                try:
                    p = Point("sensor_health")\
                        .tag("Color", first_device.get("Color", "Unknown"))\
                        .field("rssi", TILT_STATE["rssi"])\
                        .time(TILT_STATE["last_seen"])
                    write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=p)
                except Exception as ex:
                    logger.error(f"Failed to log RSSI to InfluxDB: {ex}")
                    
            else:
                TILT_STATE["last_check_status"] = "no_devices"
                logger.warning("TiltPi API returned successfully but with no devices.")
        else:
            TILT_STATE["last_check_status"] = f"error_{resp.status_code}"
            TILT_STATE["last_error"] = f"HTTP {resp.status_code}"
            
    except requests.exceptions.RequestException as e:
        TILT_STATE["last_check_status"] = "unreachable"
        TILT_STATE["last_error"] = str(e)
        logger.error(f"TiltPi API Polling Error: {e}")

def get_tilt_state():
    """Get the current memory-resident state of the Tilt sensor."""
    return TILT_STATE
