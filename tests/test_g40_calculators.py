import unittest
import logging
from app.services.hop_math import calculate_tinseth_ibu, calculate_grain_scaling

# Disable logging during tests
logging.getLogger("app.services.hop_math").setLevel(logging.CRITICAL)

class TestG40Calculators(unittest.TestCase):

    def test_tinseth_ibu_calculation(self):
        """Verify Tinseth IBU calculation logic and G40 boost."""
        # Standard values for an IPA addition
        alpha = 12.5
        grams = 50.0
        time = 60.0
        gravity = 1.050
        volume = 20.0
        
        # 1. Non-G40 baseline
        ibu_base = calculate_tinseth_ibu(alpha, grams, time, gravity, volume, is_g40=False)
        self.assertGreater(ibu_base, 0)
        
        # 2. G40 boosted (should be 10% higher)
        ibu_g40 = calculate_tinseth_ibu(alpha, grams, time, gravity, volume, is_g40=True)
        self.assertAlmostEqual(ibu_g40, round(ibu_base * 1.10, 1), places=1)

    def test_grain_scaling_efficiency_drop(self):
        """Verify efficiency drops as grain bill increases on G40."""
        base_eff = 75.0
        
        # 1. Normal batch (6kg) - No drop
        res_normal = calculate_grain_scaling(6.0, 1.050, base_efficiency=base_eff)
        self.assertEqual(res_normal["estimated_efficiency"], 75.0)
        
        # 2. Heavy batch (10kg) - Should drop by (10-7)*2 = 6%
        res_heavy = calculate_grain_scaling(10.0, 1.085, base_efficiency=base_eff)
        self.assertEqual(res_heavy["estimated_efficiency"], 69.0)
        self.assertEqual(res_heavy["efficiency_drop"], 6.0)
        self.assertTrue(res_heavy["is_high_gravity"])

    def test_grain_scaling_floor(self):
        """Verify efficiency never drops below the 55% sanity floor."""
        # Extreme batch (18kg - theoretical max)
        res_extreme = calculate_grain_scaling(18.0, 1.120, base_efficiency=75.0)
        # (18-7)*2 = 22% drop -> 75-22 = 53% -> Should floor to 55%
        self.assertEqual(res_extreme["estimated_efficiency"], 55.0)

if __name__ == '__main__':
    unittest.main()
