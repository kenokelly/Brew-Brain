import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Ensure app is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../app')))

from main import app
from core.auth import API_TOKEN

class TestSimulation(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.client = self.app.test_client()
        self.headers = {"Authorization": f"Bearer {API_TOKEN}"}

    def test_sim_01_simulate_brew_day_og(self):
        from services.learning import simulate_brew_day
        grains = [{"weight_kg": 5.0, "potential": 1.037}]
        vol = 23
        eff = 75
        result = simulate_brew_day(grains, vol, eff)
        self.assertIn("predicted_og", result)
        self.assertGreater(result["predicted_og"], 1.0)

    @patch('services.ai.requests.post')
    def test_sim_02_predict_fg_monte_carlo(self, mock_post):
        # Mock requests.post inside simulate_brew_insight
        mock_res = MagicMock()
        mock_res.status_code = 200
        mock_res.json.return_value = {"response": "Mocked AI advice"}
        mock_post.return_value = mock_res
        
        from services.learning import run_monte_carlo_simulation
        # Test with known yeast logic
        result = run_monte_carlo_simulation(1.050, "US-05", 65.0)
        self.assertIn("predicted_fg_mean", result)
        self.assertEqual(result["llm_analysis"], "Mocked AI advice")

    @patch('services.ai.requests.post')
    def test_sim_03_ollama_graceful_fail(self, mock_post):
        mock_post.side_effect = Exception("Ollama offline")
        
        from services.learning import run_monte_carlo_simulation
        result = run_monte_carlo_simulation(1.050, "US-05", 65.0)
        self.assertIsNone(result["llm_analysis"])

    def test_sim_04_timeline_api(self):
        response = self.client.post('/api/automation/simulate/timeline', headers=self.headers, json={
            "efficiency": 75,
            "volume": 23,
            "yeast": "US-05",
            "grains": [{"weight_kg": 5.0, "potential": 1.037}]
        })
        self.assertEqual(response.status_code, 200)
        data = response.json.get("data", {})
        self.assertIn("timeline", data)
        self.assertGreater(len(data["timeline"]), 0)

    def test_sim_05_learning_simulate_api(self):
        response = self.client.post('/api/automation/learning/simulate', headers=self.headers, json={
            "efficiency": 75,
            "volume": 23,
            "yeast": "US-05",
            "grains": [{"weight_kg": 5.0, "potential": 1.037}]
        })
        self.assertEqual(response.status_code, 200)
        data = response.json
        self.assertIn("predicted_og", data)
        self.assertIn("predicted_fg", data)

if __name__ == '__main__':
    unittest.main()
