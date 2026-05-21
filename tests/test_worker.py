# Save original sys.modules keys/values to restore later
import sys
from unittest.mock import MagicMock, patch

_original_modules = {}
_keys_to_remove = []
for key in ["core.config", "app.core.config", "influxdb_client", "core.influx", "services.telegram", "services.ai", "services.tilt_monitor", "scipy", "scipy.optimize", "scipy.signal"]:
    if key in sys.modules:
        _original_modules[key] = sys.modules[key]
    else:
        _keys_to_remove.append(key)

# Create a robust mock for the config module
mock_config = MagicMock()
mock_config.get_config.return_value = "1.050"
sys.modules["core.config"] = mock_config
sys.modules["app.core.config"] = mock_config

sys.modules["influxdb_client"] = MagicMock()
sys.modules["core.influx"] = MagicMock()
sys.modules["services.telegram"] = MagicMock()
sys.modules["services.ai"] = MagicMock()
sys.modules["services.tilt_monitor"] = MagicMock()

# Ensure we don't mock the WHOLE scipy, as it breaks the tests
# But in this environment we might need to mock them if not installed.
try:
    from scipy.optimize import curve_fit
    from scipy.signal import medfilt
except ImportError:
    mock_scipy = MagicMock()
    sys.modules["scipy"] = mock_scipy
    sys.modules["scipy.optimize"] = MagicMock()
    sys.modules["scipy.signal"] = MagicMock()
    # If missing, the patches below will still work but might need more care

import unittest
from datetime import datetime, timezone, timedelta
from app.services import worker

# Restore original modules to prevent side-effects on other test files
for key, val in _original_modules.items():
    sys.modules[key] = val
for key in _keys_to_remove:
    if key in sys.modules:
        del sys.modules[key]

import numpy as np

class TestWorker(unittest.TestCase):
    def setUp(self):
        self.sys_modules_patcher = patch.dict(sys.modules, {
            "core.config": mock_config,
            "app.core.config": mock_config,
            "influxdb_client": MagicMock(),
            "core.influx": MagicMock(),
            "services.telegram": MagicMock(),
            "services.ai": MagicMock(),
            "services.tilt_monitor": MagicMock()
        })
        self.sys_modules_patcher.start()

    def tearDown(self):
        self.sys_modules_patcher.stop()

    def test_sigmoid(self):
        # Test basic sigmoid functionality
        # L=0.050, k=0.5, t0=24, C=1.010
        res = worker.sigmoid(24, 0.050, 0.5, 24, 1.010)
        self.assertAlmostEqual(res, 1.010 + 0.050/2, places=4)

    def test_predict_fg_from_curve_insufficient_data(self):
        times = [datetime.now() - timedelta(hours=i) for i in range(10)]
        readings = [1.050 - (i * 0.001) for i in range(10)]
        
        fg, date = worker.predict_fg_from_curve(times, readings)
        self.assertIsNone(fg)
        self.assertIsNone(date)

    @patch("app.services.worker.medfilt")
    @patch("app.services.worker.curve_fit")
    def test_predict_fg_from_curve_success(self, mock_curve_fit, mock_medfilt):
        # Mock medfilt to return input
        mock_medfilt.side_effect = lambda x, kernel_size: x
        
        # Create 60 points of fake data
        start_time = datetime(2026, 5, 11, 0, 0, tzinfo=timezone.utc)
        times = [start_time + timedelta(hours=i) for i in range(60)]
        readings = [1.050 - (i * 0.0005) for i in range(60)]
        
        # Mock popt: L, k, t0, C
        mock_curve_fit.return_value = ([0.040, 0.5, 30, 1.010], None)
        
        fg, date = worker.predict_fg_from_curve(times, readings)
        
        self.assertEqual(fg, 1.010)
        self.assertIsInstance(date, datetime)
        # Verify it's after the start time
        self.assertTrue(date > start_time)

    @patch("app.services.worker.get_config")
    @patch("app.services.worker.write_api")
    @patch("app.services.worker.Point")
    def test_process_data_once_test_mode(self, mock_point_cls, mock_write, mock_get_config):
        mock_get_config.side_effect = lambda k: {
            "test_mode": "true",
            "test_sg_start": "1.060",
            "test_temp_base": "20.0",
            "offset": "0.0"
        }.get(k)
        
        worker.process_data_once()
        
        # Should call Point constructor with "test_readings"
        mock_point_cls.assert_called_with("test_readings")
        
        # Should call write_api.write
        mock_write.write.assert_called_once()

if __name__ == "__main__":
    unittest.main()
