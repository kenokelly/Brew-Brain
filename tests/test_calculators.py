"""
Brew Brain Calculator Test Suite

Comprehensive tests for all brewing calculators including:
- Carbonation PSI
- Refractometer correction
- Priming sugar
- Water chemistry
- Mash pH
- Hop freshness
- IBU calculations
- Batch cost
"""

import pytest
import sys
import os

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestCarbonationCalculator:
    """Tests for carbonation PSI calculation."""
    
    def test_carbonation_at_4c_2_5_volumes(self):
        from app.services.calculator import calculate_carbonation_psi
        result = calculate_carbonation_psi(4, 2.5)
        
        assert "psi" in result
        assert "bar" in result
        assert result["psi"] > 10 and result["psi"] < 15  # ~12 PSI expected
        assert result["bar"] > 0.7 and result["bar"] < 1.2
        
    def test_carbonation_at_20c_2_4_volumes(self):
        from app.services.calculator import calculate_carbonation_psi
        result = calculate_carbonation_psi(20, 2.4)
        
        # Higher temp = higher PSI for same volumes
        assert result["psi"] > 15
        
    def test_carbonation_low_volumes_cask(self):
        from app.services.calculator import calculate_carbonation_psi
        result = calculate_carbonation_psi(12, 1.5)
        
        assert result["style_suggestion"] == "British Cask / Real Ale"
        
    def test_carbonation_high_volumes_belgian(self):
        from app.services.calculator import calculate_carbonation_psi
        result = calculate_carbonation_psi(4, 3.5)
        
        assert "Belgian" in result["style_suggestion"] or "Hefeweizen" in result["style_suggestion"]


class TestRefractometerCorrection:
    """Tests for refractometer alcohol correction."""
    
    def test_refractometer_typical_ale(self):
        from app.services.calculator import correct_refractometer_reading
        # OG 15 Brix (~1.060), FG reading 8 Brix
        result = correct_refractometer_reading(8.0, 15.0)
        
        assert result["original_gravity"] > 1.055 and result["original_gravity"] < 1.065
        assert result["corrected_final_gravity"] > 1.008 and result["corrected_final_gravity"] < 1.020
        assert result["abv"] > 4.0 and result["abv"] < 8.0
        
    def test_refractometer_high_gravity(self):
        from app.services.calculator import correct_refractometer_reading
        # OG 20 Brix (~1.083), FG reading 10 Brix
        result = correct_refractometer_reading(10.0, 20.0)
        
        assert result["abv"] > 7.0  # Should be strong beer
        
    def test_refractometer_custom_wcf(self):
        from app.services.calculator import correct_refractometer_reading
        result = correct_refractometer_reading(8.0, 15.0, wort_correction_factor=1.00)
        
        # WCF affects the calculation
        assert "corrected_final_gravity" in result


class TestPrimingSugar:
    """Tests for priming sugar calculation."""
    
    def test_priming_typical_batch(self):
        from app.services.calculator import calculate_priming_sugar
        result = calculate_priming_sugar(20, 20, 2.4, "corn_sugar")
        
        assert result["total_grams"] > 100 and result["total_grams"] < 150
        assert result["per_500ml_bottle"] > 2 and result["per_500ml_bottle"] < 5
        
    def test_priming_cold_beer(self):
        from app.services.calculator import calculate_priming_sugar
        result_cold = calculate_priming_sugar(20, 4, 2.4, "corn_sugar")
        result_warm = calculate_priming_sugar(20, 20, 2.4, "corn_sugar")
        
        # Cold beer has more residual CO2, needs less sugar
        assert result_cold["total_grams"] < result_warm["total_grams"]
        
    def test_priming_different_sugars(self):
        from app.services.calculator import calculate_priming_sugar
        result_corn = calculate_priming_sugar(20, 20, 2.4, "corn_sugar")
        result_table = calculate_priming_sugar(20, 20, 2.4, "table_sugar")
        result_honey = calculate_priming_sugar(20, 20, 2.4, "honey")
        
        # Different sugar types have different densities
        assert result_table["total_grams"] < result_corn["total_grams"]
        assert result_honey["total_grams"] > result_corn["total_grams"]


class TestWaterChemistry:
    """Tests for water chemistry salt additions."""
    
    def test_water_chemistry_neipa_from_ro(self):
        from app.services.water_chemistry import calculate_salt_additions, get_ro_water_source
        
        source = get_ro_water_source()
        result = calculate_salt_additions(source, "neipa", 23)
        
        assert "gypsum_g" in result
        assert "calcium_chloride_g" in result
        assert result["calcium_chloride_g"] > result["gypsum_g"]  # NEIPA is chloride-forward
        assert result["sulfate_chloride_ratio"] < 1.0  # Malty ratio
        
    def test_water_chemistry_west_coast_from_ro(self):
        from app.services.water_chemistry import calculate_salt_additions, get_ro_water_source
        
        source = get_ro_water_source()
        result = calculate_salt_additions(source, "west_coast", 23)
        
        # West coast should be sulfate-forward
        assert result["gypsum_g"] > result["calcium_chloride_g"]
        assert result["sulfate_chloride_ratio"] > 2.0
        
    def test_water_chemistry_unknown_profile(self):
        from app.services.water_chemistry import calculate_salt_additions, get_ro_water_source
        
        source = get_ro_water_source()
        result = calculate_salt_additions(source, "unknown_profile_xyz", 23)
        
        assert "error" in result


class TestMashpH:
    """Tests for mash pH prediction."""
    
    def test_mash_ph_pale_ale(self):
        from app.services.mash_chemistry import predict_mash_ph
        
        grains = [
            {"name": "Pale Malt", "weight_kg": 5.0, "lovibond": 2.5}
        ]
        water = {"bicarbonate": 50, "calcium": 80, "magnesium": 10}
        
        result = predict_mash_ph(grains, water)
        
        assert "predicted_ph" in result
        assert result["predicted_ph"] > 5.0 and result["predicted_ph"] < 6.0
        
    def test_mash_ph_stout_dark_grain(self):
        from app.services.mash_chemistry import predict_mash_ph
        
        grains = [
            {"name": "Pale Malt", "weight_kg": 4.0, "lovibond": 2.5},
            {"name": "Roasted Barley", "weight_kg": 0.5, "lovibond": 500}
        ]
        water = {"bicarbonate": 50, "calcium": 80, "magnesium": 10}
        
        result = predict_mash_ph(grains, water)
        
        # Dark grains lower pH
        assert result["predicted_ph"] < 5.6
        
    def test_mash_ph_high_alkalinity_water(self):
        from app.services.mash_chemistry import predict_mash_ph
        
        grains = [{"name": "Pale Malt", "weight_kg": 5.0, "lovibond": 2.5}]
        water = {"bicarbonate": 250, "calcium": 50, "magnesium": 5}
        
        result = predict_mash_ph(grains, water)
        
        # High bicarb raises pH
        assert result["predicted_ph"] > 5.5
        assert result["lactic_acid_ml"] > 0  # Should suggest acid addition


class TestHopFreshness:
    """Tests for hop freshness calculation."""
    
    def test_hop_freshness_fresh_citra(self):
        from app.services.sourcing import calculate_hop_freshness
        
        result = calculate_hop_freshness(
            "Citra", 12.0, "2026-01-01", "freezer", "2026-01-17"
        )
        
        assert result["freshness_rating"] == "Excellent"
        assert result["current_alpha"] > 11.5  # Minimal degradation
        
    def test_hop_freshness_old_cascade_ambient(self):
        from app.services.sourcing import calculate_hop_freshness
        
        # 1 year old at room temp
        result = calculate_hop_freshness(
            "Cascade", 6.0, "2025-01-17", "ambient", "2026-01-17"
        )
        
        # Cascade has high HSI (50%), should see significant loss
        assert result["current_alpha"] < 4.0
        assert result["freshness_rating"] in ["Poor", "Bad - Consider Replacing"]
        
    def test_hop_freshness_unknown_variety(self):
        from app.services.sourcing import calculate_hop_freshness
        
        result = calculate_hop_freshness(
            "Super Unknown Hop 2000", 10.0, "2025-06-01", "fridge", "2026-01-17"
        )
        
        # Should use default HSI
        assert "current_alpha" in result
        assert result["hsi"] == 35  # Default value


class TestIBUCalculator:
    """Tests for Tinseth IBU calculation."""
    
    def test_ibu_60_min_boil(self):
        from app.services.calculator import calculate_tinseth_ibu
        
        # 50g hops, 10% AA, 60 min, 23L, 1.050 OG
        ibu = calculate_tinseth_ibu(50, 10, 60, 23, 1.050)
        
        assert ibu > 30 and ibu < 80  # Reasonable range
        
    def test_ibu_dry_hop_zero(self):
        from app.services.calculator import calculate_tinseth_ibu
        
        # 0 min boil = no IBU (dry hop)
        ibu = calculate_tinseth_ibu(100, 12, 0, 23, 1.050)
        
        assert ibu == 0
        
    def test_ibu_high_gravity_lower(self):
        from app.services.calculator import calculate_tinseth_ibu
        
        ibu_normal = calculate_tinseth_ibu(50, 10, 60, 23, 1.050)
        ibu_high_grav = calculate_tinseth_ibu(50, 10, 60, 23, 1.090)
        
        # Higher gravity = lower utilization = lower IBU
        assert ibu_high_grav < ibu_normal


class TestBatchCost:
    """Tests for batch cost calculation."""
    
    def test_batch_cost_basic(self):
        from app.services.calculator import calculate_batch_cost
        
        items = [
            {"cost": 10.0},
            {"cost": 5.0},
            {"cost": 3.50}
        ]
        result = calculate_batch_cost(items, 23)
        
        assert result["total_cost"] == 18.50
        assert result["pints"] > 40  # ~40 UK pints in 23L
        assert result["cost_per_pint"] < 0.50


def run_tests_with_summary():
    """Run all tests and print summary."""
    print("=" * 60)
    print("🧪 Brew Brain Calculator Test Suite")
    print("=" * 60)
    
    # Run pytest
    result = pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-x"  # Stop on first failure
    ])
    
    return result


if __name__ == "__main__":
    run_tests_with_summary()
