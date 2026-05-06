import numpy as np
from datetime import datetime, timezone, timedelta
from typing import Tuple, Response
from flask import Blueprint, request
from app.core.config import get_all_config, logger
from app.core.auth import require_api_token
from app.api.routes import api_response, handle_error

ml_bp = Blueprint('ml', __name__)

@ml_bp.route('/api/ml/train', methods=['POST'])
def train_ml_models() -> Tuple[Response, int]:
    """Trigger ML model training."""
    try:
        from app.ml.prediction import train_models
        result = train_models()
        if "error" in result:
            return api_response(status="error", error=result["error"], code=400)
        return api_response(data=result)
    except Exception as e:
        return handle_error(e, "Model Training Error")

@ml_bp.route('/api/ml/models', methods=['GET'])
def get_ml_models_info() -> Tuple[Response, int]:
    """Get status and metrics of trained models."""
    try:
        from app.ml.prediction import get_model_info
        return api_response(data=get_model_info())
    except Exception as e:
        return handle_error(e, "Model Info Error")

@ml_bp.route('/api/ml/predict', methods=['GET'])
def predict_active_batch() -> Tuple[Response, int]:
    """Get ML predictions for the active batch using real-time features."""
    try:
        from app.ml.prediction import predict_fg, predict_time_to_fg
        from app.ml.features import query_batch_data, calculate_sg_velocity, calculate_temp_variance, calculate_time_in_phase
        from app.core.config import get_all_config
        
        # Get active batch metadata from config
        config = get_all_config()
        
        og = float(config.get("og", 1.050))
        pitch_date_str = config.get("start_date")
        if not pitch_date_str:
            return api_response(status="error", error="Active batch missing start date", code=400)
            
        # Parse start_date (YYYY-MM-DD or ISO)
        try:
            if len(pitch_date_str) == 10: # YYYY-MM-DD
                pitch_time = datetime.strptime(pitch_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            else:
                pitch_time = datetime.fromisoformat(pitch_date_str).replace(tzinfo=timezone.utc)
        except Exception:
            pitch_time = datetime.now(timezone.utc) - timedelta(days=7) # Fallback to 7 days ago if invalid
        now = datetime.now(timezone.utc)
        
        # Query sensor data for the active batch duration
        data = query_batch_data(pitch_time, now)
        
        # Calculate current features
        velocity = calculate_sg_velocity(data["sg_readings"], data["sg_times"])
        variance = calculate_temp_variance(data["temp_readings"])
        avg_temp = np.mean(data["temp_readings"]) if data["temp_readings"] else 20.0
        days_elapsed = calculate_time_in_phase(pitch_time, now)
        
        # Get predictions
        prediction_fg = predict_fg(og, velocity, variance, avg_temp)
        prediction_time = predict_time_to_fg(og, velocity, variance, avg_temp, days_elapsed)
        
        return api_response(data={
            "batch_metadata": {
                "og": og,
                "days_elapsed": days_elapsed,
                "data_points": data["data_points"]
            },
            "features": {
                "velocity": velocity,
                "temp_variance": variance,
                "avg_temp": round(float(avg_temp), 1)
            },
            "prediction_fg": prediction_fg,
            "prediction_time": prediction_time
        })
        
    except Exception as e:
        return handle_error(e, "Prediction Error")

@ml_bp.route('/api/ml/peers', methods=['GET'])
def get_style_peers() -> Tuple[Response, int]:
    """Get style benchmarks and peer comparison data for the active batch."""
    try:
        from app.ml.style_intelligence import style_intel
        from app.core.config import get_all_config
        
        config = get_all_config()
        active_style = config.get("style", "IPA")
        
        metrics = style_intel.get_style_neighborhood_metrics(active_style)
        
        if not metrics:
            # Fallback to a generic style if the specific one fails
            metrics = style_intel.get_style_neighborhood_metrics("IPA")
            if not metrics:
                return api_response(status="error", error="No benchmark data found for this style", code=404)
        
        # Add recommendations
        metrics['recommendations'] = style_intel.get_recommendations(active_style)
            
        return api_response(data=metrics)
    except Exception as e:
        return handle_error(e, "Peer Comparison Error")

@ml_bp.route('/api/external-recipes/stats', methods=['GET'])
def external_recipe_stats() -> Tuple[Response, int]:
    """Get external recipe database statistics."""
    try:
        from app.ml.scraper import recipe_count, init_db
        init_db()
        stats = recipe_count()
        return api_response(data=stats)
    except Exception as e:
        return handle_error(e, "External Recipe Stats Error")


@ml_bp.route('/api/external-recipes/ingest', methods=['POST'])
@require_api_token
def external_recipe_ingest() -> Tuple[Response, int]:
    """Trigger on-demand ingestion of public BeerXML recipe sources."""
    try:
        from app.ml.scraper import ingest_all_sources
        result = ingest_all_sources()
        return api_response(data=result)
    except Exception as e:
        return handle_error(e, "External Recipe Ingestion Error")


@ml_bp.route('/api/ml/peer-comparison', methods=['GET'])
def peer_comparison_endpoint() -> Tuple[Response, int]:
    """
    Compare active batch or supplied metrics against the external recipe DB.

    Query params (optional): style, og, fg, abv, ibu
    Falls back to active batch config if not supplied.
    """
    try:
        from ml.peer_comparison import peer_comparison
        from core.config import get_all_config

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
        if request.args.get("ibu"):
            user_recipe["ibu"] = float(request.args["ibu"])

        result = peer_comparison.compare(user_recipe, style)
        return api_response(data=result)
    except Exception as e:
        return handle_error(e, "Peer Comparison Error")
r")
