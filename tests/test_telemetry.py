import sys
import os
from unittest.mock import MagicMock, patch

# Set PYTHONPATH within Python to handle standard imports inside app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../app'))

def test_format_diff():
    # Mock missing dependencies only for the context of this test file to avoid global test pollution
    mock_modules = {
        "influxdb_client": MagicMock(),
        "influxdb_client.client": MagicMock(),
        "influxdb_client.client.write_api": MagicMock(),
        "scipy": MagicMock(),
        "scipy.stats": MagicMock(),
        "requests": MagicMock(),
        "numpy": MagicMock()
    }

    with patch.dict(sys.modules, mock_modules):
        from app.services.telemetry import format_diff

        # Positive values
        assert format_diff(0.005) == "-0.005"
        assert format_diff(1.234) == "-1.234"

        # Negative values
        assert format_diff(-0.005) == "+0.005"
        assert format_diff(-1.234) == "+1.234"

        # Zero
        assert format_diff(0) == "0.000"
        assert format_diff(0.0) == "0.000"
        assert format_diff(-0.0) == "0.000"

        # Edge cases
        assert format_diff(1e-10) == "-0.000"
        assert format_diff(-1e-10) == "+0.000"
        assert format_diff(0.0001) == "-0.000"
        assert format_diff(-0.0001) == "+0.000"
