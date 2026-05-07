import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Mock dependencies that are not in the environment to allow the module to be imported
# We only mock what is strictly necessary for the imports to work
missing_deps = [
    'influxdb_client',
    'influxdb_client.client.write_api',
    'requests',
    'flask',
    'flask_cors',
    'flask_socketio',
    'eventlet',
    'apscheduler',
    'apscheduler.schedulers.background',
    'recipe_scrapers',
    'github',
    'google_search_results',
    'joblib',
    'pyarrow',
    'pyarrow.parquet',
    'redis'
]

for dep in missing_deps:
    sys.modules[dep] = MagicMock()

# Add app to path to allow the 'services' import to work as expected by the source code
sys.path.insert(0, os.path.join(os.getcwd(), 'app'))

from services.telemetry import send_daily_board_report

class TestTelemetry(unittest.TestCase):

    @patch('services.telemetry.get_daily_telemetry')
    @patch('services.telemetry.send_telegram_message')
    def test_send_daily_board_report_success(self, mock_send_telegram, mock_get_telemetry):
        # Setup mock data
        mock_get_telemetry.return_value = {
            "batch_name": "Test IPA",
            "sg_now": 1.012,
            "sg_24h_ago": 1.020,
            "sg_diff": 0.008,
            "abv_gain": 1.05,
            "total_abv": 5.5,
            "temp_range": "19.5 - 20.2°C",
            "is_stable": True,
            "predicted_fg": 1.010,
            "predicted_date": "2025-05-10"
        }
        mock_send_telegram.return_value = {"status": "success"}

        # Execute
        result = send_daily_board_report()

        # Verify
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["batch"], "Test IPA")
        mock_send_telegram.assert_called_once()
        args, kwargs = mock_send_telegram.call_args
        self.assertIn("Test IPA", args[0])
        self.assertIn("1.012", args[0])
        self.assertTrue(kwargs.get("force"))

    @patch('services.telemetry.get_daily_telemetry')
    @patch('services.telemetry.send_telegram_message')
    def test_send_daily_board_report_skipped(self, mock_send_telegram, mock_get_telemetry):
        # Setup mock data for skipped path
        mock_get_telemetry.return_value = {"error": "Insufficient data for 24h diff"}

        # Execute
        result = send_daily_board_report()

        # Verify
        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["reason"], "Insufficient data for 24h diff")
        mock_send_telegram.assert_not_called()

    @patch('services.telemetry.get_daily_telemetry')
    def test_send_daily_board_report_exception(self, mock_get_telemetry):
        # Setup mock to raise exception
        mock_get_telemetry.side_effect = Exception("InfluxDB Connection Failed")

        # Execute
        result = send_daily_board_report()

        # Verify
        self.assertEqual(result["status"], "error")
        self.assertIn("InfluxDB Connection Failed", result["message"])

if __name__ == '__main__':
    unittest.main()
