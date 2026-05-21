import sys
import os
import pytest
import datetime
from unittest.mock import patch, mock_open, MagicMock

# Ensure app is in path
app_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../app'))
if app_dir not in sys.path:
    sys.path.insert(0, app_dir)

# Save original modules
_original_modules = {}
_keys_to_remove = []
for key in ["influxdb_client", "influxdb_client.client", "influxdb_client.client.write_api", "core.config", "core.influx", "services.tilt_monitor", "ml.prediction"]:
    if key in sys.modules:
        _original_modules[key] = sys.modules[key]
    else:
        _keys_to_remove.append(key)

# Mock dependencies before import to avoid real connections/failures
mock_influx = MagicMock()
sys.modules["influxdb_client"] = MagicMock()
sys.modules["influxdb_client.client"] = MagicMock()
sys.modules["influxdb_client.client.write_api"] = MagicMock()
sys.modules['core.config'] = type('MockConfig', (), {'get_config': lambda x: None})()
sys.modules['core.influx'] = type('MockInflux', (), {'query_api': MagicMock(), 'INFLUX_BUCKET': 'test'})()
sys.modules['services.tilt_monitor'] = type('MockTilt', (), {'get_tilt_state': lambda: {}})()
sys.modules['ml.prediction'] = type('MockPrediction', (), {'get_predicted_fg': lambda: {}})()

from app.services.status import (
    get_pi_temp,
    get_status_dict,
    get_disk_usage,
    get_sd_io_stats,
    get_daily_telemetry,
    get_maintenance_summary
)

# Restore original modules to prevent side-effects on other test files
for key, val in _original_modules.items():
    sys.modules[key] = val
for key in _keys_to_remove:
    if key in sys.modules:
        del sys.modules[key]


def test_get_pi_temp_success():
    with patch("builtins.open", mock_open(read_data="45000")):
        temp = get_pi_temp()
        assert temp == 45.0

def test_get_pi_temp_failure():
    with patch("builtins.open", side_effect=FileNotFoundError):
        temp = get_pi_temp()
        assert temp == 0.0

    with patch("builtins.open", side_effect=OSError):
        temp = get_pi_temp()
        assert temp == 0.0


@patch("app.services.status.get_config")
@patch("app.services.status.query_api.query")
@patch("app.services.status.get_tilt_state", create=True)
def test_get_status_dict_test_mode(mock_get_tilt_state, mock_query, mock_get_config):
    def get_config_side_effect(key):
        configs = {
            "test_mode": "true",
            "offset": "0.0",
            "og": "1.050",
            "target_fg": "1.010",
            "batch_name": "Test",
            "batch_notes": "",
            "start_date": "2023-01-01",
            "alert_telegram_token": ""
        }
        return configs.get(key)
    mock_get_config.side_effect = get_config_side_effect

    # Mock InfluxDB response
    mock_record_sg = MagicMock()
    mock_record_sg.get_field.return_value = "sg"
    mock_record_sg.get_value.return_value = 1.045
    mock_record_sg.get_time.return_value = datetime.datetime(2023, 1, 1, tzinfo=datetime.timezone.utc)

    mock_record_temp = MagicMock()
    mock_record_temp.get_field.return_value = "temp"
    mock_record_temp.get_value.return_value = 22.0
    mock_record_temp.get_time.return_value = datetime.datetime(2023, 1, 1, tzinfo=datetime.timezone.utc)

    mock_record_rssi = MagicMock()
    mock_record_rssi.get_field.return_value = "rssi"
    mock_record_rssi.get_value.return_value = -65
    mock_record_rssi.get_time.return_value = datetime.datetime(2023, 1, 1, tzinfo=datetime.timezone.utc)

    mock_table = MagicMock()
    mock_table.records = [mock_record_sg, mock_record_temp, mock_record_rssi]
    mock_query.return_value = [mock_table]

    # We must patch the import inside get_status_dict
    with patch.dict("sys.modules", {"services.tilt_monitor": MagicMock(get_tilt_state=mock_get_tilt_state)}):
        status = get_status_dict()

    assert status["test_mode"] is True
    assert status["sg"] == 1.045
    assert status["temp"] == 22.0
    assert status["rssi"] == -65
    assert status["status"] == "Online"


@patch("app.services.status.get_config")
@patch("app.services.status.query_api.query")
def test_get_status_dict_live_mode_with_tilt_state(mock_query, mock_get_config):
    def get_config_side_effect(key):
        configs = {
            "test_mode": "false",
            "offset": "0.002",
            "og": "1.050",
            "target_fg": "1.010",
            "batch_name": "Test",
            "batch_notes": "",
            "start_date": "2023-01-01",
            "alert_telegram_token": ""
        }
        return configs.get(key)
    mock_get_config.side_effect = get_config_side_effect

    mock_tilt_state = {
        "rssi": -70,
        "last_seen": datetime.datetime(2023, 1, 1, tzinfo=datetime.timezone.utc),
        "sg": 1.040,
        "temp": 68.0  # Fahrenheit
    }

    mock_get_tilt_state = MagicMock(return_value=mock_tilt_state)
    mock_tilt_monitor = MagicMock()
    mock_tilt_monitor.get_tilt_state = mock_get_tilt_state

    with patch.dict("sys.modules", {"services.tilt_monitor": mock_tilt_monitor}):
        status = get_status_dict()

    assert status["test_mode"] is False
    assert status["sg"] == 1.042  # 1.040 + 0.002
    assert status["temp"] == 20.0 # (68 - 32) * 5/9
    assert status["temp_unit"] == "C"
    assert status["rssi"] == -70


@patch("app.services.status.get_config")
@patch("app.services.status.query_api.query")
def test_get_status_dict_live_mode_fallback_influx(mock_query, mock_get_config):
    def get_config_side_effect(key):
        configs = {
            "test_mode": "false",
            "offset": "0.0",
            "og": "1.050",
            "target_fg": "1.010",
            "batch_name": "Test",
            "batch_notes": "",
            "start_date": "2023-01-01",
            "alert_telegram_token": ""
        }
        return configs.get(key)
    mock_get_config.side_effect = get_config_side_effect

    # Mock empty tilt state to force Influx fallback
    mock_tilt_state = {}
    mock_get_tilt_state = MagicMock(return_value=mock_tilt_state)
    mock_tilt_monitor = MagicMock()
    mock_tilt_monitor.get_tilt_state = mock_get_tilt_state

    # Mock InfluxDB response
    mock_record_sg = MagicMock()
    mock_record_sg.get_field.return_value = "sg"
    mock_record_sg.get_value.return_value = 1.048
    mock_record_sg.get_time.return_value = datetime.datetime(2023, 1, 1, tzinfo=datetime.timezone.utc)
    mock_record_temp = MagicMock()
    mock_record_temp.get_field.return_value = "temp"
    mock_record_temp.get_value.return_value = 21.5
    mock_record_temp.get_time.return_value = datetime.datetime(2023, 1, 1, tzinfo=datetime.timezone.utc)

    mock_table = MagicMock()
    mock_table.records = [mock_record_sg, mock_record_temp]
    mock_query.return_value = [mock_table]

    with patch.dict("sys.modules", {"services.tilt_monitor": mock_tilt_monitor}):
        status = get_status_dict()

    assert status["test_mode"] is False
    assert status["sg"] == 1.048
    assert status["temp"] == 21.5


@patch("app.services.status.get_config")
@patch("app.services.status.query_api.query")
def test_get_status_dict_exception_handling(mock_query, mock_get_config):
    def get_config_side_effect(key):
        configs = {
            "test_mode": "false",
            "offset": "0.0",
            "og": "1.050",
            "target_fg": "1.010",
            "batch_name": "Test",
            "batch_notes": "",
            "start_date": "2023-01-01",
            "alert_telegram_token": ""
        }
        return configs.get(key)
    mock_get_config.side_effect = get_config_side_effect
    mock_query.side_effect = ConnectionError("Influx DB Down")

    mock_get_tilt_state = MagicMock(return_value={})
    mock_tilt_monitor = MagicMock()
    mock_tilt_monitor.get_tilt_state = mock_get_tilt_state

    with patch.dict("sys.modules", {"services.tilt_monitor": mock_tilt_monitor}):
        status = get_status_dict()

    assert status["status"] == "Online"
    assert status["sg"] is None
    assert status["temp"] is None


@patch("shutil.disk_usage")
def test_get_disk_usage(mock_disk_usage):
    # Mocking standard successful return
    MockUsage = type('MockUsage', (), {'total': 10000000000, 'used': 6000000000, 'free': 4000000000})
    mock_disk_usage.return_value = MockUsage()

    result = get_disk_usage("/")
    assert result["total_bytes"] == 10000000000
    assert result["used_percent"] == 60.0
    assert result["warning"] is False

    # Test warning threshold
    MockUsageWarning = type('MockUsage', (), {'total': 10000000000, 'used': 9000000000, 'free': 1000000000})
    mock_disk_usage.return_value = MockUsageWarning()
    result = get_disk_usage("/")
    assert result["warning"] is True

    # Test exception
    mock_disk_usage.side_effect = OSError("Disk read error")
    result = get_disk_usage("/")
    assert "error" in result


def test_get_sd_io_stats_success():
    mock_stat_data = "100 0 200 300 400 0 500 600 0 0 0"
    with patch("builtins.open", mock_open(read_data=mock_stat_data)):
        stats = get_sd_io_stats()
        assert stats["reads_completed"] == 100
        assert stats["sectors_read"] == 200
        assert stats["read_ms"] == 300
        assert stats["writes_completed"] == 400
        assert stats["sectors_written"] == 500
        assert stats["write_ms"] == 600

def test_get_sd_io_stats_file_not_found():
    with patch("builtins.open", side_effect=FileNotFoundError):
        stats = get_sd_io_stats()
        assert "error" in stats
        assert stats["error"] == "SD card stats not available (not running on Pi)"

def test_get_sd_io_stats_os_error():
    with patch("builtins.open", side_effect=OSError):
        stats = get_sd_io_stats()
        assert "error" in stats
        assert stats["error"] == "SD card stats not available (not running on Pi)"

def test_get_sd_io_stats_index_error():
    mock_data = "100 0" # Not enough elements to unpack
    with patch("builtins.open", mock_open(read_data=mock_data)):
        stats = get_sd_io_stats()
        assert "error" in stats
        assert stats["error"] == "SD card stats not available (not running on Pi)"


@patch("app.services.status.get_config")
@patch("app.services.status.query_api.query")
def test_get_daily_telemetry_success(mock_query, mock_get_config):
    def get_config_side_effect(key):
        configs = {"batch_name": "Test", "og": "1.050"}
        return configs.get(key)
    mock_get_config.side_effect = get_config_side_effect

    # Mock predictions
    mock_prediction = MagicMock()
    mock_prediction.get_predicted_fg = MagicMock(return_value={"fg": 1.012, "date": "2023-01-10"})

    # Mock influx queries
    # Three queries are made: now, 24h, temp_range
    mock_record_now = MagicMock(); mock_record_now.get_field.return_value = "sg"; mock_record_now.get_value.return_value = 1.020
    mock_record_24h = MagicMock(); mock_record_24h.get_field.return_value = "sg"; mock_record_24h.get_value.return_value = 1.030

    mock_record_temp1 = MagicMock(); mock_record_temp1.get_field.return_value = "temp"; mock_record_temp1.get_value.return_value = 20.0
    mock_record_temp2 = MagicMock(); mock_record_temp2.get_field.return_value = "temp"; mock_record_temp2.get_value.return_value = 20.5

    mock_table_now = MagicMock(); mock_table_now.records = [mock_record_now]
    mock_table_24h = MagicMock(); mock_table_24h.records = [mock_record_24h]
    mock_table_temp = MagicMock(); mock_table_temp.records = [mock_record_temp1, mock_record_temp2]

    mock_query.side_effect = [[mock_table_now], [mock_table_24h], [mock_table_temp]]

    with patch.dict("sys.modules", {"ml.prediction": mock_prediction}):
        telemetry = get_daily_telemetry()

    assert "error" not in telemetry
    assert telemetry["sg_now"] == 1.020
    assert telemetry["sg_24h_ago"] == 1.030
    assert telemetry["sg_diff"] == 0.010
    assert telemetry["abv_gain"] == round(0.010 * 131.25, 2)
    assert telemetry["total_abv"] == round((1.050 - 1.020) * 131.25, 2)
    assert telemetry["temp_range"] == "20.0 - 20.5°C"
    assert telemetry["is_stable"] is True
    assert telemetry["predicted_fg"] == 1.012


@patch("app.services.status.get_config")
@patch("app.services.status.query_api.query")
def test_get_daily_telemetry_insufficient_data(mock_query, mock_get_config):
    mock_get_config.return_value = "1.050"

    # Return empty tables
    mock_query.side_effect = [[], [], []]

    mock_prediction = MagicMock()
    mock_prediction.get_predicted_fg = MagicMock(return_value={})

    with patch.dict("sys.modules", {"ml.prediction": mock_prediction}):
        telemetry = get_daily_telemetry()

    assert "error" in telemetry
    assert telemetry["error"] == "Insufficient data for 24h diff"


@patch("app.services.status.get_disk_usage")
@patch("app.services.status.get_pi_temp")
@patch("app.services.status.get_sd_io_stats")
def test_get_maintenance_summary(mock_sd_io, mock_pi_temp, mock_disk):
    mock_disk.return_value = {"total_bytes": 100}
    mock_pi_temp.return_value = 45.0
    mock_sd_io.return_value = {"reads_completed": 10}

    summary = get_maintenance_summary()
    assert summary["disk"]["total_bytes"] == 100
    assert summary["data_volume"]["total_bytes"] == 100
    assert summary["pi_temp"] == 45.0
    assert summary["sd_io"]["reads_completed"] == 10

    # Assert get_disk_usage called with right args
    mock_disk.assert_any_call("/")
    mock_disk.assert_any_call("/data")
