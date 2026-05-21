import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime
import sys
import os

# Ensure app is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../app')))

# Save original modules
_original_modules = {}
_keys_to_remove = []
for key in ["influxdb_client", "influxdb_client.client", "influxdb_client.client.write_api", "redis", "extensions", "core.cache"]:
    if key in sys.modules:
        _original_modules[key] = sys.modules[key]
    else:
        _keys_to_remove.append(key)

# Mock dependencies BEFORE ANY IMPORTS
mock_influx = MagicMock()
sys.modules["influxdb_client"] = mock_influx
sys.modules["influxdb_client.client"] = MagicMock()
sys.modules["influxdb_client.client.write_api"] = MagicMock()
sys.modules["redis"] = MagicMock()
sys.modules["extensions"] = MagicMock()

mock_cache_obj = MagicMock()
mock_core_cache = MagicMock()
mock_core_cache.cache = mock_cache_obj
sys.modules["core.cache"] = mock_core_cache

from app.services import notifications
# Force mock
notifications.cache = mock_cache_obj

# Restore original modules to prevent side-effects on other test files
for key, val in _original_modules.items():
    sys.modules[key] = val
for key in _keys_to_remove:
    if key in sys.modules:
        del sys.modules[key]

class TestNotifications(unittest.TestCase):
    def setUp(self):
        notifications.logger = MagicMock()
        self.cache = mock_cache_obj
        self.cache.reset_mock()
        self.cache.get.side_effect = None
        self.cache.get.return_value = None
        self.cache.set.side_effect = None
        self.cache.set.return_value = None
        
        self.sys_modules_patcher = patch.dict(sys.modules, {
            "core.cache": mock_core_cache,
            "influxdb_client": mock_influx,
            "redis": MagicMock(),
            "extensions": MagicMock()
        })
        self.sys_modules_patcher.start()

    def tearDown(self):
        self.sys_modules_patcher.stop()

    @patch("app.services.notifications.get_config")
    def test_is_quiet_hours_standard(self, mock_get_config):
        mock_get_config.side_effect = lambda k: "08:00" if k == "alert_start_time" else "22:00"
        with patch("app.services.notifications.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 5, 11, 10, 0)
            self.assertFalse(notifications.is_quiet_hours())
        with patch("app.services.notifications.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 5, 11, 23, 0)
            self.assertTrue(notifications.is_quiet_hours())

    @patch("app.services.notifications.get_config")
    def test_is_quiet_hours_overnight(self, mock_get_config):
        # Quiet hours span midnight (active 22:00 to 06:00, quiet 06:00 to 22:00)
        mock_get_config.side_effect = lambda k: "22:00" if k == "alert_start_time" else "06:00"
        with patch("app.services.notifications.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 5, 11, 12, 0)
            self.assertTrue(notifications.is_quiet_hours())
        with patch("app.services.notifications.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 5, 11, 23, 0)
            self.assertFalse(notifications.is_quiet_hours())

    @patch("app.services.notifications.requests.post")
    @patch("app.services.notifications.get_config")
    def test_send_telegram_success(self, mock_get_config, mock_post):
        mock_get_config.side_effect = lambda k: {
            "alert_telegram_token": "fake_token",
            "alert_telegram_chat": "fake_chat",
            "brew_active": "true",
            "alert_verbosity_min": "0"
        }.get(k)
        
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp
        self.cache.get.return_value = None
        
        with patch("app.services.notifications.is_quiet_hours", return_value=False):
            result = notifications.send_telegram_message("Test message")
            self.assertEqual(result.get("status"), "success")
            mock_post.assert_called_once()


    @patch("app.services.notifications.requests.post")
    @patch("app.services.notifications.get_config")
    def test_send_telegram_force(self, mock_get_config, mock_post):
        # Use a more realistic side effect
        mock_get_config.side_effect = lambda k: {
            "alert_telegram_token": "fake",
            "alert_telegram_chat": "fake",
            "alert_verbosity_min": "0"
        }.get(k)
        
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp
        self.cache.get.return_value = None
        
        with patch("app.services.notifications.is_quiet_hours", return_value=True):
            # force=True should bypass both brew_active=false and is_quiet_hours=True
            result = notifications.send_telegram_message("Force message", force=True)
            if result.get("status") != "success":
                print(f"DEBUG: force test result: {result}")
            self.assertEqual(result.get("status"), "success")
            mock_post.assert_called_once()

    @patch("app.services.notifications.get_config")
    def test_send_telegram_verbosity_limit(self, mock_get_config):
        mock_get_config.side_effect = lambda k: {
            "brew_active": "true",
            "alert_verbosity_min": "10"
        }.get(k)
        
        self.cache.get.return_value = datetime.now().timestamp() - 300
        
        with patch("app.services.notifications.is_quiet_hours", return_value=False):
            result = notifications.send_telegram_message("Spam message")
            self.assertEqual(result.get("status"), "skipped")
            self.assertEqual(result.get("reason"), "verbosity_limit")

    @patch("app.services.notifications.requests.post")
    @patch("app.services.notifications.get_config")
    def test_send_telegram_verbosity_bypass(self, mock_get_config, mock_post):
        mock_get_config.side_effect = lambda k: {
            "brew_active": "true",
            "alert_verbosity_min": "60",
            "bypass_temp_threshold": "0.5",
            "alert_telegram_token": "fake",
            "alert_telegram_chat": "fake"
        }.get(k)
        
        # Mock cache to return old timestamp for verbosity check and old value for deviation check
        def cache_get_side_effect(key):
            if "last_notified_alert" in key:
                return datetime.now().timestamp() - 300
            if "last_notified_values" in key:
                return {"temp": 20.0}
            return None
            
        self.cache.get.side_effect = cache_get_side_effect
        
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        with patch("app.services.notifications.is_quiet_hours", return_value=False):
            # Current temp 21.0 (> 0.5 deviation)
            result = notifications.send_telegram_message("Major change", current_values={"temp": 21.0})
            self.assertEqual(result.get("status"), "success")
            mock_post.assert_called_once()

if __name__ == "__main__":
    unittest.main()
