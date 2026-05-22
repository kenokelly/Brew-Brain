import pytest
from unittest.mock import patch, MagicMock
from app.services.inventory import fetch_inventory_with_backoff, get_processed_inventory

@pytest.fixture
def mock_cache():
    with patch('app.services.inventory.cache') as mock:
        yield mock

@pytest.fixture
def mock_alerts():
    with patch('app.services.inventory.alerts') as mock:
        yield mock

def test_fetch_inventory_with_backoff_success(mock_alerts, mock_cache):
    # Mock a successful Brewfather response
    mock_alerts.fetch_brewfather_inventory.return_value = {
        "hops": {"Citra": 250},
        "fermentables": {"Pale Ale Malt": 5.0}
    }
    
    # Use apply() to run the task synchronously in the current process
    task_result = fetch_inventory_with_backoff.apply(kwargs={"base_delay": 0})
    result = task_result.result
    
    assert result["status"] == "success"
    mock_cache.set.assert_called_once()
    args, kwargs = mock_cache.set.call_args
    assert args[0] == "raw_inventory"
    assert "Citra" in args[1]["hops"]

def test_fetch_inventory_with_backoff_429_retry(mock_alerts, mock_cache):
    # Mock a 429 error
    mock_alerts.fetch_brewfather_inventory.return_value = {"error": "HTTP 429 Too Many Requests"}
    
    # apply() will perform retries synchronously until max_retries is hit,
    # then raise MaxRetriesExceededError which is caught by except Exception
    task_result = fetch_inventory_with_backoff.apply(kwargs={"base_delay": 0})
    
    assert task_result.state == "SUCCESS"
    assert "error" in task_result.result
    assert "Can't retry" in task_result.result["error"]
    mock_cache.set.assert_not_called()

def test_get_processed_inventory_low_stock(mock_cache):
    # Mock the cache returning raw inventory
    mock_cache.get.return_value = {
        "hops": {"Citra": 50}, # Less than 100g -> low stock
        "fermentables": {"Pale Ale Malt": 3.0}, # Less than 5kg -> low stock
        "yeast": {"US-05": 1} # Less than 2 pkgs -> low stock
    }
    
    with patch('app.services.inventory.calculate_hop_freshness') as mock_freshness:
        mock_freshness.return_value = {
            "current_alpha": 8.0,
            "alpha_loss_pct": 20.0,
            "freshness": "Average"
        }
        
        result = get_processed_inventory()
        
        # Check Hops
        assert len(result["hops"]) == 1
        assert result["hops"][0]["name"] == "Citra"
        assert result["hops"][0]["low_stock_alert"] is True
        assert result["hops"][0]["current_alpha"] == 8.0
        
        # Check Fermentables
        assert len(result["fermentables"]) == 1
        assert result["fermentables"][0]["name"] == "Pale Ale Malt"
        assert result["fermentables"][0]["low_stock_alert"] is True
        
        # Check Yeast
        assert len(result["yeast"]) == 1
        assert result["yeast"][0]["name"] == "Us-05"
        assert result["yeast"][0]["low_stock_alert"] is True
