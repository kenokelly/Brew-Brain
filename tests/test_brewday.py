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


class TestBrewDayRamps(unittest.TestCase):
    """Heating ramp logging, ETA and history-based predictions."""

    def setUp(self):
        import tempfile
        from services import brewday_ramp
        cache.clear()
        self.ramp = brewday_ramp
        self.tmp = tempfile.TemporaryDirectory()
        self.history_patch = patch.object(
            brewday_ramp, "HISTORY_FILE", os.path.join(self.tmp.name, "ramp_history.json")
        )
        self.history_patch.start()
        self.influx_patch = patch.object(brewday_ramp, "write_temp_point")
        self.influx_patch.start()
        self.manager = BrewSessionManager()
        self.batch_id = "ramp-batch"
        self.manager.start_session(self.batch_id, {"name": "Ramp IPA", "target_og": 1.050,
                                                   "target_volume_l": 23})

    def tearDown(self):
        self.history_patch.stop()
        self.influx_patch.stop()
        self.tmp.cleanup()
        cache.clear()

    def _readings(self, temps, minutes_apart=5, phase="strike", target=72.0):
        from datetime import datetime, timedelta, timezone
        t0 = datetime(2026, 10, 18, 9, 0, tzinfo=timezone.utc)
        return [{"temp_c": t, "target_c": target, "phase": phase,
                 "timestamp": (t0 + timedelta(minutes=i * minutes_apart)).isoformat()}
                for i, t in enumerate(temps)]

    def test_slope_and_eta_from_live_readings(self):
        # 2 °C per minute, 52 °C now, 20 °C to go -> 10 min
        session = {"temp_readings": self._readings([12, 22, 32, 42, 52])}
        current = self.ramp.ramp_summary(session, history=[])["current"]
        self.assertAlmostEqual(current["rate_c_per_min"], 2.0)
        self.assertEqual(current["eta_source"], "live")
        self.assertAlmostEqual(current["eta_min"], 10.0)

    def test_segments_split_on_target_change(self):
        readings = self._readings([15, 40, 65], target=66.0, phase="strike") + \
                   self._readings([66, 66, 75], target=76.0, phase="mash")
        segments = self.ramp.split_segments(readings)
        self.assertEqual([s["phase"] for s in segments], ["strike", "mash"])
        self.assertTrue(segments[0]["is_ramp"])

    def test_eta_falls_back_to_history(self):
        history = [{"ramps": [{"phase": "strike", "rate_c_per_min": 1.5}]},
                   {"ramps": [{"phase": "strike", "rate_c_per_min": 2.5}]}]
        session = {"temp_readings": self._readings([42])}
        current = self.ramp.ramp_summary(session, history=history)["current"]
        self.assertEqual(current["eta_source"], "history")
        self.assertEqual(current["history_brews"], 2)
        self.assertAlmostEqual(current["eta_min"], 15.0)  # 30 °C at 2.0 °C/min

    def test_target_reached(self):
        session = {"temp_readings": self._readings([60, 73])}
        self.assertEqual(self.ramp.ramp_summary(session, history=[])["current"]["eta_source"], "reached")

    def test_record_temperature_and_history_saved_on_end(self):
        result = self.manager.record_temperature(self.batch_id, 14.0, 72.0)
        self.assertEqual(result["reading"]["phase"], "setup")
        state = self.manager.get_current_state(self.batch_id)
        state["temp_readings"] = self._readings([14, 34, 54, 71])
        cache.set(self.manager._session_key(self.batch_id), state)

        summary = self.manager.end_session(self.batch_id)
        self.assertIn("ramp", summary)
        history = self.ramp.load_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["volume_l"], 23)
        self.assertEqual(history[0]["ramps"][0]["phase"], "strike")
        self.assertIsNone(self.manager.get_current_state("last"))

    def test_last_resolves_to_latest_session(self):
        self.assertEqual(self.manager.get_current_state("last")["batch_id"], self.batch_id)

    def test_target_og_key_gives_corrections(self):
        reading = self.manager.record_gravity_reading(self.batch_id, 1.040, 23, "post_boil")
        self.assertIn("dme_addition_g", reading["corrections"])
        self.assertEqual(reading["corrections"]["target_sg"], 1.050)

    def test_api_temp_action_ramp_and_aliases(self):
        app = Flask(__name__)
        app.register_blueprint(brewday_bp, url_prefix="/api/brewday")
        client = app.test_client()

        res = client.post("/api/brewday/action", json={
            "batch_id": self.batch_id, "action_type": "temp", "temp_c": 15, "target_c": 72})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["data"]["ramp"]["current"]["target_c"], 72.0)

        res = client.post("/api/brewday/action", json={
            "batch_id": self.batch_id, "action_type": "temp", "temp_c": "hot"})
        self.assertEqual(res.status_code, 400)
        res = client.post("/api/brewday/action", json={
            "batch_id": self.batch_id, "action_type": "temp", "temp_c": 160})
        self.assertEqual(res.status_code, 400)

        res = client.get("/api/brewday/ramp?batch_id=last")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.get_json()["data"]["segments"]), 1)

        res = client.post("/api/brewday/action", json={
            "batch_id": self.batch_id, "action_type": "next_phase"})
        self.assertEqual(res.get_json()["data"]["phase"], "strike")
        res = client.post("/api/brewday/action", json={
            "batch_id": self.batch_id, "action_type": "add_timer", "name": "Mash", "duration_min": 60})
        self.assertEqual(res.status_code, 200)
