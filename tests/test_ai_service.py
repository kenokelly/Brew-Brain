import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta
import sys
import os

# Mock dependencies
mock_np = MagicMock()
mock_np.mean.side_effect = lambda x: sum(x) / len(x) if x else 0
sys.modules["numpy"] = mock_np
sys.modules["influxdb_client"] = MagicMock()
sys.modules["influxdb_client.client.write_api"] = MagicMock()

# Add 'app' directory to sys.path
sys.path.append(os.path.join(os.getcwd(), 'app'))

# Mock core.influx
mock_influx = MagicMock()
sys.modules["core.influx"] = mock_influx
mock_influx.INFLUX_BUCKET = "test_bucket"

# Mock core.cache.cache
mock_cache_data = {}
class MockCache:
    def get(self, key):
        return mock_cache_data.get(key)
    def set(self, key, value, ttl=None):
        mock_cache_data[key] = value

mock_cache_obj = MockCache()
mock_cache_module = MagicMock()
mock_cache_module.cache = mock_cache_obj
sys.modules["core.cache"] = mock_cache_module

from services.ai import analyze_yeast_history

class MockRecord:
    def __init__(self, t, v):
        self.t = t
        self.v = v
    def get_time(self):
        return self.t
    def get_value(self):
        return self.v

class MockTable:
    def __init__(self, records):
        self.records = records

class TestAIService(unittest.TestCase):
    def setUp(self):
        mock_cache_data.clear()

    @patch('services.ai.query_api')
    def test_analyze_yeast_history_caching(self, mock_query_api):
        yeast_name = "US-05"
        now = datetime.now(timezone.utc)

        # Create enough data for 1 historic batch (> 20 readings, last reading > 24h ago)
        # Batch: 48h ago to 25h ago
        start = now - timedelta(hours=48)
        readings = []
        for i in range(25): # 25 points > 20
            t = start + timedelta(hours=i)
            # Duration must be > 1.0 days for it to be counted in analysis
            readings.append(MockRecord(t, 1.050 - (i * 0.001)))

        # readings[-1].t = 48 - 24 = 24h ago.
        # Actually it's start + 24*1h = (now - 48h) + 24h = now - 24h.
        # last_point_time = readings[-1].get_time() = now - 24h
        # (now - last_point_time).total_seconds() > (24 * 3600) is FALSE if it's exactly 24h.

        # Let's make it older.
        start = now - timedelta(hours=72)
        readings = []
        for i in range(30):
            t = start + timedelta(hours=i)
            readings.append(MockRecord(t, 1.050 - (i * 0.001)))

        # last point is at 72 - 29 = 43 hours ago. > 24h.
        # duration is 29 hours > 24 hours (1 day).

        mock_query_api.query.return_value = [MockTable(readings)]

        # First call - should hit "InfluxDB"
        result1 = analyze_yeast_history(yeast_name)
        self.assertIsNotNone(result1)
        self.assertEqual(mock_query_api.query.call_count, 1)

        # Second call - should hit cache
        result2 = analyze_yeast_history(yeast_name)
        self.assertEqual(result1, result2)
        self.assertEqual(mock_query_api.query.call_count, 1)

        # Verify cache content
        cache_key = f"yeast_history_{yeast_name}"
        self.assertIn(cache_key, mock_cache_data)
        self.assertEqual(mock_cache_data[cache_key], result1)

    @patch('services.ai.query_api')
    def test_analyze_yeast_history_no_data(self, mock_query_api):
        mock_query_api.query.return_value = []
        result = analyze_yeast_history("UnknownYeast")
        self.assertIsNone(result)
        self.assertEqual(len(mock_cache_data), 0)

if __name__ == '__main__':
    unittest.main()
