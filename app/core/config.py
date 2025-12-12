import os
import sqlite3
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime

# --- CONFIGURATION & LOGGING ---
DATA_DIR = "/data"
LOG_FILE = f"{DATA_DIR}/brew_brain.log"
DB_FILE = f"{DATA_DIR}/brewery.db"
BACKUP_DIR = f"{DATA_DIR}/backups"

for d in [DATA_DIR, BACKUP_DIR]:
    if not os.path.exists(d): os.makedirs(d)

# Setup Structured Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("BrewBrain")
file_handler = RotatingFileHandler(LOG_FILE, maxBytes=1_000_000, backupCount=5)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

# Config Cache
_config_cache = {}

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT)''')
        defaults = {
            "offset": "0.0", "test_mode": "false", "og": "1.050", "target_fg": "1.010",
            "batch_name": "New Batch", "batch_notes": "", "start_date": datetime.now().strftime("%Y-%m-%d"),
            "bf_user": "", "bf_key": "", "alert_telegram_token": "", "alert_telegram_chat": "",
            "temp_max": "28.0", "tilt_timeout_min": "60"
        }
        for k, v in defaults.items(): conn.execute("INSERT OR IGNORE INTO config (key, value) VALUES (?, ?)", (k, v))
        
    refresh_config_cache()

def refresh_config_cache():
    global _config_cache
    with sqlite3.connect(DB_FILE) as conn:
        rows = conn.execute("SELECT key, value FROM config").fetchall()
        _config_cache = {k: v for k, v in rows}

def get_config(key):
    return _config_cache.get(key)

def get_all_config():
    return _config_cache

def set_config(key, value):
    global _config_cache
    str_val = str(value)
    with sqlite3.connect(DB_FILE) as conn: 
        conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", (key, str_val))
    _config_cache[key] = str_val
