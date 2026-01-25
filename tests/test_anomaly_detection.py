import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta
import numpy as np

# Mocking InfluxDB Record
class MockRecord:
    def __init__(self, value, time=None):
        self.value = value
        self.time = time

    def get_value(self):
        return self.value
    
    def get_time(self):
        return self.time

class MockTable:
    def __init__(self, records):
        self.records = records

class TestAnomalyDetection(unittest.TestCase):

    def setUp(self):
        self.patcher_query = patch('app.services.anomaly.query_api')
        self.patcher_config = patch('app.services.anomaly.get_config')
        self.patcher_telegram = patch('app.services.anomaly.send_telegram_message')
        self.patcher_broadcast = patch('app.services.anomaly.broadcast_alert')

        self.mock_query = self.patcher_query.start()
        self.mock_config = self.patcher_config.start()
        self.mock_telegram = self.patcher_telegram.start()
        self.mock_broadcast = self.patcher_broadcast.start()

        # Default config mock
        self.mock_config.side_effect = lambda k: {
            "batch_name": "Test Batch",
            "yeast_min_temp": 65,
            "yeast_max_temp": 75
        }.get(k)

    def tearDown(self):
        self.patcher_query.stop()
        self.patcher_config.stop()
        self.patcher_telegram.stop()
        self.patcher_broadcast.stop()

    def test_calculate_anomaly_score_normal(self):
        from app.services.anomaly import calculate_anomaly_score
        
        # Simulate 48h of stable readings (48 data points)
        temp_readings = [70.0] * 48
        sg_readings = [1.050 - (i * 0.0005) for i in range(48)] # Steady drop
        
        self.mock_query.query.side_effect = [
            [MockTable([MockRecord(v) for v in temp_readings])],
            [MockTable([MockRecord(v) for v in sg_readings])]
        ]
        
        result = calculate_anomaly_score()
        self.assertEqual(result["status"], "normal")
        self.assertLess(result["anomaly_score"], 1.0)
        self.mock_telegram.assert_not_called()

    def test_calculate_anomaly_score_temp_spike(self):
        from app.services.anomaly import calculate_anomaly_score
        
        # Stable readings (with a bit of noise) followed by a spike
        temp_readings = [70.0, 70.1, 69.9, 70.0] * 11 + [70.0, 70.1, 69.9] + [85.0]
        sg_readings = [1.050 - (i * 0.0005) for i in range(48)]
        
        self.mock_query.query.side_effect = [
            [MockTable([MockRecord(v) for v in temp_readings])],
            [MockTable([MockRecord(v) for v in sg_readings])]
        ]
        
        result = calculate_anomaly_score()
        self.assertEqual(result["status"], "anomaly")
        self.assertGreaterEqual(result["anomaly_score"], 1.0)
        self.mock_telegram.assert_called_once()
        self.mock_broadcast.assert_called_with("statistical_anomaly", unittest.mock.ANY, "warning", unittest.mock.ANY)

    def test_check_stalled_fermentation(self):
        from app.services.anomaly import check_stalled_fermentation
        
        now = datetime.now(timezone.utc)
        # Simulate flat SG over 24h
        readings = [
            MockRecord(1.040, now - timedelta(hours=i)) 
            for i in range(24, -1, -1)
        ]
        
        self.mock_query.query.return_value = [MockTable(readings)]
        
        result = check_stalled_fermentation("Stall Test")
        self.assertEqual(result["status"], "stalled")
        self.mock_telegram.assert_called_once()

    def test_check_temperature_deviation(self):
        from app.services.anomaly import check_temperature_deviation
        
        # Simulate high temp (80F when target is 70F)
        self.mock_query.query.return_value = [MockTable([MockRecord(80.0)])]
        
        result = check_temperature_deviation(batch_name="Temp Test")
        self.assertEqual(result["status"], "deviation")
        self.assertTrue("🔥" in self.mock_telegram.call_args[0][0])

    def test_check_runaway_fermentation(self):
        from app.services.anomaly import check_runaway_fermentation
        
        # First reading 1.050, last reading 1.025 (drop of 0.025 in 12h)
        self.mock_query.query.side_effect = [
            [MockTable([MockRecord(1.050)])],
            [MockTable([MockRecord(1.025)])]
        ]
        
        result = check_runaway_fermentation("Runaway Test")
        self.assertEqual(result["status"], "runaway")
        self.mock_telegram.assert_called_once()

    def test_check_signal_loss(self):
        from app.services.anomaly import check_signal_loss
        
        # Last reading was 2 hours ago
        last_time = datetime.now(timezone.utc) - timedelta(minutes=120)
        self.mock_query.query.return_value = [MockTable([MockRecord(1.030, last_time)])]
        
        # Mock troubleshoot_tiltpi to avoid network calls
        with patch('app.services.anomaly.troubleshoot_tiltpi') as mock_trouble:
            mock_trouble.return_value = {"status": "checked"}
            result = check_signal_loss("Signal Test")
            self.assertEqual(result["status"], "signal_loss")
            self.mock_telegram.assert_called_once()

if __name__ == '__main__':
    unittest.main()
