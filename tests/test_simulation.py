import pytest
from unittest.mock import patch, MagicMock

def test_sim_01_simulate_brew_day_og():
    from app.services.learning import simulate_brew_day
    grains = [{"weight_kg": 5.0, "potential": 1.037}]
    vol = 23
    eff = 75
    result = simulate_brew_day(grains, vol, eff)
    assert "predicted_og" in result
    assert result["predicted_og"] > 1.0

@patch('app.services.learning.get_history')
@patch('app.services.ai.requests.post')
def test_sim_02_predict_fg_monte_carlo(mock_post, mock_history):
    mock_history.return_value = [
        {"yeast": "US-05", "success": True, "attenuation": 80.0}
    ]
    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.json.return_value = {"response": "Mocked AI advice"}
    mock_post.return_value = mock_res
    
    from app.services.learning import run_monte_carlo_simulation
    result = run_monte_carlo_simulation(1.050, "US-05", 65.0)
    assert "predicted_fg_mean" in result
    assert result["llm_analysis"] == "Mocked AI advice"

def test_run_simulation_task_success():
    from app.services.tasks import run_simulation_task
    with patch("app.services.learning.get_history") as mock_history, \
         patch("services.ai.requests.post") as mock_post:
         
        mock_history.return_value = [
            {"yeast": "US-05", "success": True, "attenuation": 80.0},
            {"yeast": "US-05", "success": True, "attenuation": 81.0},
        ]
        
        mock_res = MagicMock()
        mock_res.status_code = 200
        mock_res.json.return_value = {"response": "Mock LLM Warning"}
        mock_post.return_value = mock_res
        
        task_result = run_simulation_task.apply(kwargs={"target_og": 1.065, "yeast_name": "US-05", "mash_temp_c": 65.0})
        result = task_result.result
        assert result["status"] == "success"
        data = result["data"]
        assert "predicted_fg_mean" in data
        assert "predicted_fg_p5" in data
        assert "predicted_fg_p95" in data
        assert "distribution_bins" in data
        assert data["llm_analysis"] == "Mock LLM Warning"
