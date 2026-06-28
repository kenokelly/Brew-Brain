import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import json
from flask import Flask

# Ensure app is in path
app_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../app'))
if app_dir not in sys.path:
    sys.path.insert(0, app_dir)

from core.cache import cache
from services.brew_math import (
    calculate_dme_addition,
    calculate_dilution_water,
    calculate_boil_extension,
)
from services.brewday_coach import BrewSessionManager
from api.brewday import brewday_bp


class TestBrewMath(unittest.TestCase):
    """Tests for brew_math.py."""

    def test_calculate_dme_addition_success(self):
        # 1.040 to 1.050 with 20L
        res = calculate_dme_addition(1.040, 1.050, 20.0)
        # (1.050 - 1.040) * 20.0 * 1000 / 0.375 = 0.010 * 20000 / 0.375 = 533.33g
        self.assertAlmostEqual(res, 533.3333333333334)

    def test_calculate_dme_addition_invalid(self):
        with self.assertRaises(ValueError):
            calculate_dme_addition(1.050, 1.040, 20.0)  # target must be >= measured
        with self.assertRaises(ValueError):
            calculate_dme_addition(0.999, 1.050, 20.0)  # SG must be > 1.0
        with self.assertRaises(ValueError):
            calculate_dme_addition(1.040, 1.050, -5.0)  # Vol must be > 0

    def test_calculate_dilution_water_success(self):
        # 1.060 to 1.050 with 20L
        res = calculate_dilution_water(1.060, 1.050, 20.0)
        # ((1.060 - 1.0) / (1.050 - 1.0) * 20.0) - 20.0 = (0.060 / 0.050 * 20) - 20 = 24 - 20 = 4.0L
        self.assertAlmostEqual(res, 4.0)

    def test_calculate_dilution_water_invalid(self):
        with self.assertRaises(ValueError):
            calculate_dilution_water(1.040, 1.050, 20.0)  # target must be <= measured
        with self.assertRaises(ValueError):
            calculate_dilution_water(1.060, 0.999, 20.0)  # SG must be > 1.0

    def test_calculate_boil_extension_success(self):
        # 1.045 to 1.050 with 20L, boil off rate 0.05 L/min
        res = calculate_boil_extension(1.045, 1.050, 20.0, 0.05)
        # target_volume = 0.045 / 0.050 * 20 = 18.0L
        # to boil off = 2.0L
        # minutes = 2.0 / 0.05 = 40.0 min
        self.assertAlmostEqual(res, 40.0)

    def test_calculate_boil_extension_invalid(self):
        with self.assertRaises(ValueError):
            calculate_boil_extension(1.050, 1.045, 20.0, 0.05)  # target must be >= measured


class TestBrewSessionManager(unittest.TestCase):
    """Tests for BrewSessionManager."""

    def setUp(self):
        cache.clear()
        self.manager = BrewSessionManager()
        self.batch_id = "test-batch-123"
        self.recipe_data = {
            "name": "Hazy Test IPA",
            "og": 1.055,
            "fg": 1.010,
            "volume": 20,
            "boil_off_rate_lpm": 0.05
        }

    def tearDown(self):
        cache.clear()

    def test_session_lifecycle(self):
        # Start
        session = self.manager.start_session(self.batch_id, self.recipe_data)
        self.assertEqual(session["batch_id"], self.batch_id)
        self.assertEqual(session["phase"], "setup")
        self.assertEqual(session["phase_index"], 0)

        # Get state
        state = self.manager.get_current_state(self.batch_id)
        self.assertIsNotNone(state)
        self.assertEqual(state["batch_name"], "Hazy Test IPA")

        # Advance step
        updated = self.manager.advance_step(self.batch_id)
        self.assertEqual(updated["phase"], "strike")
        self.assertEqual(updated["phase_index"], 1)

        # Add timer
        timer = self.manager.add_timer(self.batch_id, "Mash Rest", 60, "mash")
        self.assertEqual(timer["name"], "Mash Rest")
        self.assertEqual(timer["duration_min"], 60)

        timers = self.manager.get_timers(self.batch_id)
        self.assertEqual(len(timers), 1)
        self.assertEqual(timers[0]["name"], "Mash Rest")

        # End session
        summary = self.manager.end_session(self.batch_id)
        self.assertEqual(summary["phase"], "complete")
        self.assertIn("ended_at", summary)
        self.assertEqual(len(summary["timers"]), 1)

    def test_record_gravity_reading_low(self):
        self.manager.start_session(self.batch_id, self.recipe_data)
        # Target OG is 1.055. If we measure 1.050:
        reading = self.manager.record_gravity_reading(self.batch_id, 1.050, 20.0, "pre_boil")
        self.assertEqual(reading["sg"], 1.050)
        self.assertEqual(reading["volume_l"], 20.0)

        # Check that corrections are calculated
        corr = reading["corrections"]
        self.assertIn("dme_addition_g", corr)
        self.assertIn("boil_extension_min", corr)
        self.assertNotIn("dilution_water_l", corr)

    def test_record_gravity_reading_high(self):
        self.manager.start_session(self.batch_id, self.recipe_data)
        # Target OG is 1.055. If we measure 1.060:
        reading = self.manager.record_gravity_reading(self.batch_id, 1.060, 20.0, "pre_boil")
        self.assertEqual(reading["sg"], 1.060)

        corr = reading["corrections"]
        self.assertIn("dilution_water_l", corr)
        self.assertNotIn("dme_addition_g", corr)


class TestBrewDayAPI(unittest.TestCase):
    """Integration/unit tests for Flask brewday blueprint."""

    def setUp(self):
        cache.clear()
        self.app = Flask(__name__)
        self.app.register_blueprint(brewday_bp, url_prefix="/api/brewday")
        self.client = self.app.test_client()
        self.batch_id = "api-test-batch"
        self.recipe = {
            "name": "API IPA",
            "og": 1.052,
            "volume": 20
        }

    def tearDown(self):
        cache.clear()

    def test_start_session_api(self):
        res = self.client.post("/api/brewday/start", json={
            "batch_id": self.batch_id,
            "recipe": self.recipe
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["data"]["batch_id"], self.batch_id)

    def test_get_state_api(self):
        # 404 if no session
        res = self.client.get(f"/api/brewday/state?batch_id={self.batch_id}")
        self.assertEqual(res.status_code, 404)

        # Start and get state
        self.client.post("/api/brewday/start", json={
            "batch_id": self.batch_id,
            "recipe": self.recipe
        })
        res = self.client.get(f"/api/brewday/state?batch_id={self.batch_id}")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["data"]["batch_id"], self.batch_id)

    @patch("services.ai.requests.post")
    def test_actions_api(self, mock_post):
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "Mash at 65C."}
        mock_post.return_value = mock_response

        # Start session
        self.client.post("/api/brewday/start", json={
            "batch_id": self.batch_id,
            "recipe": self.recipe
        })

        # Test Chat Action
        res = self.client.post("/api/brewday/action", json={
            "batch_id": self.batch_id,
            "action_type": "chat",
            "message": "What is my mash temperature?"
        })
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["data"]["response"], "Mash at 65C.")

        # Test Advance Action
        res = self.client.post("/api/brewday/action", json={
            "batch_id": self.batch_id,
            "action_type": "advance"
        })
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["data"]["phase"], "strike")

        # Test Timer Action
        res = self.client.post("/api/brewday/action", json={
            "batch_id": self.batch_id,
            "action_type": "timer",
            "name": "Boil Addition",
            "duration_min": 15,
            "addition_type": "hop"
        })
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["data"]["name"], "Boil Addition")

    @patch("services.ai.requests.post")
    def test_correct_api(self, mock_post):
        # Mock LLM explanation
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "Wort is slightly weak. Add DME to increase gravity."}
        mock_post.return_value = mock_response

        # Start session
        self.client.post("/api/brewday/start", json={
            "batch_id": self.batch_id,
            "recipe": self.recipe
        })

        # Call correct API
        res = self.client.post("/api/brewday/correct", json={
            "batch_id": self.batch_id,
            "measured_sg": 1.045,
            "measured_volume": 20.0,
            "stage": "pre_boil"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()["data"]
        self.assertIn("reading", data)
        self.assertIn("explanation", data)
        self.assertEqual(data["explanation"]["explanation"], "Wort is slightly weak. Add DME to increase gravity.")

    @patch("services.ai.requests.post")
    @patch("services.brew_logger.generate_brewday_log")
    def test_complete_api(self, mock_log, mock_post):
        # Mock LLM evaluation
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "Great brew day!"}
        mock_post.return_value = mock_response
        mock_log.return_value = "/path/to/log.md"

        # Start session
        self.client.post("/api/brewday/start", json={
            "batch_id": self.batch_id,
            "recipe": self.recipe
        })

        # Complete session
        res = self.client.post("/api/brewday/complete", json={
            "batch_id": self.batch_id
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()["data"]
        self.assertEqual(data["evaluation"]["evaluation"], "Great brew day!")
        self.assertEqual(data["log_path"], "/path/to/log.md")


if __name__ == "__main__":
    unittest.main()
