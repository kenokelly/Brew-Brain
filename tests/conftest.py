import pytest
from unittest.mock import MagicMock, patch

@pytest.fixture
def mock_write_api():
    """Mock the InfluxDB WriteAPI."""
    with patch('app.core.influx.write_api') as mock:
        yield mock

@pytest.fixture
def mock_query_api():
    """Mock the InfluxDB QueryAPI."""
    with patch('app.core.influx.query_api') as mock:
        yield mock

@pytest.fixture
def mock_config():
    """Mock config getters/setters."""
    with patch.dict('app.core.config._config_cache', {
        'batch_name': 'Test Batch',
        'og': '1.050',
        'target_fg': '1.010',
        'test_mode': 'true',
        'alert_telegram_token': 'dummy_token',
        'alert_telegram_chat': 'dummy_chat'
    }) as mock_dict:
        yield mock_dict

@pytest.fixture
def mock_brewfather():
    """Mock Brewfather API calls."""
    with patch('app.services.alerts.fetch_batch_readings') as mock:
        mock.return_value = []
        yield mock
