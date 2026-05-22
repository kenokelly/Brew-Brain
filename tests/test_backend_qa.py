"""
Backend QA Tests — Stream 5.2
Tests for the Monte Carlo simulation engine and Tap List service logic.
These are pure Python unit tests that run without Flask or InfluxDB.
"""
import pytest
import sys
import os
from unittest.mock import patch, MagicMock

# Add app directory to path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))


class TestMonteCarloSimulation:
    """Tests for services.learning.run_monte_carlo_simulation"""

    @patch('services.learning.get_history')
    def test_returns_expected_keys(self, mock_history):
        """Result dict must contain all required fields."""
        mock_history.return_value = []
        
        from services.learning import run_monte_carlo_simulation
        result = run_monte_carlo_simulation(1.055, "US-05", 65.0)

        assert "predicted_fg_mean" in result
        assert "predicted_fg_p5" in result
        assert "predicted_fg_p95" in result
        assert "llm_analysis" in result

    @patch('services.learning.get_history')
    def test_fg_is_less_than_og(self, mock_history):
        """Predicted FG must always be lower than the target OG."""
        mock_history.return_value = []
        
        from services.learning import run_monte_carlo_simulation
        result = run_monte_carlo_simulation(1.060, "US-05", 65.0)

        assert result["predicted_fg_mean"] < 1.060
        assert result["predicted_fg_p5"] < 1.060

    @patch('services.learning.get_history')
    def test_fg_is_physically_valid(self, mock_history):
        """FG must be >= 1.000 (gravity of pure water)."""
        mock_history.return_value = []
        
        from services.learning import run_monte_carlo_simulation
        result = run_monte_carlo_simulation(1.040, "US-05", 62.0)

        assert result["predicted_fg_mean"] >= 1.000
        assert result["predicted_fg_p5"] >= 1.000

    @patch('services.learning.get_history')
    def test_confidence_interval_ordering(self, mock_history):
        """p5 must be lower than p95."""
        mock_history.return_value = []
        
        from services.learning import run_monte_carlo_simulation
        result = run_monte_carlo_simulation(1.050, "US-05", 66.0)

        assert result["predicted_fg_p5"] <= result["predicted_fg_p95"]

    @patch('services.learning.get_history')
    def test_higher_mash_temp_raises_fg(self, mock_history):
        """Higher mash temperature should produce a higher mean FG (less fermentable wort)."""
        mock_history.return_value = []
        
        from services.learning import run_monte_carlo_simulation

        result_low = run_monte_carlo_simulation(1.055, "US-05", 62.0)
        result_high = run_monte_carlo_simulation(1.055, "US-05", 70.0)

        # High mash temp should yield higher FG on average
        assert result_high["predicted_fg_mean"] > result_low["predicted_fg_mean"]

    @patch('services.learning.get_history')
    def test_uses_historical_data_when_available(self, mock_history):
        """When we have >=3 yeast batches, should use their attenuation."""
        mock_history.return_value = [
            {"yeast": "US-05", "success": True, "attenuation": 78},
            {"yeast": "US-05", "success": True, "attenuation": 80},
            {"yeast": "US-05", "success": True, "attenuation": 76},
        ]
        
        from services.learning import run_monte_carlo_simulation
        result = run_monte_carlo_simulation(1.050, "US-05", 65.0)

        # With ~78% avg attenuation, FG should be around 1.011
        assert 1.005 < result["predicted_fg_mean"] < 1.020

    @patch('services.ai.requests.post')
    @patch('services.learning.get_history')
    def test_llm_analysis_is_non_empty_string(self, mock_history, mock_post):
        """The LLM analysis field must be a meaningful string."""
        mock_history.return_value = []
        
        mock_res = MagicMock()
        mock_res.status_code = 200
        mock_res.json.return_value = {"response": "This is a mocked LLM response that is definitely longer than 20 characters."}
        mock_post.return_value = mock_res
        
        from services.learning import run_monte_carlo_simulation
        result = run_monte_carlo_simulation(1.050, "US-05", 65.0)

        assert isinstance(result["llm_analysis"], str)
        assert len(result["llm_analysis"]) > 20


class TestTapService:
    """Tests for services.taps pour_tap volume math."""

    @patch('services.taps.set_config')
    @patch('services.taps.get_config')
    def test_pour_decrements_volume(self, mock_get, mock_set):
        """Pouring 568ml from a full 19L keg should reduce remaining percentage."""
        mock_get.return_value = {
            "tap1": {
                "name": "Test Beer",
                "volume_remaining_ml": 19000.0,
                "keg_volume_l": 19.0,
                "remaining_pct": 100.0
            }
        }

        from services.taps import pour_tap
        result = pour_tap("tap1", 568.0)

        assert result["status"] == "success"
        # 568ml from 19000ml = 18432ml remaining = 97.01%
        assert 96.0 < result["new_remaining_pct"] < 98.0

    @patch('services.taps.set_config')
    @patch('services.taps.get_config')
    def test_pour_cannot_go_below_zero(self, mock_get, mock_set):
        """Pouring from a nearly empty keg should clamp at 0."""
        mock_get.return_value = {
            "tap1": {
                "name": "Test Beer",
                "volume_remaining_ml": 100.0,
                "keg_volume_l": 19.0,
                "remaining_pct": 0.5
            }
        }

        from services.taps import pour_tap
        result = pour_tap("tap1", 568.0)

        assert result["status"] == "success"
        assert result["new_remaining_pct"] == 0.0

    @patch('services.taps.get_config')
    def test_pour_nonexistent_tap_returns_error(self, mock_get):
        """Pouring from a tap that doesn't exist should return an error."""
        mock_get.return_value = {}

        from services.taps import pour_tap
        result = pour_tap("tap99", 568.0)

        assert "error" in result


class TestPydanticConfig:
    """Tests for core.config Pydantic validation."""

    def test_default_config_is_valid(self):
        """Default config should instantiate without errors."""
        from core.config import BrewBrainConfig
        config = BrewBrainConfig()
        assert config.og == 1.050
        assert config.test_mode is False
        assert config.batch_name == "New Batch"

    def test_invalid_date_falls_back_to_today(self):
        """An invalid start_date should be coerced to today's date."""
        from core.config import BrewBrainConfig
        config = BrewBrainConfig(start_date="not-a-date")
        # Should have been reset to today's date format
        from datetime import datetime
        datetime.strptime(config.start_date, "%Y-%m-%d")

    def test_extra_fields_are_rejected(self):
        """Fields not in the schema should be rejected."""
        from core.config import BrewBrainConfig
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            BrewBrainConfig(nonexistent_field="value")

    def test_numeric_bounds(self):
        """OG and FG should accept valid float values."""
        from core.config import BrewBrainConfig
        config = BrewBrainConfig(og=1.080, target_fg=1.015)
        assert config.og == 1.080
        assert config.target_fg == 1.015
