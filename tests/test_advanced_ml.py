import unittest
import sys
import os

# Add app directory to path
app_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../app"))
if app_dir not in sys.path:
    sys.path.insert(0, app_dir)

from ml.schemas import (
    YeastPitchDetails,
    DryHopAddition,
    BatchMLFeatures,
    PredictionOutputSchema,
)
from ml.kinetic_engine import (
    calculate_viability_decay,
    calculate_pitch_density,
    estimate_lag_phase_hours,
)
from ml.creep_analyzer import (
    get_hop_enzymatic_index,
    detect_hop_creep_signature,
    calculate_hop_creep_offset,
)
from ml.correlation import (
    calculate_dtw_distance,
    calculate_cross_correlation_score,
    find_best_peer_batch,
)


class TestMLSchemas(unittest.TestCase):
    """Tests for Pydantic models in ml/schemas.py."""

    def test_yeast_pitch_details(self):
        pitch = YeastPitchDetails(
            cells_pitch_billions=200.0,
            viability_percent=90.0,
            yeast_age_days=14,
            generation=2,
            is_starter=True,
            starter_volume_liters=1.5,
        )
        self.assertEqual(pitch.cells_pitch_billions, 200.0)
        self.assertTrue(pitch.is_starter)

    def test_dry_hop_addition(self):
        addition = DryHopAddition(
            addition_time_hours=96.0,
            dosage_g_l=5.0,
            temperature_c=18.0,
            hop_variety="Citra",
        )
        self.assertEqual(addition.dosage_g_l, 5.0)
        self.assertEqual(addition.hop_variety, "Citra")

    def test_prediction_output_schema(self):
        pred = PredictionOutputSchema(
            batch_id="batch_01",
            predicted_fg=1.011,
            predicted_fg_lower_bound=1.009,
            predicted_fg_upper_bound=1.013,
            days_to_fg=3.5,
            hop_creep_detected=True,
            hop_creep_gravity_offset=-0.002,
            correlation_score=0.88,
        )
        self.assertEqual(pred.predicted_fg, 1.011)
        self.assertTrue(pred.hop_creep_detected)


class TestKineticEngine(unittest.TestCase):
    """Tests for ml/kinetic_engine.py."""

    def test_calculate_viability_decay(self):
        # 0 days = 100%
        self.assertEqual(calculate_viability_decay(0), 100.0)
        # 30 days at decay 0.008 = 100 * e^(-0.24) approx 78.7%
        v30 = calculate_viability_decay(30)
        self.assertAlmostEqual(v30, 78.7, places=1)
        # 500 days clamped to 5.0%
        self.assertEqual(calculate_viability_decay(500), 5.0)

    def test_calculate_pitch_density(self):
        # 200B cells, 20L, 1.050 OG (12.5°P) -> (200 * 1000) / (20 * 12.5) = 200000 / 250 = 800?? No, 200B cells = 200,000M / (20L * 12.5P) = 800??
        # Wait: 200B = 200,000 million cells.
        # 200,000 M / (20,000 mL * 12.5P) = 200,000 / 250,000 = 0.8 M/mL/P
        density = calculate_pitch_density(200.0, 20.0, 1.050)
        self.assertEqual(density, 0.8)

    def test_estimate_lag_phase_hours(self):
        lag = estimate_lag_phase_hours(viability_pct=95.0, pitch_density=0.75)
        self.assertGreater(lag, 5.0)
        self.assertLess(lag, 24.0)


class TestCreepAnalyzer(unittest.TestCase):
    """Tests for ml/creep_analyzer.py."""

    def test_get_hop_enzymatic_index(self):
        self.assertEqual(get_hop_enzymatic_index("Amarillo"), 1.4)
        self.assertEqual(get_hop_enzymatic_index("Cascade"), 1.3)
        self.assertEqual(get_hop_enzymatic_index("Unknown Hop"), 1.0)

    def test_detect_hop_creep_signature(self):
        # High attenuation (OG 1.050, SG 1.010) + negative velocity (-0.002) = hop creep
        self.assertTrue(detect_hop_creep_signature([-0.002], current_sg=1.010, og=1.050))
        # Low attenuation (OG 1.050, SG 1.035) -> False
        self.assertFalse(detect_hop_creep_signature([-0.002], current_sg=1.035, og=1.050))

    def test_calculate_hop_creep_offset(self):
        additions = [
            {"dosage_g_l": 6.0, "temperature_c": 18.0, "hop_variety": "Amarillo"}
        ]
        res = calculate_hop_creep_offset(additions)
        self.assertTrue(res["creep_detected"])
        self.assertLess(res["gravity_offset"], 0.0)
        self.assertGreater(res["time_extension_days"], 0.0)


class TestCorrelation(unittest.TestCase):
    """Tests for ml/correlation.py."""

    def test_calculate_dtw_distance_identical(self):
        seq = [-0.010, -0.008, -0.004, -0.001]
        dist = calculate_dtw_distance(seq, seq)
        self.assertEqual(dist, 0.0)

    def test_calculate_cross_correlation_score(self):
        seq1 = [-0.010, -0.008, -0.004, -0.001]
        seq2 = [-0.010, -0.008, -0.004, -0.001]
        score = calculate_cross_correlation_score(seq1, seq2)
        self.assertEqual(score, 1.0)

    def test_find_best_peer_batch(self):
        active = [-0.010, -0.008, -0.004, -0.001]
        peers = [
            {"batch_id": "batch_A", "velocity_curve": [-0.010, -0.008, -0.004, -0.001]},
            {"batch_id": "batch_B", "velocity_curve": [0.0, 0.0, 0.0, 0.0]},
        ]
        res = find_best_peer_batch(active, peers)
        self.assertEqual(res["best_peer_id"], "batch_A")
        self.assertEqual(res["correlation_score"], 1.0)
        self.assertFalse(res["is_anomalous"])


if __name__ == "__main__":
    unittest.main()
