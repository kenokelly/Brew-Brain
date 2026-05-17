import unittest
from app.services.water_chemistry import calculate_salt_additions, get_ro_water_source

class TestWaterChemistry(unittest.TestCase):

    def test_calculate_salt_additions_ro_to_west_coast(self):
        """Verify salt additions from RO water to West Coast profile."""
        source = get_ro_water_source()
        target = "west_coast"
        volume = 23.0
        
        result = calculate_salt_additions(source, target, volume)
        
        # Check final sulfate (target is 250)
        # 250.0 should be achieved via ~10.3g Gypsum
        self.assertAlmostEqual(result["final_sulfate"], 250.0, delta=2.0)
        
        # Check Ratio (should be > 2.0 for West Coast)
        self.assertGreater(result["sulfate_chloride_ratio"], 2.0)

    def test_calculate_salt_additions_ro_to_neipa(self):
        """Verify salt additions from RO water to NEIPA juicy profile."""
        source = get_ro_water_source()
        target = "neipa_juicy"
        
        result = calculate_salt_additions(source, target, 23.0)
        
        # Ratio should be low (< 1.0) for soft mouthfeel
        # NEIPA Juicy Target: SO4=80, CL=150 -> Ratio ~0.53
        self.assertLess(result["sulfate_chloride_ratio"], 1.0)
        self.assertIn("Soft", result["ratio_description"])

    def test_invalid_profile(self):
        """Verify handling of unknown profiles."""
        res = calculate_salt_additions({}, "invalid_name")
        self.assertIn("error", res)

if __name__ == '__main__':
    unittest.main()
