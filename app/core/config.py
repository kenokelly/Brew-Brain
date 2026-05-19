import os
import logging
import json
from typing import Optional, Dict, Any
from logging.handlers import RotatingFileHandler
from datetime import datetime, timezone
from influxdb_client import Point
from core.influx import write_api, query_api, INFLUX_BUCKET, INFLUX_ORG

from pydantic import BaseModel, Field, field_validator
import tempfile
import shutil

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

# --- PYDANTIC V2 SCHEMA ---
class BrewBrainConfig(BaseModel):
    # Hardware/General
    offset: float = 0.0
    test_mode: bool = False
    temp_max: float = 28.0
    tilt_timeout_min: int = 60
    
    # Active Batch Details
    og: float = 1.050
    target_fg: float = 1.010
    batch_name: str = "New Batch"
    batch_notes: str = ""
    start_date: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    style: str = "Unknown"
    yeast_strain: str = "Unknown"
    
    # Integrations
    bf_user: str = ""
    bf_key: str = ""
    alert_telegram_token: str = ""
    alert_telegram_chat: str = ""
    
    # AI/Services
    ollama_host: str = "ollama"
    ollama_model: str = "llama3:latest"
    serp_api_key: str = ""
    
    # Simulation Defaults
    test_sg_start: float = 1.060
    test_temp_base: float = 20.0
    
    # Alerting Tuning
    alert_start_time: str = "08:00"
    alert_end_time: str = "22:00"
    alert_verbosity_min: int = 0
    report_verbosity_min: int = 60
    bypass_temp_threshold: float = 0.5
    bypass_sg_threshold: float = 0.005

    @field_validator('start_date')
    @classmethod
    def validate_date(cls, v: str) -> str:
        if v is None:
            return datetime.now().strftime("%Y-%m-%d")
        try:
            datetime.strptime(str(v), "%Y-%m-%d")
            return str(v)
        except ValueError:
            return datetime.now().strftime("%Y-%m-%d")

    @field_validator('batch_name', 'batch_notes', 'style', 'yeast_strain', 
                     'bf_user', 'bf_key', 'alert_telegram_token', 'alert_telegram_chat', 
                     'ollama_host', 'ollama_model', 'serp_api_key', 'alert_start_time', 'alert_end_time', mode='before')
    @classmethod
    def coerce_string(cls, v: Any) -> str:
        if v is None:
            return ""
        return str(v)

    @field_validator('og', mode='before')
    @classmethod
    def coerce_og(cls, v: Any) -> float:
        if v is None:
            return 1.050
        try:
            return float(v)
        except (ValueError, TypeError):
            return 1.050

    @field_validator('target_fg', mode='before')
    @classmethod
    def coerce_fg(cls, v: Any) -> float:
        if v is None:
            return 1.010
        try:
            return float(v)
        except (ValueError, TypeError):
            return 1.010

# Config Instance (Defaults to starting state)
_config_instance = BrewBrainConfig()

# Config Paths
CONFIG_PATH = os.path.join(DATA_DIR, "config.json")

def _save_config_to_file():
    """Save in-memory config to local JSON file using ATOMIC writes."""
    global _config_instance
    try:
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        # Create a temp file in the same directory to ensure it's on the same filesystem
        fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(CONFIG_PATH), prefix="config_tmp_", suffix=".json")
        with os.fdopen(fd, 'w') as f:
            f.write(_config_instance.model_dump_json(indent=2))
            f.flush()
            os.fsync(f.fileno()) # Ensure it's fully written to disk
            
        # Atomic replace
        os.replace(temp_path, CONFIG_PATH)
    except Exception as e:
        logger.error(f"Failed to atomically save config to local file: {e}")
        # Cleanup temp file if error occurred before replace
        try:
            if os.path.exists(temp_path): os.remove(temp_path)
        except Exception: pass

def _load_config_from_file() -> bool:
    """Load config from local JSON file."""
    global _config_instance
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r') as f:
                loaded = json.load(f)
                _config_instance = BrewBrainConfig.model_validate(loaded)
                return True
    except Exception as e:
        logger.warning(f"Failed to load config file: {e}")
    return False

def load_initial_config():
    """Initialize config on startup."""
    global _config_instance
    
    # Try loading from local file first (Primary)
    if _load_config_from_file():
        logger.info("Config initialized from local file")
    else:
        # Fallback to InfluxDB for migration/initial setup
        logger.info("Local config not found, attempting to refresh from InfluxDB")
        refresh_config_from_influx()
        _save_config_to_file()

def refresh_config_from_influx() -> None:
    """Reads the latest config from InfluxDB into memory."""
    global _config_instance
    try:
        # Get all config keys set in the last 365 days
        q = f'from(bucket: "{INFLUX_BUCKET}") |> range(start: -365d) |> filter(fn: (r) => r["_measurement"] == "app_config") |> last()'
        tables = query_api.query(q)
        
        found = False
        updates = {}
        # Update cache with values found in DB
        for table in tables:
            for record in table.records:
                key = record.get_field()
                val = record.get_value()
                if key and val is not None:
                    updates[key] = val
                    found = True
        
        if found:
            # Validate updates against model
            current_dict = _config_instance.model_dump()
            current_dict.update(updates)
            _config_instance = BrewBrainConfig.model_validate(current_dict)
            logger.info("Config refreshed from InfluxDB")
            _save_config_to_file()
            
    except Exception as e:
        logger.error(f"Failed to refresh config from InfluxDB: {e}")

def get_config(key: str) -> Optional[Any]:
    return getattr(_config_instance, key, None)

def get_all_config() -> Dict[str, Any]:
    return _config_instance.model_dump()

def set_config(key: str, value: Any) -> None:
    """Updates config in memory, saves to local file, and mirrors to InfluxDB."""
    global _config_instance
    
    # Validate the single update by dumping, updating, and re-validating
    try:
        current_dict = _config_instance.model_dump()
        current_dict[key] = value
        _config_instance = BrewBrainConfig.model_validate(current_dict)
    except Exception as e:
        logger.error(f"Config validation failed for key '{key}' with value '{value}': {e}")
        raise ValueError(f"Invalid config value for {key}: {e}")
    
    # Save to local file (Primary)
    _save_config_to_file()
    
    try:
        # Mirror to InfluxDB for historical tracking
        # Convert to string for InfluxDB field mapping simplicity in this app
        p = Point("app_config").field(key, str(value)).time(datetime.now(timezone.utc))
        write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=p)
    except Exception as e:
        # Don't block on InfluxDB failure anymore
        logger.debug(f"Failed to mirror config '{key}' to InfluxDB (non-critical): {e}")
