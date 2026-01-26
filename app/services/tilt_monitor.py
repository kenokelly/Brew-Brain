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
    
    # Try multiple possible endpoints for robustness against Docker network modes
    possible_urls = [
        "http://192.168.155.226:1880/macid/all", # Direct IP
        "http://172.17.0.1:1880/macid/all",      # Docker Direct Gateway (Linux default)
        "http://host.docker.internal:1880/macid/all" # Docker Desktop / Mac
    ]
    
    success = False
    
    for url in possible_urls:
        try:
            # logger.info(f"Polling TiltAPI at {url}")
            resp = requests.get(url, timeout=3)
            
            if resp.status_code == 200:
                data = resp.json()
                
                # The new API returns a dict of devices
                if not data or not isinstance(data, dict):
                    # logger.debug(f"TiltPi API at {url} returned empty or invalid data.")
                    continue
                
                # Get the first available device
                first_device_id = list(data.keys())[0]
                first_device = data[first_device_id]
                
                # Extract essential metrics
                if first_device.get("RSSI"):
                     TILT_STATE["rssi"] = int(first_device.get("RSSI"))
                
                if first_device.get("SG"):
                     TILT_STATE["sg"] = float(first_device.get("SG"))
                
                if first_device.get("Temp"):
                     TILT_STATE["temp"] = float(first_device.get("Temp"))
                     
                # User Requested: Trust displayTemp and tempUnits from API
                TILT_STATE["display_temp"] = first_device.get("displayTemp") or first_device.get("Temp")
                TILT_STATE["temp_unit"] = first_device.get("tempUnits") or first_device.get("tempUnit")
                
                TILT_STATE["color"] = first_device.get("Color")
                
                TILT_STATE["last_seen"] = datetime.now(timezone.utc)
                TILT_STATE["last_check_status"] = "healthy"
                TILT_STATE["last_error"] = None
                
                success = True
                break # specific URL worked, stop trying others
            else:
                # logger.debug(f"TiltPi API at {url} returned status code {resp.status_code}")
                continue
                
        except Exception as e:
            # logger.debug(f"Failed to poll {url}: {e}")
            continue

    if success:
        # Write RSSI to InfluxDB for historical tracking
        # We only write if we successfully got data to avoid spamming errors or partial writes
        if TILT_STATE["rssi"] is not None:
            try:
                p = Point("sensor_health")\
                    .tag("Color", TILT_STATE.get("color", "Unknown"))\
                    .field("rssi", TILT_STATE["rssi"])\
                    .time(TILT_STATE["last_seen"])
                write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=p)
            except Exception as ex:
                logger.error(f"Failed to log RSSI to InfluxDB: {ex}")
    else:
        # Mark as unreachable only if ALL URLs failed
        TILT_STATE["last_check_status"] = "unreachable"
        TILT_STATE["last_error"] = "All endpoints failed"

def get_tilt_state():
    """Get the current memory-resident state of the Tilt sensor."""
    return TILT_STATE
