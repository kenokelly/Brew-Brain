import unittest
from unittest.mock import MagicMock, patch, mock_open
from datetime import datetime, timezone, timedelta
import numpy as np
import pandas as pd


class TestDataPipeline(unittest.TestCase):

    def setUp(self):
        self.patcher_query = patch('app.ml.features.query_api')
        self.patcher_config = patch('app.services.batch_exporter.get_config')
        
        self.mock_query = self.patcher_query.start()
        self.mock_config = self.patcher_config.start()
        
        # Default config
        self.mock_config.side_effect = lambda k: {
            "bf_user": "test_user",
            "bf_key": "test_key"
        }.get(k)

    def tearDown(self):
        self.patcher_query.stop()
        self.patcher_config.stop()

    def test_calculate_sg_velocity(self):
        from app.ml.features import calculate_sg_velocity
        
        # Simulate 7 days of fermentation, 1.050 -> 1.010
        sg_readings = [1.050, 1.045, 1.040, 1.035, 1.030, 1.020, 1.015, 1.010]
        timestamps = [
            datetime.now(timezone.utc) - timedelta(days=7-i)
            for i in range(8)
        ]
        
        velocity = calculate_sg_velocity(sg_readings, timestamps)
        
        # Expected: (1.050 - 1.010) * 1000 / 7 days ≈ 5.7 points/day
        self.assertGreater(velocity, 5.0)
        self.assertLess(velocity, 6.5)

    def test_calculate_temp_variance(self):
        from app.ml.features import calculate_temp_variance
        
        # Stable temps
        stable_temps = [20.0, 20.1, 19.9, 20.0, 20.1]
        variance_stable = calculate_temp_variance(stable_temps)
        self.assertLess(variance_stable, 0.2)
        
        # Unstable temps
        unstable_temps = [18.0, 22.0, 19.0, 23.0, 17.0]
        variance_unstable = calculate_temp_variance(unstable_temps)
        self.assertGreater(variance_unstable, 1.0)

    def test_calculate_time_in_phase(self):
        from app.ml.features import calculate_time_in_phase
        
        start = datetime.now(timezone.utc) - timedelta(days=7)
        end = datetime.now(timezone.utc)
        
        days = calculate_time_in_phase(start, end)
        self.assertAlmostEqual(days, 7.0, delta=0.1)

    def test_extract_features_from_batch(self):
        from app.ml.features import extract_features_from_batch
        
        # Mock InfluxDB query response
        class MockRecord:
            def __init__(self, value, time):
                self._value = value
                self._time = time
            
            def get_value(self):
                return self._value
            
            def get_time(self):
                return self._time
        
        class MockTable:
            def __init__(self, records):
                self.records = records
        
        # Create mock data with ascending timestamps
        now = datetime.now(timezone.utc)
        temp_records = [MockRecord(20.0, now + timedelta(hours=i)) for i in range(24)]
        sg_records = [MockRecord(1.050 - i*0.001, now + timedelta(hours=i)) for i in range(24)]
        
        # Mock both queries (temp and sg)
        self.mock_query.query.side_effect = [
            [MockTable(temp_records)],
            [MockTable(sg_records)]
        ]
        
        start_time = now - timedelta(days=7)
        end_time = now
        
        features = extract_features_from_batch(
            batch_name="Test Batch",
            start_time=start_time,
            end_time=end_time,
            og=1.050,
            fg=1.010,
            yeast="US-05",
            style="IPA"
        )
        
        self.assertEqual(features["batch_name"], "Test Batch")
        self.assertEqual(features["og"], 1.050)
        self.assertEqual(features["fg"], 1.010)
        self.assertEqual(features["yeast"], "US-05")
        self.assertEqual(features["style"], "IPA")
        self.assertGreater(features["data_points"], 0)
        self.assertGreater(features["sg_velocity"], 0)

    @patch('app.services.batch_exporter.requests.get')
    def test_get_completed_batches(self, mock_get):
        from app.services.batch_exporter import get_completed_batches
        
        # Mock Brewfather API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "_id": "batch1",
                "name": "Test IPA",
                "status": "Completed",
                "brewDate": 1640000000000
            }
        ]
        mock_get.return_value = mock_response
        
        batches = get_completed_batches()
        
        self.assertEqual(len(batches), 1)
        self.assertEqual(batches[0]["name"], "Test IPA")

    @patch('app.services.batch_exporter.os.makedirs')
    @patch('app.services.batch_exporter.pd.DataFrame.to_parquet')
    @patch('app.services.batch_exporter.os.path.getsize')
    def test_export_batch_to_parquet(self, mock_getsize, mock_to_parquet, mock_makedirs):
        from app.services.batch_exporter import export_batch_to_parquet
        
        # Mock InfluxDB query
        class MockRecord:
            def __init__(self, time, temp, sg):
                self._time = time
                self.values = {"Temp": temp, "SG": sg}
            
            def get_time(self):
                return self._time
        
        class MockTable:
            def __init__(self, records):
                self.records = records
        
        now = datetime.now(timezone.utc)
        records = [
            MockRecord(now - timedelta(hours=i), 20.0, 1.050 - i*0.001)
            for i in range(24)
        ]
        
        # Patch the query at the module level
        with patch('app.services.batch_exporter.query_api') as mock_query_api:
            mock_query_api.query.return_value = [MockTable(records)]
            mock_getsize.return_value = 1024
            
            result = export_batch_to_parquet(
                batch_id="test123",
                batch_name="Test Batch",
                start_time=now - timedelta(days=7),
                end_time=now,
                og=1.050,
                fg=1.010,
                yeast="US-05",
                style="IPA"
            )
            
            self.assertEqual(result["status"], "success")
            self.assertGreater(result["records"], 0)
            self.assertIn("filepath", result)
            mock_to_parquet.assert_called_once()


if __name__ == '__main__':
    unittest.main()
