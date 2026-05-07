import pytest
from unittest.mock import patch, MagicMock
import sys
import contextlib

# To avoid polluting sys.modules globally and breaking other tests, we only mock what is necessary,
# and ideally we'd do it carefully or only run the tests in an environment that has these installed.
# The memory explicitly mentions:
# "The development environment has no internet access, preventing the use of `pip install`. Missing dependencies (like numpy, scipy, and pytest) must be mocked in test files (e.g., using `sys.modules`) to facilitate local test execution for logic that does not strictly require them at runtime."
# We need to do this mock but clean it up or make sure it doesn't break other files. However,
# for tests running isolated or as directed, this is acceptable. To follow the review, we can
# use a fixture or manage sys.modules more carefully, or rely on the memory instruction.
# Since the review block us for global mutation, let's restore sys.modules if they weren't there, or just use patch.dict.

@contextlib.contextmanager
def mock_dependencies():
    missing_deps = [
        'requests', 'pyarrow', 'pyarrow.parquet', 'influxdb_client',
        'influxdb_client.client', 'influxdb_client.client.write_api',
        'numpy', 'scipy', 'scipy.signal', 'sklearn', 'sklearn.ensemble', 'joblib'
    ]

    saved_modules = {}
    for dep in missing_deps:
        if dep in sys.modules:
            saved_modules[dep] = sys.modules[dep]
        else:
            saved_modules[dep] = None
        sys.modules[dep] = MagicMock()

    try:
        yield
    finally:
        for dep, module in saved_modules.items():
            if module is None:
                del sys.modules[dep]
            else:
                sys.modules[dep] = module

with mock_dependencies():
    from services.batch_exporter import get_completed_batches

@patch('services.batch_exporter.get_config')
def test_get_completed_batches_no_creds(mock_get_config):
    # Setup mock to return None
    mock_get_config.return_value = None

    result = get_completed_batches()

    assert result == []
    # get_config is called for "bf_user" and "bf_key", if the first returns None, the second might not be called, but we don't strictly enforce count.

@patch('services.batch_exporter.requests.get')
@patch('services.batch_exporter.get_config')
def test_get_completed_batches_success(mock_get_config, mock_requests_get):
    # Setup mocks
    mock_get_config.side_effect = lambda key: "dummy" if key in ["bf_user", "bf_key"] else None

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [{"id": "batch1", "status": "Completed"}]
    mock_requests_get.return_value = mock_response

    result = get_completed_batches()

    assert result == [{"id": "batch1", "status": "Completed"}]
    mock_requests_get.assert_called_once()

@patch('services.batch_exporter.requests.get')
@patch('services.batch_exporter.get_config')
def test_get_completed_batches_api_error(mock_get_config, mock_requests_get):
    # Setup mocks
    mock_get_config.side_effect = lambda key: "dummy" if key in ["bf_user", "bf_key"] else None

    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_requests_get.return_value = mock_response

    result = get_completed_batches()

    assert result == []
    mock_requests_get.assert_called_once()

@patch('services.batch_exporter.requests.get')
@patch('services.batch_exporter.get_config')
def test_get_completed_batches_exception(mock_get_config, mock_requests_get):
    # Setup mocks
    mock_get_config.side_effect = lambda key: "dummy" if key in ["bf_user", "bf_key"] else None
    mock_requests_get.side_effect = Exception("Network Error")

    result = get_completed_batches()

    assert result == []
    mock_requests_get.assert_called_once()
