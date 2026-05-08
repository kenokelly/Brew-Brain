import unittest
from unittest.mock import patch
import sys

# Safely mock missing modules only if they aren't installed to avoid test pollution
def _mock_missing_imports():
    from unittest.mock import MagicMock
    mock = MagicMock()
    for mod in ['influxdb_client', 'influxdb_client.client', 'influxdb_client.client.write_api', 'requests']:
        try:
            __import__(mod)
        except ImportError:
            sys.modules[mod] = mock

_mock_missing_imports()

from app.services.telemetry import send_daily_board_report, std_status, format_diff


class TestTelemetry(unittest.TestCase):

    @patch('app.services.telemetry.send_telegram_message')
    @patch('app.services.telemetry.get_daily_telemetry')
    def test_send_daily_board_report_success(self, mock_get_daily_telemetry, mock_send_telegram_message):
        mock_get_daily_telemetry.return_value = {
            'batch_name': 'Test Batch',
            'sg_now': 1.020,
            'sg_diff': 0.005,
            'abv_gain': 0.6,
            'total_abv': 5.2,
            'temp_range': '20.0-21.0C',
            'is_stable': True,
            'predicted_fg': 1.010,
            'predicted_date': '2023-10-31'
        }

        result = send_daily_board_report()

        self.assertEqual(result, {"status": "success", "batch": "Test Batch"})
        mock_send_telegram_message.assert_called_once()
        args, kwargs = mock_send_telegram_message.call_args
        self.assertTrue(kwargs.get('force'))
        self.assertIn("Test Batch", args[0])
        self.assertIn("1.020", args[0])
        self.assertIn("5.2%", args[0])

    @patch('app.services.telemetry.get_daily_telemetry')
    def test_send_daily_board_report_error_in_telemetry(self, mock_get_daily_telemetry):
        mock_get_daily_telemetry.return_value = {
            "error": "No data available"
        }

        result = send_daily_board_report()

        self.assertEqual(result, {"status": "skipped", "reason": "No data available"})

    @patch('app.services.telemetry.get_daily_telemetry')
    def test_send_daily_board_report_exception(self, mock_get_daily_telemetry):
        mock_get_daily_telemetry.side_effect = Exception("API failure")

        result = send_daily_board_report()

        self.assertEqual(result['status'], "error")
        self.assertIn("API failure", result['message'])

    def test_std_status(self):
        self.assertEqual(std_status(0.009), "🚀 Active Fermentation")
        self.assertEqual(std_status(0.005), "🐢 Slowing Down")
        self.assertEqual(std_status(0.000), "🏁 Near Completion")
        self.assertEqual(std_status(-0.005), "⏸️ Idle / Equilibrium")
        self.assertEqual(std_status(0.0015), "⏸️ Idle / Equilibrium") # between 0.001 and 0.002

    def test_format_diff(self):
        self.assertEqual(format_diff(0.005), "-0.005")
        self.assertEqual(format_diff(-0.003), "+0.003")
        self.assertEqual(format_diff(0), "0.000")

if __name__ == '__main__':
    unittest.main()
