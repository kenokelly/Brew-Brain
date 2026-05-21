import os
import json
import unittest
import sys
from unittest.mock import patch, MagicMock

# 1. Import the module directly
from app.core import config

class TestConfig(unittest.TestCase):
    def setUp(self):
        # Use a temporary config file for tests
        self.test_data_dir = os.path.abspath("test_data_config")
        os.makedirs(self.test_data_dir, exist_ok=True)
        config.DATA_DIR = self.test_data_dir
        config.CONFIG_PATH = os.path.join(self.test_data_dir, "config.json")
        if os.path.exists(config.CONFIG_PATH):
            os.remove(config.CONFIG_PATH)
        
        # Reset cache to defaults
        config._config_instance = config.BrewBrainConfig()

    def tearDown(self):
        # Clean up test data
        if os.path.exists(config.CONFIG_PATH):
            os.remove(config.CONFIG_PATH)
        if os.path.exists(self.test_data_dir):
            try:
                os.rmdir(self.test_data_dir)
            except OSError:
                pass

    def test_get_config_default(self):
        val = config.get_config("og")
        self.assertEqual(val, 1.050)

    def test_set_config_persists_to_file(self):
        # Mock write_api which is imported from core.influx
        with patch("app.core.config.write_api") as mock_write:
            config.set_config("batch_name", "Test Batch Persistence")
            
            # Check cache
            self.assertEqual(config.get_config("batch_name"), "Test Batch Persistence")
            
            # Check file
            self.assertTrue(os.path.exists(config.CONFIG_PATH))
            with open(config.CONFIG_PATH, "r") as f:
                saved = json.load(f)
                self.assertEqual(saved["batch_name"], "Test Batch Persistence")

    def test_coercion(self):
        with patch("app.core.config.write_api") as mock_write:
            # String None coercion
            config.set_config("batch_notes", None)
            self.assertEqual(config.get_config("batch_notes"), "")
            
            # String values on numeric fields
            config.set_config("temp_max", "22.5")
            self.assertEqual(config.get_config("temp_max"), 22.5)
            
            config.set_config("tilt_timeout_min", "120")
            self.assertEqual(config.get_config("tilt_timeout_min"), 120)
            
            # Empty string fallback on float/int
            config.set_config("temp_max", "")
            self.assertEqual(config.get_config("temp_max"), 28.0) # default fallback
            
            config.set_config("tilt_timeout_min", "")
            self.assertEqual(config.get_config("tilt_timeout_min"), 60) # default fallback
            
            # Boolean string coercion
            config.set_config("test_mode", "true")
            self.assertTrue(config.get_config("test_mode"))
            
            config.set_config("test_mode", "false")
            self.assertFalse(config.get_config("test_mode"))

    def test_load_initial_config_from_file(self):
        # Create a pre-existing config file
        test_config = {"batch_name": "Pre-existing Batch", "target_fg": 1.008}
        with open(config.CONFIG_PATH, "w") as f:
            json.dump(test_config, f)
            
        config.load_initial_config()
        
        self.assertEqual(config.get_config("batch_name"), "Pre-existing Batch")
        self.assertEqual(config.get_config("target_fg"), 1.008)

    def test_load_initial_config_fallback_to_influx(self):
        # Ensure no local file
        if os.path.exists(config.CONFIG_PATH):
            os.remove(config.CONFIG_PATH)
            
        # Mock InfluxDB response via the query_api that config.py imports
        with patch("app.core.config.query_api") as mock_query_api:
            mock_record = MagicMock()
            mock_record.get_field.return_value = "batch_name"
            mock_record.get_value.return_value = "Influx Batch"
            
            mock_table = MagicMock()
            mock_table.records = [mock_record]
            mock_query_api.query.return_value = [mock_table]
            
            config.load_initial_config()
            
            self.assertEqual(config.get_config("batch_name"), "Influx Batch")
            # Should have saved to file after fallback
            self.assertTrue(os.path.exists(config.CONFIG_PATH))

if __name__ == "__main__":
    unittest.main()
