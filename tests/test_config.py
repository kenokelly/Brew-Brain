import os
import json
import unittest
import sys
from unittest.mock import patch, MagicMock

# Mock dependencies before import
sys.modules["influxdb_client"] = MagicMock()
sys.modules["core.influx"] = MagicMock()

from app.core import config

class TestConfig(unittest.TestCase):
    def setUp(self):
        # Use a temporary config file for tests
        self.test_data_dir = "test_data"
        os.makedirs(self.test_data_dir, exist_ok=True)
        config.DATA_DIR = self.test_data_dir
        config.CONFIG_PATH = os.path.join(self.test_data_dir, "config.json")
        if os.path.exists(config.CONFIG_PATH):
            os.remove(config.CONFIG_PATH)
        
        # Reset cache to defaults
        config._config_cache = config.DEFAULTS.copy()

    def tearDown(self):
        # Clean up test data
        if os.path.exists(config.CONFIG_PATH):
            os.remove(config.CONFIG_PATH)
        if os.path.exists(self.test_data_dir):
            os.rmdir(self.test_data_dir)

    def test_get_config_default(self):
        val = config.get_config("og")
        self.assertEqual(val, "1.050")

    def test_set_config_persists_to_file(self):
        with patch("app.core.config.write_api") as mock_write:
            config.set_config("batch_name", "Test Batch")
            
            # Check cache
            self.assertEqual(config.get_config("batch_name"), "Test Batch")
            
            # Check file
            self.assertTrue(os.path.exists(config.CONFIG_PATH))
            with open(config.CONFIG_PATH, "r") as f:
                saved = json.load(f)
                self.assertEqual(saved["batch_name"], "Test Batch")
            
            # Check InfluxDB mirror call
            mock_write.write.assert_called_once()

    def test_load_initial_config_from_file(self):
        # Create a pre-existing config file
        test_config = {"batch_name": "Pre-existing Batch", "target_fg": "1.008"}
        with open(config.CONFIG_PATH, "w") as f:
            json.dump(test_config, f)
            
        config.load_initial_config()
        
        self.assertEqual(config.get_config("batch_name"), "Pre-existing Batch")
        self.assertEqual(config.get_config("target_fg"), "1.008")
        self.assertEqual(config.get_config("og"), "1.050") # Still uses default for others

    @patch("app.core.config.query_api.query")
    def test_load_initial_config_fallback_to_influx(self, mock_query):
        # Ensure no local file
        if os.path.exists(config.CONFIG_PATH):
            os.remove(config.CONFIG_PATH)
            
        # Mock InfluxDB response
        mock_record = MagicMock()
        mock_record.get_field.return_value = "batch_name"
        mock_record.get_value.return_value = "Influx Batch"
        
        mock_table = MagicMock()
        mock_table.records = [mock_record]
        mock_query.return_value = [mock_table]
        
        config.load_initial_config()
        
        self.assertEqual(config.get_config("batch_name"), "Influx Batch")
        # Should have saved to file after fallback
        self.assertTrue(os.path.exists(config.CONFIG_PATH))

if __name__ == "__main__":
    unittest.main()
