import numpy as np
from datetime import datetime, timezone, timedelta
from typing import Tuple
from flask import Response
from flask import Blueprint, request
from core.config import get_all_config, logger
from core.auth import require_api_token
from api.routes import api_response, handle_error

ml_bp = Blueprint('ml', __name__)

@ml_bp.route('/train', methods=['POST'])
def train_ml_models() -> Tuple[Response, int]:
    """Trigger ML model training."""
    try:
        from ml.tasks import train_prediction_models
        task = train_prediction_models.delay()
        return api_response(data={"status": "Task Queued", "task_id": task.id})
    except Exception as e:
        return handle_error(e, "Model Training Error")

@ml_bp.route('/models', methods=['GET'])
def get_ml_models_info() -> Tuple[Response, int]:
    """Get status and metrics of trained models."""
    try:
        from ml.prediction import get_model_info
        return api_response(data=get_model_info())
    except Exception as e:
        return handle_error(e, "Model Info Error")

@ml_bp.route('/predict', methods=['GET'])
def predict_active_batch() -> Tuple[Response, int]:
    """Get ML predictions for the active batch using real-time features."""
    try:
        from ml.prediction import predict_fg, predict_time_to_fg
        from ml.features import query_batch_data, calculate_sg_velocity, calculate_temp_variance, calculate_time_in_phase
        from core.config import get_all_config
        
        config = get_all_config()
        og = float(config.get("og", 1.050))
        pitch_date_str = config.get("start_date")
        if not pitch_date_str:
            return api_response(status="error", error="Active batch missing start date", code=400)
            
        try:
            if len(pitch_date_str) == 10:
                pitch_time = datetime.strptime(pitch_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            else:
                pitch_time = datetime.fromisoformat(pitch_date_str).replace(tzinfo=timezone.utc)
        except Exception:
            pitch_time = datetime.now(timezone.utc) - timedelta(days=7)
        
        now = datetime.now(timezone.utc)
        data = query_batch_data(pitch_time, now)
        velocity = calculate_sg_velocity(data["sg_readings"], data["sg_times"])
        variance = calculate_temp_variance(data["temp_readings"])
        avg_temp = np.mean(data["temp_readings"]) if data["temp_readings"] else 20.0
        days_elapsed = calculate_time_in_phase(pitch_time, now)
        
        style = config.get("style", "Unknown")
        yeast = config.get("yeast_strain", "Unknown")
        
        prediction_fg = predict_fg(og, velocity, variance, avg_temp, style, yeast)
        prediction_time = predict_time_to_fg(og, velocity, variance, avg_temp, days_elapsed, style, yeast)
        
        return api_response(data={
            "batch_metadata": {"og": og, "days_elapsed": days_elapsed, "data_points": data["data_points"], "style": style, "yeast": yeast},
            "features": {"velocity": velocity, "temp_variance": variance, "avg_temp": round(float(avg_temp), 1)},
            "prediction_fg": prediction_fg,
            "prediction_time": prediction_time
        })
    except Exception as e:
        return handle_error(e, "Prediction Error")

@ml_bp.route('/peers', methods=['GET'])
def get_style_peers() -> Tuple[Response, int]:
    """Get style benchmarks and peer comparison data for the active batch."""
    try:
        from ml.style_intelligence import style_intel
        config = get_all_config()
        active_style = config.get("style", "IPA")
        metrics = style_intel.get_style_neighborhood_metrics(active_style)
        if not metrics:
            metrics = style_intel.get_style_neighborhood_metrics("IPA")
            if not metrics:
                return api_response(status="error", error="No benchmark data", code=404)
        metrics['recommendations'] = style_intel.get_recommendations(active_style)
        return api_response(data=metrics)
    except Exception as e:
        return handle_error(e, "Peer Comparison Error")

@ml_bp.route('/external-recipes/stats', methods=['GET'])
def external_recipe_stats() -> Tuple[Response, int]:
    try:
        from ml.scraper import recipe_count, init_db
        init_db()
        return api_response(data=recipe_count())
    except Exception as e:
        return handle_error(e, "External Recipe Stats Error")

@ml_bp.route('/peer-comparison', methods=['GET'])
def peer_comparison_endpoint() -> Tuple[Response, int]:
    try:
        from ml.peer_comparison import peer_comparison
        config = get_all_config()
        style = request.args.get("style") or config.get("style", "IPA")
        user_recipe = {
            "og": float(request.args.get("og") or config.get("og") or 1.050),
            "fg": float(request.args.get("fg") or config.get("target_fg") or 1.010),
        }
        if request.args.get("abv"):
            user_recipe["abv"] = float(request.args["abv"])
        else:
            user_recipe["abv"] = round((user_recipe["og"] - user_recipe["fg"]) * 131.25, 1)
        
        result = peer_comparison.compare(user_recipe, style)
        return api_response(data=result)
    except Exception as e:
        return handle_error(e, "Peer Comparison Error")
