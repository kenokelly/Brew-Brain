import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta
import sys
import os

# Save original modules
_original_modules = {}
_keys_to_remove = []
for key in ["influxdb_client", "core.influx", "core.cache", "serpapi"]:
    if key in sys.modules:
        _original_modules[key] = sys.modules[key]
    else:
        _keys_to_remove.append(key)

# Mock dependencies
sys.modules["influxdb_client"] = MagicMock()
sys.modules["core.influx"] = MagicMock()
sys.modules["core.cache"] = MagicMock()
sys.modules["serpapi"] = MagicMock()

# Setup paths
sys.path.append(os.path.join(os.getcwd(), 'app'))

from services.yeast import search_yeast_meta, YEAST_DATABASE
from services.ai import get_proactive_advice, predict_issues

# Restore original modules to prevent side-effects on other test files
for key, val in _original_modules.items():
    sys.modules[key] = val
for key in _keys_to_remove:
    if key in sys.modules:
        del sys.modules[key]

class TestPhase18AI(unittest.TestCase):
    def setUp(self):
        self.sys_modules_patcher = patch.dict(sys.modules, {
            "influxdb_client": MagicMock(),
            "core.influx": MagicMock(),
            "core.cache": MagicMock(),
            "serpapi": MagicMock()
        })
        self.sys_modules_patcher.start()

    def tearDown(self):
        self.sys_modules_patcher.stop()

    def test_yeast_fuzzy_match(self):
        """Verify local database fuzzy matching in yeast service."""
        # Exact match
        res = search_yeast_meta("US-05")
        self.assertEqual(res["name"], "SafAle US-05")
        
        # Fuzzy match (lowercase)
        res = search_yeast_meta("us-05")
        self.assertEqual(res["name"], "SafAle US-05")
        
        # Partial match
        res = search_yeast_meta("London Ale")
        self.assertEqual(res["name"], "Wyeast 1318 London Ale III")

    @patch('services.ai.requests.post')
    @patch('services.ai.get_config')
    @patch('ml.features.query_batch_data')
    @patch('ml.features.calculate_sg_velocity')
    def test_get_proactive_advice_resource_control(self, mock_vel, mock_query, mock_config, mock_post):
        """Verify keep_alive: 0 is present in Ollama calls."""
        mock_config.return_value = "llama3"
        mock_query.return_value = {"sg_readings": [1.050, 1.040], "sg_times": [datetime.now(), datetime.now()]}
        mock_vel.return_value = 5.0
        
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "Advice text"}
        mock_post.return_value = mock_response

        with patch('services.status.get_status_dict') as mock_status:
            mock_status.return_value = {"sg": 1.040, "temp": 20.0}
            get_proactive_advice()

        # Check that keep_alive: 0 was sent
        args, kwargs = mock_post.call_args
        payload = kwargs['json']
        self.assertEqual(payload['keep_alive'], 0)
        self.assertIn("Fermentation Velocity: 5.0", payload['prompt'])

    @patch('services.ai.requests.post')
    @patch('ml.features.query_batch_data')
    def test_predict_issues_stall(self, mock_query, mock_post):
        """Verify predict_issues detects slowing trends."""
        # Simulate significant slowing: 48h avg = 10 pts/day, 12h avg = 1 pt/day
        mock_query.side_effect = [
            {"sg_readings": [1.050, 1.0495], "sg_times": [datetime.now(), datetime.now()]}, # 12h
            {"sg_readings": [1.050, 1.040], "sg_times": [datetime.now(), datetime.now()]}   # 48h
        ]
        
        # We need to mock calculate_sg_velocity since we are mocking query_batch_data
        with patch('ml.features.calculate_sg_velocity') as mock_vel:
            mock_vel.side_effect = [1.0, 10.0] # 12h vs 48h
            
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"response": "High risk of stall"}
            mock_post.return_value = mock_response

            with patch('services.status.get_status_dict') as mock_status:
                mock_status.return_value = {"sg": 1.040}
                res = predict_issues()
                
                self.assertIsNotNone(res)
                self.assertIn("AI PREDICTION", res)

if __name__ == '__main__':
    unittest.main()
