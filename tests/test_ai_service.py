import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta
import sys
import os

# Add 'app' directory to sys.path
if os.path.join(os.getcwd(), 'app') not in sys.path:
    sys.path.append(os.path.join(os.getcwd(), 'app'))

from app.services.ai import analyze_yeast_history

# Mock cache object
mock_cache_data = {}
class MockCache:
    def get(self, key):
        return mock_cache_data.get(key)
    def set(self, key, value, ttl=None):
        mock_cache_data[key] = value

mock_cache_obj = MockCache()

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
        self.cache_patcher = patch('app.services.ai.cache', mock_cache_obj)
        self.cache_patcher.start()

    def tearDown(self):
        self.cache_patcher.stop()

    @patch('app.services.ai.query_api')
    def test_analyze_yeast_history_caching(self, mock_query_api):
        yeast_name = "US-05"
        now = datetime.now(timezone.utc)

        # Create enough data for 1 historic batch (> 20 readings, last reading > 24h ago)
        start = now - timedelta(hours=72)
        readings = []
        for i in range(30):
            t = start + timedelta(hours=i)
            readings.append(MockRecord(t, 1.050 - (i * 0.001)))

        mock_query_api.query.return_value = [MockTable(readings)]

        # First call - should hit "InfluxDB"
        result1 = analyze_yeast_history(yeast_name)
        self.assertIsNotNone(result1)
        self.assertEqual(mock_query_api.query.call_count, 2)

        # Second call - should hit cache
        result2 = analyze_yeast_history(yeast_name)
        self.assertEqual(result1, result2)
        self.assertEqual(mock_query_api.query.call_count, 2)

        # Verify cache content
        cache_key = f"yeast_history_{yeast_name}"
        self.assertIn(cache_key, mock_cache_data)
        self.assertEqual(mock_cache_data[cache_key], result1)

    @patch('app.services.ai.query_api')
    def test_analyze_yeast_history_no_data(self, mock_query_api):
        mock_query_api.query.return_value = []
        result = analyze_yeast_history("UnknownYeast")
        self.assertIsNone(result)
        self.assertEqual(len(mock_cache_data), 0)

if __name__ == '__main__':
    unittest.main()
