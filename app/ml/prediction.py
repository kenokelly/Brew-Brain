"""
FG Prediction Model for Brew Brain

Trains and serves XGBoost models for:
- Final Gravity prediction
- Time-to-FG prediction

Uses historical batch data from Brewfather + InfluxDB.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Optional, List, Any
import joblib

logger = logging.getLogger(__name__)

MODEL_DIR = "data/models"
FG_MODEL_PATH = os.path.join(MODEL_DIR, "fg_predictor.joblib")
TIME_MODEL_PATH = os.path.join(MODEL_DIR, "time_predictor.joblib")
HISTORY_FILE = "data/brew_history.json"


def ensure_model_dir():
    """Create model directory if it doesn't exist."""
    os.makedirs(MODEL_DIR, exist_ok=True)


def load_training_data() -> List[Dict]:
    """Load historical batch data for training."""
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load history: {e}")
        return []


def prepare_features(batches: List[Dict]) -> tuple:
    """
    Extract features and targets from batch history.
    
    Features: OG, yeast_attenuation_pct, avg_temp
    Targets: FG, days_to_fg
    """
    X = []  # Features
    y_fg = []  # FG targets
    y_time = []  # Time targets
    
    for batch in batches:
        try:
            og = batch.get('og')
            fg = batch.get('fg')
            att = batch.get('attenuation')
            
            if og and fg and att:
                # Feature vector
                features = [
                    float(og),
                    float(att),
                    float(batch.get('avg_temp', 20.0)),
                ]
                X.append(features)
                y_fg.append(float(fg))
                
                # Time target (days_to_fg if available, else estimate from style)
                days = batch.get('days_to_fg', 7.0)  # Default 7 days
                y_time.append(float(days))
                
        except (ValueError, TypeError) as e:
            logger.debug(f"Skipping batch: {e}")
            continue
    
    return X, y_fg, y_time


def train_models() -> Dict[str, Any]:
    """
    Train FG and time-to-FG prediction models.
    
    Returns dict with training metrics.
    """
    try:
        from sklearn.ensemble import GradientBoostingRegressor
        from sklearn.model_selection import cross_val_score
        import numpy as np
    except ImportError:
        return {"error": "sklearn not installed. Run: pip install scikit-learn"}
    
    ensure_model_dir()
    
    # Load data
    batches = load_training_data()
    if len(batches) < 5:
        return {"error": f"Need at least 5 batches, got {len(batches)}"}
    
    X, y_fg, y_time = prepare_features(batches)
    
    if len(X) < 5:
        return {"error": f"Only {len(X)} valid batches after filtering"}
    
    X = np.array(X)
    y_fg = np.array(y_fg)
    y_time = np.array(y_time)
    
    # Train FG model
    fg_model = GradientBoostingRegressor(
        n_estimators=50,
        max_depth=3,
        learning_rate=0.1,
        random_state=42
    )
    fg_model.fit(X, y_fg)
    
    # Cross-validation score
    fg_cv = cross_val_score(fg_model, X, y_fg, cv=min(3, len(X)), scoring='neg_mean_absolute_error')
    fg_mae = -fg_cv.mean()
    
    # Train time model
    time_model = GradientBoostingRegressor(
        n_estimators=50,
        max_depth=3,
        learning_rate=0.1,
        random_state=42
    )
    time_model.fit(X, y_time)
    time_cv = cross_val_score(time_model, X, y_time, cv=min(3, len(X)), scoring='neg_mean_absolute_error')
    time_mae = -time_cv.mean()
    
    # Save models
    joblib.dump(fg_model, FG_MODEL_PATH)
    joblib.dump(time_model, TIME_MODEL_PATH)
    
    logger.info(f"Models trained on {len(X)} batches. FG MAE: {fg_mae:.4f}, Time MAE: {time_mae:.1f} days")
    
    return {
        "status": "success",
        "batches_used": len(X),
        "fg_model": {
            "path": FG_MODEL_PATH,
            "mae": round(fg_mae, 4)
        },
        "time_model": {
            "path": TIME_MODEL_PATH,
            "mae": round(time_mae, 2)
        },
        "trained_at": datetime.now().isoformat()
    }


def predict_fg(og: float, attenuation: float, avg_temp: float = 20.0) -> Dict[str, Any]:
    """
    Predict Final Gravity for a batch.
    
    Args:
        og: Original Gravity (e.g., 1.055)
        attenuation: Expected yeast attenuation % (e.g., 78.0)
        avg_temp: Average fermentation temp in °C
        
    Returns:
        Dict with predicted_fg, predicted_abv, confidence
    """
    import numpy as np
    
    # Check if model exists
    if not os.path.exists(FG_MODEL_PATH):
        # Fallback to simple calculation
        predicted_fg = og - ((attenuation / 100.0) * (og - 1.0))
        return {
            "predicted_fg": round(predicted_fg, 3),
            "predicted_abv": round((og - predicted_fg) * 131.25, 1),
            "method": "formula",
            "confidence": "low"
        }
    
    try:
        model = joblib.load(FG_MODEL_PATH)
        features = np.array([[og, attenuation, avg_temp]])
        predicted_fg = model.predict(features)[0]
        
        # Sanity bounds
        predicted_fg = max(0.990, min(predicted_fg, og - 0.005))
        
        return {
            "predicted_fg": round(predicted_fg, 3),
            "predicted_abv": round((og - predicted_fg) * 131.25, 1),
            "method": "ml_model",
            "confidence": "high"
        }
    except Exception as e:
        logger.error(f"FG prediction failed: {e}")
        return {"error": str(e)}


def predict_time_to_fg(og: float, current_sg: float, attenuation: float, days_elapsed: float = 0) -> Dict[str, Any]:
    """
    Predict days remaining until Final Gravity is reached.
    
    Args:
        og: Original Gravity
        current_sg: Current Specific Gravity
        attenuation: Expected yeast attenuation %
        days_elapsed: Days since pitch
        
    Returns:
        Dict with days_remaining, estimated_completion
    """
    import numpy as np
    
    if not os.path.exists(TIME_MODEL_PATH):
        # Fallback: estimate based on current progress
        if og <= 1.0 or current_sg <= 1.0:
            return {"error": "Invalid gravity values"}
            
        predicted_fg = og - ((attenuation / 100.0) * (og - 1.0))
        total_drop = og - predicted_fg
        current_drop = og - current_sg
        
        if total_drop <= 0:
            return {"days_remaining": 0, "method": "formula"}
            
        progress = current_drop / total_drop
        
        # Assume 7 days total for typical fermentation
        if progress >= 0.95:
            days_remaining = 1
        elif days_elapsed > 0 and progress > 0:
            # Extrapolate from current speed
            days_remaining = max(1, int((1 - progress) / (progress / days_elapsed)))
        else:
            days_remaining = 7
            
        return {
            "days_remaining": days_remaining,
            "progress_pct": round(progress * 100, 1),
            "method": "formula",
            "confidence": "low"
        }
    
    try:
        model = joblib.load(TIME_MODEL_PATH)
        features = np.array([[og, attenuation, 20.0]])  # Use default temp
        total_days = model.predict(features)[0]
        days_remaining = max(0, total_days - days_elapsed)
        
        return {
            "days_remaining": round(days_remaining, 1),
            "total_estimated_days": round(total_days, 1),
            "method": "ml_model",
            "confidence": "high"
        }
    except Exception as e:
        logger.error(f"Time prediction failed: {e}")
        return {"error": str(e)}


def get_model_info() -> Dict[str, Any]:
    """Get information about trained models."""
    info = {
        "fg_model": {"exists": os.path.exists(FG_MODEL_PATH)},
        "time_model": {"exists": os.path.exists(TIME_MODEL_PATH)},
        "training_data_count": len(load_training_data())
    }
    
    if info["fg_model"]["exists"]:
        stat = os.stat(FG_MODEL_PATH)
        info["fg_model"]["size_kb"] = round(stat.st_size / 1024, 1)
        info["fg_model"]["modified"] = datetime.fromtimestamp(stat.st_mtime).isoformat()
    
    if info["time_model"]["exists"]:
        stat = os.stat(TIME_MODEL_PATH)
        info["time_model"]["size_kb"] = round(stat.st_size / 1024, 1)
        info["time_model"]["modified"] = datetime.fromtimestamp(stat.st_mtime).isoformat()
    
    return info
