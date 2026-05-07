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
    """Get ML predictions for the active batch, serving from cache ONLY."""
    try:
        from core.cache import cache
        cached_predictions = cache.get("ml_predictions")
        if cached_predictions:
            return api_response(data=cached_predictions)
            
        # Return 202 to indicate processing started/pending in background
        return api_response(
            status="accepted", 
            data={"status": "Calculating", "message": "ML model is processing batch data in the background"}, 
            code=202
        )
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
