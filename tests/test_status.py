import sys
from unittest.mock import MagicMock

sys.modules['influxdb_client'] = MagicMock()
sys.modules['influxdb_client.client'] = MagicMock()
sys.modules['influxdb_client.client.write_api'] = MagicMock()

import pytest
from unittest.mock import patch, mock_open
from services.status import get_pi_temp

def test_get_pi_temp_success():
    m = mock_open(read_data="45678")
    with patch("builtins.open", m):
        temp = get_pi_temp()
    assert temp == 45.7

def test_get_pi_temp_file_not_found():
    with patch("builtins.open", side_effect=FileNotFoundError):
        temp = get_pi_temp()
    assert temp == 0.0

def test_get_pi_temp_os_error():
    with patch("builtins.open", side_effect=OSError):
        temp = get_pi_temp()
    assert temp == 0.0

def test_get_pi_temp_value_error():
    m = mock_open(read_data="invalid")
    with patch("builtins.open", m):
        with pytest.raises(ValueError):
            get_pi_temp()
