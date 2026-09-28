import os
os.environ["INFLUX_TOKEN"] = "mock"
import pytest
from unittest.mock import MagicMock, patch

@pytest.fixture(autouse=True)
def isolated_journal(tmp_path, monkeypatch):
    """Every alert path writes to the autopilot journal; keep test runs out
    of the real data/journal.json."""
    monkeypatch.setenv("BREW_BRAIN_JOURNAL_DIR", str(tmp_path))
    yield tmp_path

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
