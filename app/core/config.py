import os
import logging
import json
from typing import Optional, Dict, Any
from logging.handlers import RotatingFileHandler
from datetime import datetime, timezone
from influxdb_client import Point
from app.core.influx import write_api, query_api, INFLUX_BUCKET, INFLUX_ORG

# --- CONFIGURATION & LOGGING ---
# Use Env Var or Default to local 'data' folder
DATA_DIR = os.environ.get("BREW_BRAIN_DATA", "data")
LOG_FILE = os.path.join(DATA_DIR, "brew_brain.log")
BACKUP_DIR = os.path.join(DATA_DIR, "backups")
config_file = os.path.join(DATA_DIR, "config.json")

for d in [DATA_DIR, BACKUP_DIR]:
    if not os.path.exists(d): os.makedirs(d)

# Setup Structured Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("BrewBrain")
file_handler = RotatingFileHandler(LOG_FILE, maxBytes=1_000_000, backupCount=5)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

# Config Defaults
DEFAULTS: Dict[str, str] = {
    "offset": "0.0", "test_mode": "false", "og": "1.050", "target_fg": "1.010",
    "batch_name": "New Batch", "batch_notes": "", "start_date": datetime.now().strftime("%Y-%m-%d"),
    "bf_user": "", "bf_key": "", "alert_telegram_token": "", "alert_telegram_chat": "",
    "temp_max": "28.0", "tilt_timeout_min": "60",
    "test_sg_start": "1.060", "test_temp_base": "20.0",
    "alert_start_time": "08:00", "alert_end_time": "22:00"
}

# Config Cache
_config_cache: Dict[str, str] = DEFAULTS.copy()

def refresh_config_from_influx() -> None:
    """Reads the latest config from InfluxDB into memory."""
    global _config_cache
    try:
        # Get all config keys set in the last 365 days
        q = f'from(bucket: "{INFLUX_BUCKET}") |> range(start: -365d) |> filter(fn: (r) => r["_measurement"] == "app_config") |> last()'
        tables = query_api.query(q)
        
        # Update cache with values found in DB
        for table in tables:
            for record in table.records:
                key = record.get_field()
                val = record.get_value()
                if key and val is not None:
                    _config_cache[key] = str(val)
        
        logger.info("Config refreshed from InfluxDB")
            
    except Exception as e:
        logger.error(f"Failed to refresh config from InfluxDB: {e}")

def get_config(key: str) -> Optional[str]:
    return _config_cache.get(key)

def get_all_config() -> Dict[str, str]:
    return _config_cache

def set_config(key: str, value: Any) -> None:
    """Writes config to InfluxDB and updates memory cache."""
    global _config_cache
    str_val = str(value)
    
    # Opti-lock: Update cache immediately for responsiveness
    _config_cache[key] = str_val
    
    try:
        # Persist to InfluxDB
        p = Point("app_config").field(key, str_val).time(datetime.now(timezone.utc))
        write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=p)
    except Exception as e:
        logger.error(f"Failed to save config '{key}' to InfluxDB: {e}")
