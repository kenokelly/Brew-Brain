import unittest
from unittest.mock import patch, MagicMock
import sys
import os
from flask import Flask

# Add app directory to path
app_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../app"))
if app_dir not in sys.path:
    sys.path.insert(0, app_dir)

from services.scale_processor import calculate_keg_volume
from services.flow_manager import process_pour_event
from api.telemetry_receiver import telemetry_receiver_bp
from core.config import set_config, get_config


class TestScaleProcessor(unittest.TestCase):
    """Tests for scale_processor.py."""

    def test_calculate_keg_volume_full_keg(self):
        # 19L full keg with ~4.5kg tare weight + 19kg beer = 23.5kg raw
        res = calculate_keg_volume(23.5, tare_weight_kg=4.5, sg=1.010, keg_capacity_l=19.0)
        self.assertEqual(res["raw_weight_kg"], 23.5)
        self.assertEqual(res["net_weight_kg"], 19.0)
        self.assertAlmostEqual(res["volume_remaining_l"], 18.81, places=2)
        self.assertFalse(res["is_empty"])
        self.assertFalse(res["is_disconnected"])

    def test_calculate_keg_volume_empty_keg(self):
        # Raw weight close to tare weight
        res = calculate_keg_volume(4.6, tare_weight_kg=4.5, sg=1.010)
        self.assertTrue(res["is_empty"])
        self.assertFalse(res["is_disconnected"])

    def test_calculate_keg_volume_disconnected(self):
        # Raw weight < 0.5kg indicates scale unweighted / disconnected
        res = calculate_keg_volume(0.2, tare_weight_kg=4.5)
        self.assertTrue(res["is_disconnected"])
        self.assertTrue(res["is_empty"])

    def test_calculate_keg_volume_invalid_inputs(self):
        with self.assertRaises(ValueError):
            calculate_keg_volume(None)
        with self.assertRaises(ValueError):
            calculate_keg_volume(-2.0)


class TestFlowManager(unittest.TestCase):
    """Tests for flow_manager.py."""

    def setUp(self):
        set_config("taps", {
            "tap1": {
                "name": "Test IPA",
                "keg_volume_l": 19.0,
                "volume_remaining_ml": 19000.0,
                "remaining_pct": 100.0,
            }
        })

    def tearDown(self):
        set_config("taps", {})

    def test_process_pour_event_valid(self):
        # 3340 pulses at 5880 pulses/L = ~568mL (1 pint)
        res = process_pour_event("tap1", pulse_count=3340, duration_sec=10.0)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["tap_id"], "tap1")
        self.assertAlmostEqual(res["volume_ml"], 568.0, places=1)
        self.assertLess(res["new_remaining_pct"], 100.0)
        self.assertFalse(res["is_low_volume_alert"])

    def test_process_pour_event_noise_threshold(self):
        # Small pulse count (<15mL) should be ignored as noise
        res = process_pour_event("tap1", pulse_count=50)
        self.assertEqual(res["status"], "ignored")
        self.assertIn("below noise threshold", res["reason"])

    def test_process_pour_event_nonexistent_tap(self):
        res = process_pour_event("tap99", pulse_count=3340)
        self.assertEqual(res["status"], "error")
        self.assertIn("not found", res["error"])


class TestTelemetryReceiverAPI(unittest.TestCase):
    """Integration/unit tests for Flask telemetry receiver API endpoints."""

    def setUp(self):
        set_config("taps", {
            "tap1": {
                "name": "API IPA",
                "fg": 1.010,
                "keg_volume_l": 19.0,
                "volume_remaining_ml": 19000.0,
                "remaining_pct": 100.0,
            }
        })
        self.app = Flask(__name__)
        self.app.register_blueprint(telemetry_receiver_bp, url_prefix="/api/automation/telemetry")
        self.client = self.app.test_client()

    def tearDown(self):
        set_config("taps", {})

    def test_scale_telemetry_endpoint(self):
        res = self.client.post("/api/automation/telemetry/scale", json={
            "tap_id": "tap1",
            "sensor_id": "scale_01",
            "weight_kg": 15.0,
            "tare_weight_kg": 4.5,
            "battery_v": 4.15,
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["data"]["tap_id"], "tap1")
        self.assertIn("processed", data["data"])

    def test_scale_telemetry_missing_args(self):
        res = self.client.post("/api/automation/telemetry/scale", json={
            "weight_kg": 15.0
        })
        self.assertEqual(res.status_code, 400)

    def test_flow_telemetry_endpoint(self):
        res = self.client.post("/api/automation/telemetry/flow", json={
            "tap_id": "tap1",
            "sensor_id": "flow_01",
            "pulse_count": 3340,
            "duration_sec": 12.0,
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["data"]["status"], "success")

    def test_flow_telemetry_missing_args(self):
        res = self.client.post("/api/automation/telemetry/flow", json={
            "tap_id": "tap1"
        })
        self.assertEqual(res.status_code, 400)


if __name__ == "__main__":
    unittest.main()
