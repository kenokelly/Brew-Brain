import os
import logging
import json
from typing import Optional, Dict, Any
from logging.handlers import RotatingFileHandler
from datetime import datetime, timezone
from influxdb_client import Point
from core.influx import write_api, query_api, INFLUX_BUCKET, INFLUX_ORG

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
    "alert_start_time": "08:00", "alert_end_time": "22:00",
    "alert_verbosity_min": "0", "report_verbosity_min": "60",
    "bypass_temp_threshold": "0.5", "bypass_sg_threshold": "0.005",
    "ollama_host": "ollama", "ollama_model": "llama3:latest"
}

# Config Cache
_config_cache: Dict[str, str] = DEFAULTS.copy()

# Config Paths
CONFIG_PATH = os.path.join(DATA_DIR, "config.json")

def _save_config_to_file():
    """Save in-memory cache to local JSON file."""
    global _config_cache
    try:
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, 'w') as f:
            json.dump(_config_cache, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save config to local file: {e}")

def _load_config_from_file() -> bool:
    """Load config from local JSON file."""
    global _config_cache
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r') as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    _config_cache.update(loaded)
                    return True
    except Exception as e:
        logger.warning(f"Failed to load config file: {e}")
    return False

def load_initial_config():
    """Initialize config on startup."""
    global _config_cache
    _config_cache.update(DEFAULTS)
    
    # Try loading from local file first (Primary)
    if _load_config_from_file():
        logger.info("Config initialized from local file")
    else:
        # Fallback to InfluxDB for migration/initial setup
        logger.info("Local config not found, attempting to refresh from InfluxDB")
        refresh_config_from_influx()
        if any(_config_cache[k] != DEFAULTS[k] for k in DEFAULTS):
            _save_config_to_file()

def refresh_config_from_influx() -> None:
    """Reads the latest config from InfluxDB into memory."""
    global _config_cache
    try:
        # Get all config keys set in the last 365 days
        q = f'from(bucket: "{INFLUX_BUCKET}") |> range(start: -365d) |> filter(fn: (r) => r["_measurement"] == "app_config") |> last()'
        tables = query_api.query(q)
        
        found = False
        # Update cache with values found in DB
        for table in tables:
            for record in table.records:
                key = record.get_field()
                val = record.get_value()
                if key and val is not None:
                    _config_cache[key] = str(val)
                    found = True
        
        if found:
            logger.info("Config refreshed from InfluxDB")
            _save_config_to_file()
            
    except Exception as e:
        logger.error(f"Failed to refresh config from InfluxDB: {e}")

def get_config(key: str) -> Optional[str]:
    return _config_cache.get(key)

def get_all_config() -> Dict[str, str]:
    return _config_cache

def set_config(key: str, value: Any) -> None:
    """Updates config in memory, saves to local file, and mirrors to InfluxDB."""
    global _config_cache
    str_val = str(value)
    
    # Update cache and local file (Primary)
    _config_cache[key] = str_val
    _save_config_to_file()
    
    try:
        # Mirror to InfluxDB for historical tracking
        p = Point("app_config").field(key, str_val).time(datetime.now(timezone.utc))
        write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=p)
    except Exception as e:
        # Don't block on InfluxDB failure anymore
        logger.debug(f"Failed to mirror config '{key}' to InfluxDB (non-critical): {e}")
