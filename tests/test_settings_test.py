import sys
import os
import pytest
from unittest.mock import patch, MagicMock
import requests

# Ensure app is in path
app_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../app'))
if app_dir not in sys.path:
    sys.path.insert(0, app_dir)

# Save original sys.modules keys/values to restore later
_original_modules = {}
_keys_to_remove = []
for key in ["influxdb_client", "influxdb_client.client", "influxdb_client.client.write_api", "core.influx", "services.tilt_monitor"]:
    if key in sys.modules:
        _original_modules[key] = sys.modules[key]
    else:
        _keys_to_remove.append(key)

# Mock dependencies before import to avoid real connections/failures
sys.modules["influxdb_client"] = MagicMock()
sys.modules["influxdb_client.client"] = MagicMock()
sys.modules["influxdb_client.client.write_api"] = MagicMock()
sys.modules['core.influx'] = MagicMock()
sys.modules['services.tilt_monitor'] = MagicMock()

# Import core.auth first so that resolving core.auth.API_TOKEN works
import core.auth
core.auth.API_TOKEN = 'test_secret_token'

from flask import Flask
from api.settings import settings_bp

# Restore original modules to prevent side-effects on other test files
for key, val in _original_modules.items():
    sys.modules[key] = val
for key in _keys_to_remove:
    if key in sys.modules:
        del sys.modules[key]

@pytest.fixture
def client():
    with patch.dict(sys.modules, {
        "influxdb_client": MagicMock(),
        "influxdb_client.client": MagicMock(),
        "influxdb_client.client.write_api": MagicMock(),
        "core.influx": MagicMock(),
        "services.tilt_monitor": MagicMock()
    }):
        app = Flask(__name__)
        app.register_blueprint(settings_bp, url_prefix='/api')
        # Set the test auth token
        core.auth.API_TOKEN = 'test_secret_token'
        with app.test_client() as client:
            yield client

def test_require_api_token_failure(client):
    """Test that unauthorized requests are rejected."""
    res = client.post('/api/settings/test', json={"integration": "telegram"})
    assert res.status_code == 401
    assert res.get_json()["status"] == "error"

@patch('requests.post')
def test_test_telegram_success(mock_post, client):
    """Test successful Telegram connection check."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_post.return_value = mock_response

    payload = {
        "integration": "telegram",
        "config": {
            "alert_telegram_token": "123456:ABC-DEF",
            "alert_telegram_chat": "987654"
        }
    }
    headers = {"Authorization": "Bearer test_secret_token"}
    res = client.post('/api/settings/test', json=payload, headers=headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert "Test message sent to 987654" in data["message"]

@patch('requests.post')
def test_test_telegram_failure(mock_post, client):
    """Test Telegram connection check failure response."""
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text = "Bad Request"
    mock_post.return_value = mock_response

    payload = {
        "integration": "telegram",
        "config": {
            "alert_telegram_token": "123456:ABC-DEF",
            "alert_telegram_chat": "987654"
        }
    }
    headers = {"Authorization": "Bearer test_secret_token"}
    res = client.post('/api/settings/test', json=payload, headers=headers)
    assert res.status_code == 400
    data = res.get_json()
    assert data["status"] == "error"
    assert "Telegram Error (400)" in data["error"]

@patch('requests.post')
@patch('core.config.get_config')
def test_test_telegram_masked(mock_get_config, mock_post, client):
    """Test Telegram connection check when credentials are masked."""
    mock_get_config.return_value = "actual_real_token"
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_post.return_value = mock_response

    payload = {
        "integration": "telegram",
        "config": {
            "alert_telegram_token": "********",
            "alert_telegram_chat": "987654"
        }
    }
    headers = {"Authorization": "Bearer test_secret_token"}
    res = client.post('/api/settings/test', json=payload, headers=headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    mock_get_config.assert_any_call("alert_telegram_token")
    mock_post.assert_called_once_with(
        "https://api.telegram.org/botactual_real_token/sendMessage",
        json={"chat_id": "987654", "text": "🧪 *Brew Brain Test*\nConnection successful!", "parse_mode": "Markdown"},
        timeout=5
    )

@patch('requests.get')
def test_test_brewfather_success(mock_get, client):
    """Test successful Brewfather connection check."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_get.return_value = mock_response

    payload = {
        "integration": "brewfather",
        "config": {
            "bf_user": "user123",
            "bf_key": "key123"
        }
    }
    headers = {"Authorization": "Bearer test_secret_token"}
    res = client.post('/api/settings/test', json=payload, headers=headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert "authenticated successfully" in data["message"]

@patch('requests.get')
@patch('core.config.get_config')
def test_test_brewfather_masked(mock_get_config, mock_get, client):
    """Test Brewfather connection check when API key is masked."""
    mock_get_config.return_value = "actual_real_key"
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_get.return_value = mock_response

    payload = {
        "integration": "brewfather",
        "config": {
            "bf_user": "user123",
            "bf_key": "********"
        }
    }
    headers = {"Authorization": "Bearer test_secret_token"}
    res = client.post('/api/settings/test', json=payload, headers=headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    mock_get_config.assert_any_call("bf_key")
    
    import base64
    expected_auth = base64.b64encode(b"user123:actual_real_key").decode()
    mock_get.assert_called_once_with(
        "https://api.brewfather.app/v2/batches?limit=1",
        headers={"Authorization": f"Basic {expected_auth}"},
        timeout=5
    )

@patch('requests.get')
def test_test_serpapi_success(mock_get, client):
    """Test successful SerpApi connection check."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_get.return_value = mock_response

    payload = {
        "integration": "serpapi",
        "config": {
            "serp_api_key": "serp_key"
        }
    }
    headers = {"Authorization": "Bearer test_secret_token"}
    res = client.post('/api/settings/test', json=payload, headers=headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert "authenticated successfully" in data["message"]

@patch('requests.get')
def test_test_ollama_success(mock_get, client):
    """Test successful Ollama connection check."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "models": [{"name": "llama3:latest"}]
    }
    mock_get.return_value = mock_response

    payload = {
        "integration": "ollama",
        "config": {
            "ollama_host": "http://ollama:11434",
            "ollama_model": "llama3"
        }
    }
    headers = {"Authorization": "Bearer test_secret_token"}
    res = client.post('/api/settings/test', json=payload, headers=headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert "Ollama connected. Model 'llama3' is installed and ready." in data["message"]

@patch('requests.get')
def test_test_ollama_missing_model(mock_get, client):
    """Test Ollama connection check where the model is missing."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "models": [{"name": "phi3:latest"}]
    }
    mock_get.return_value = mock_response

    payload = {
        "integration": "ollama",
        "config": {
            "ollama_host": "http://ollama:11434",
            "ollama_model": "llama3"
        }
    }
    headers = {"Authorization": "Bearer test_secret_token"}
    res = client.post('/api/settings/test', json=payload, headers=headers)
    assert res.status_code == 400
    data = res.get_json()
    assert data["status"] == "error"
    assert "model 'llama3' not found" in data["error"]
