import pytest
import numpy as np
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

# Mock dependencies before importing worker
import sys
from types import ModuleType

# Create mock modules for core.config and core.influx
core = ModuleType('core')
sys.modules['core'] = core
core.config = ModuleType('core.config')
sys.modules['core.config'] = core.config
core.influx = ModuleType('core.influx')
sys.modules['core.influx'] = core.influx

# Add dummy functions/constants
core.config.get_config = MagicMock(return_value=None)
core.config.set_config = MagicMock()
core.config.logger = MagicMock()
core.influx.write_api = MagicMock()
core.influx.query_api = MagicMock()
core.influx.INFLUX_BUCKET = "test_bucket"
core.influx.INFLUX_ORG = "test_org"

# Mock services
services = ModuleType('services')
sys.modules['services'] = services
services.telegram = MagicMock()
sys.modules['services.telegram'] = services.telegram
services.ai = MagicMock()
sys.modules['services.ai'] = services.ai
services.tilt_monitor = MagicMock()
sys.modules['services.tilt_monitor'] = services.tilt_monitor
services.notifications = MagicMock()
sys.modules['services.notifications'] = services.notifications
services.status = MagicMock()
sys.modules['services.status'] = services.status
services.cache = MagicMock()
sys.modules['services.cache'] = services.cache
services.core = MagicMock()
sys.modules['services.core'] = services.core

from app.services.worker import predict_fg_from_curve
from app.services.learning import predict_fg_4pl

def test_predict_fg_from_curve_empty_after_clean():
    """
    Test that predict_fg_from_curve returns (None, None) gracefully 
    if clean_data is empty (though len(clean_data) < 50 should catch it first).
    """
    times = [datetime.now(timezone.utc)] * 60
    # All readings outside [0.900, 1.200]
    readings = [0.5] * 60
    
    # This should hit the 'if len(clean_data) < 50' guard
    fg, date = predict_fg_from_curve(times, readings)
    assert fg is None
    assert date is None

def test_predict_fg_from_curve_empty_guards():
    """
    Force an empty y_data_smooth to verify the new guard clause.
    """
    # We bypass the initial guards by providing 50 valid points, 
    # but we'll mock medfilt to return an empty array if possible, 
    # or just trust the code logic.
    
    # Actually, with the guard I added:
    # if len(y_data_smooth) == 0: return None, None
    
    with patch('app.services.worker.medfilt', return_value=np.array([])):
        times = [datetime.now(timezone.utc)] * 51
        readings = [1.050] * 51
        fg, date = predict_fg_from_curve(times, readings)
        assert fg is None
        assert date is None

def test_predict_fg_4pl_empty_guards():
    """
    Test the guard in learning.py
    """
    with patch('app.services.learning.medfilt', return_value=np.array([])):
        times = [datetime.now(timezone.utc)] * 21
        readings = [1.050] * 21
        result = predict_fg_4pl(times, readings)
        assert result["predicted_fg"] is None
        assert result["error"] == "Empty smoothed data"
