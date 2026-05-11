import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime
import sys

# Mock dependencies before import
sys.modules["extensions"] = MagicMock()
sys.modules["core.influx"] = MagicMock()
sys.modules["influxdb_client"] = MagicMock()

from app.services import notifications

class TestNotifications(unittest.TestCase):
    def setUp(self):
        notifications.logger = MagicMock()

    @patch("app.services.notifications.get_config")
    def test_is_quiet_hours_standard(self, mock_get_config):
        # 08:00 - 22:00 active, 22:00 - 08:00 quiet
        mock_get_config.side_effect = lambda k: "08:00" if k == "alert_start_time" else "22:00"
        
        # Test 10:00 AM (Active)
        with patch("app.services.notifications.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 5, 11, 10, 0)
            self.assertFalse(notifications.is_quiet_hours())
            
        # Test 11:00 PM (Quiet)
        with patch("app.services.notifications.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 5, 11, 23, 0)
            self.assertTrue(notifications.is_quiet_hours())

    @patch("app.services.notifications.get_config")
    def test_is_quiet_hours_overnight(self, mock_get_config):
        # 22:00 - 08:00 active, 08:00 - 22:00 quiet
        mock_get_config.side_effect = lambda k: "22:00" if k == "alert_start_time" else "08:00"
        
        # Test 02:00 AM (Active)
        with patch("app.services.notifications.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 5, 11, 2, 0)
            self.assertFalse(notifications.is_quiet_hours())
            
        # Test 10:00 AM (Quiet)
        with patch("app.services.notifications.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 5, 11, 10, 0)
            self.assertTrue(notifications.is_quiet_hours())

    @patch("app.services.notifications.requests.post")
    @patch("app.services.notifications.get_config")
    def test_send_telegram_success(self, mock_get_config, mock_post):
        mock_get_config.side_effect = lambda k: {
            "alert_telegram_token": "fake_token",
            "alert_telegram_chat": "fake_chat",
            "brew_active": "true"
        }.get(k)
        
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp
        
        # Mock quiet hours to be false
        with patch("app.services.notifications.is_quiet_hours", return_value=False):
            result = notifications.send_telegram_message("Test message")
            self.assertEqual(result["status"], "success")
            mock_post.assert_called_once()

    @patch("app.services.notifications.get_config")
    def test_send_telegram_skipped_inactive(self, mock_get_config):
        mock_get_config.side_effect = lambda k: "false" if k == "brew_active" else None
        
        result = notifications.send_telegram_message("Test message")
        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["reason"], "brew_inactive")

    @patch("app.services.notifications.is_quiet_hours", return_value=True)
    @patch("app.services.notifications.get_config")
    def test_send_telegram_skipped_quiet_hours(self, mock_get_config, mock_quiet):
        mock_get_config.side_effect = lambda k: "true" if k == "brew_active" else "fake"
        
        result = notifications.send_telegram_message("Test message")
        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["reason"], "quiet_hours")

    @patch("app.services.notifications.is_quiet_hours", return_value=True)
    @patch("app.services.notifications.requests.post")
    @patch("app.services.notifications.get_config")
    def test_send_telegram_force(self, mock_get_config, mock_post, mock_quiet):
        mock_get_config.side_effect = lambda k: "fake"
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp
        
        # Should NOT skip even if quiet hours is True because force=True
        result = notifications.send_telegram_message("Force message", force=True)
        self.assertEqual(result["status"], "success")
        mock_post.assert_called_once()

if __name__ == "__main__":
    unittest.main()
