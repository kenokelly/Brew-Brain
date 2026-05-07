import pytest
from unittest.mock import mock_open, patch
import sys
import os

# Mock dependencies before import
sys.modules['core.config'] = type('MockConfig', (), {'get_config': lambda x: None})()
sys.modules['core.influx'] = type('MockInflux', (), {'query_api': None, 'INFLUX_BUCKET': 'test'})()
sys.modules['influxdb_client'] = type('MockInfluxClient', (), {'Point': None})()
sys.modules['services.tilt_monitor'] = type('MockTilt', (), {'get_tilt_state': lambda: {}})()
sys.modules['ml.prediction'] = type('MockPrediction', (), {'get_predicted_fg': lambda: {}})()

# Use relative pathing instead of absolute
app_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../app'))
if app_dir not in sys.path:
    sys.path.insert(0, app_dir)

from services.status import get_sd_io_stats

def test_get_sd_io_stats_success():
    mock_data = "100 0 200 300 400 0 500 600 0 0 0"
    with patch("builtins.open", mock_open(read_data=mock_data)):
        stats = get_sd_io_stats()

    assert stats == {
        "reads_completed": 100,
        "sectors_read": 200,
        "read_ms": 300,
        "writes_completed": 400,
        "sectors_written": 500,
        "write_ms": 600,
    }

def test_get_sd_io_stats_file_not_found():
    with patch("builtins.open", side_effect=FileNotFoundError):
        stats = get_sd_io_stats()

    assert stats == {"error": "SD card stats not available (not running on Pi)"}

def test_get_sd_io_stats_os_error():
    with patch("builtins.open", side_effect=OSError):
        stats = get_sd_io_stats()

    assert stats == {"error": "SD card stats not available (not running on Pi)"}

def test_get_sd_io_stats_index_error():
    mock_data = "100 0" # Not enough elements to unpack
    with patch("builtins.open", mock_open(read_data=mock_data)):
        stats = get_sd_io_stats()

    assert stats == {"error": "SD card stats not available (not running on Pi)"}
