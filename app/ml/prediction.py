"""
FG Prediction Model for Brew Brain

Trains and serves XGBoost models for:
- Final Gravity prediction
- Time-to-FG prediction

Uses historical batch data from Brewfather + InfluxDB.
"""

import os
import glob
import logging
import joblib
import numpy as np
import pyarrow.parquet as pq
from datetime import datetime, timezone
from collections import defaultdict
from typing import Dict, List, Optional, Any
from ml.features import calculate_sg_velocity, calculate_temp_variance, calculate_time_in_phase, normalize_features
from core.influx import write_api, INFLUX_BUCKET, INFLUX_ORG
from influxdb_client import Point

logger = logging.getLogger(__name__)

MODEL_DIR = "data/models"
FG_MODEL_PATH = os.path.join(MODEL_DIR, "fg_predictor.joblib")
TIME_MODEL_PATH = os.path.join(MODEL_DIR, "time_predictor.joblib")
EXPORT_DIR = "data/exports"

# Encoding constants for categorical features
STYLE_MAPPING = {"IPA": 1, "Stout": 2, "Lager": 3, "Pale Ale": 4, "Wheat": 5, "Saison": 6}
YEAST_MAPPING = {"US-05": 1, "S-04": 2, "W-34/70": 3, "Nottingham": 4, "Voss Kveik": 5}

def encode_category(value: str, mapping: Dict[str, int]) -> int:
    """Encode a string value using a mapping, with fallback to 0."""
    if not value:
        return 0
    return mapping.get(value, 0)


def ensure_model_dir():
    """Create model directory if it doesn't exist."""
    os.makedirs(MODEL_DIR, exist_ok=True)


def load_training_data() -> List[Dict[str, Any]]:
    """Load latest aggregated historical batch data as list of dicts."""
    pattern = os.path.join(EXPORT_DIR, "training_data_*.parquet")
    files = glob.glob(pattern)
    if not files:
        # Fallback to individual batch files
        files = glob.glob(os.path.join(EXPORT_DIR, "*.parquet"))
        if not files:
            return []
    
    # Sort by modification time to get the latest
    files.sort(key=os.path.getmtime, reverse=True)
    try:
        table = pq.read_table(files[0])
        records = table.to_pydict()
        # Convert column-oriented dict to list of row dicts
        n = table.num_rows
        rows = []
        columns = records.keys()
        for i in range(n):
            rows.append({col: records[col][i] for col in columns})
        logger.info(f"Loaded training data from {files[0]} ({n} records)")
        return rows
    except Exception as e:
        logger.error(f"Failed to load Parquet data: {e}")
        return []


def prepare_features(data: List[Dict[str, Any]]) -> tuple:
    """
    Extract features and targets from batch history (list of dicts).
    Calculates features (velocity, variance) from raw time-series data.
    """
    if not data:
        return np.array([]), np.array([]), np.array([])

    X = []  # Features
    y_fg = []  # FG targets
    y_time = []  # Time targets
    
    # Group by batch_id to process each fermentation separately
    batches = defaultdict(list)
    for row in data:
        batches[row.get('batch_id')].append(row)
    
    for batch_id, rows in batches.items():
        try:
            # Sort by timestamp
            rows.sort(key=lambda r: r.get('timestamp', ''))
            
            # Extract basic metadata from first row
            first = rows[0]
            og = first.get('og')
            fg = first.get('fg')
            yeast = first.get('yeast', 'Unknown')
            style = first.get('style', 'Unknown')
            
            if og is None or fg is None:
                continue
            # Check for NaN (works for both int/float)
            try:
                if og != og or fg != fg:  # NaN != NaN
                    continue
            except TypeError:
                continue

            # Calculate engineering features from raw data
            temp_readings = [r['temp'] for r in rows if r.get('temp') is not None]
            sg_readings = [r['sg'] for r in rows if r.get('sg') is not None]
            timestamps = [r['timestamp'] for r in rows]
            
            if len(sg_readings) < 10 or len(temp_readings) < 10:
                continue

            # Features: OG, sg_velocity, temp_variance, avg_temp
            velocity = calculate_sg_velocity(sg_readings, timestamps)
            variance = calculate_temp_variance(temp_readings)
            avg_temp = float(np.mean(temp_readings))
            
            # Normalization
            feat_dict = {
                "og": og,
                "avg_temp": avg_temp,
                "sg_velocity": velocity
            }
            norm_feat = normalize_features(feat_dict)
            
            # Categorical encoding
            style_code = encode_category(style, STYLE_MAPPING)
            yeast_code = encode_category(yeast, YEAST_MAPPING)
            
            # Calculate days to FG (time from pitch to when SG reaches FG +/- 0.001)
            pitch_time = timestamps[0]
            fg_time = None
            for r in rows:
                if r.get('sg') is not None and r['sg'] <= fg + 0.001:
                    fg_time = r['timestamp']
                    break
            
            if fg_time is None:
                days_to_fg = calculate_time_in_phase(pitch_time, timestamps[-1])
            else:
                days_to_fg = calculate_time_in_phase(pitch_time, fg_time)

            features = [
                float(norm_feat.get("og_normalized", 0)),
                float(norm_feat.get("velocity_normalized", 0)),
                float(norm_feat.get("temp_normalized", 0)),
                float(variance),
                float(style_code),
                float(yeast_code)
            ]
            
            X.append(features)
            y_fg.append(float(fg))
            y_time.append(float(days_to_fg))
            
        except Exception as e:
            logger.debug(f"Skipping batch {batch_id}: {e}")
            continue
    
    return np.array(X), np.array(y_fg), np.array(y_time)


def train_models() -> Dict[str, Any]:
    """
    Train FG and time-to-FG prediction models using Gradient Boosting.
    
    Returns dict with training metrics.
    """
    from sklearn.ensemble import GradientBoostingRegressor
    from sklearn.model_selection import cross_val_score
    
    ensure_model_dir()
    
    # Load data
    data = load_training_data()
    if not data:
        return {"error": "No training data found in data/exports/*.parquet"}
    
    X, y_fg, y_time = prepare_features(data)
    
    if len(X) < 5:
        return {"error": f"Need at least 5 valid batches, got {len(X)}"}
    
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
    
    # Log metrics to InfluxDB for Grafana alerting
    try:
        p = Point("ml_metrics") \
            .field("fg_mae", float(fg_mae)) \
            .field("time_mae", float(time_mae)) \
            .field("batches_used", int(len(X))) \
            .time(datetime.now(timezone.utc))
        write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=p)
        logger.info("ML metrics logged to InfluxDB")
    except Exception as e:
        logger.error(f"Failed to log ML metrics: {e}")

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


def predict_fg(og: float, velocity: float = 0.0, variance: float = 0.0, avg_temp: float = 20.0, style: str = "Unknown", yeast: str = "Unknown") -> Dict[str, Any]:
    """
    Predict Final Gravity for a batch.
    """
    # Check if model exists
    if not os.path.exists(FG_MODEL_PATH):
        # Fallback to simple calculation (assuming 75% attenuation)
        attenuation = 75.0
        predicted_fg = og - ((attenuation / 100.0) * (og - 1.0))
        return {
            "predicted_fg": round(float(predicted_fg), 3),
            "predicted_abv": round(float((og - predicted_fg) * 131.25), 1),
            "method": "formula",
            "confidence": "low"
        }
    
    try:
        model = joblib.load(FG_MODEL_PATH)
        
        # Consistent feature engineering
        feat_dict = {"og": og, "avg_temp": avg_temp, "sg_velocity": velocity}
        norm_feat = normalize_features(feat_dict)
        style_code = encode_category(style, STYLE_MAPPING)
        yeast_code = encode_category(yeast, YEAST_MAPPING)
        
        features = np.array([[
            float(norm_feat.get("og_normalized", 0)),
            float(norm_feat.get("velocity_normalized", 0)),
            float(norm_feat.get("temp_normalized", 0)),
            float(variance),
            float(style_code),
            float(yeast_code)
        ]])
        
        predicted_fg = model.predict(features)[0]
        predicted_fg = max(0.990, min(predicted_fg, og - 0.005))
        
        return {
            "predicted_fg": round(float(predicted_fg), 3),
            "predicted_abv": round(float((og - predicted_fg) * 131.25), 1),
            "method": "ml_model",
            "confidence": "high"
        }
    except Exception as e:
        logger.error(f"FG prediction failed: {e}")
        return {"error": str(e)}


def predict_time_to_fg(og: float, velocity: float = 0.0, variance: float = 0.0, avg_temp: float = 20.0, days_elapsed: float = 0, style: str = "Unknown", yeast: str = "Unknown") -> Dict[str, Any]:
    """
    Predict days remaining until Final Gravity is reached.
    """
    if not os.path.exists(TIME_MODEL_PATH):
        # Fallback
        days_remaining = max(1, 7 - days_elapsed)
        return {
            "days_remaining": round(float(days_remaining), 1),
            "method": "formula",
            "confidence": "low"
        }
    
    try:
        model = joblib.load(TIME_MODEL_PATH)
        
        # Consistent feature engineering
        feat_dict = {"og": og, "avg_temp": avg_temp, "sg_velocity": velocity}
        norm_feat = normalize_features(feat_dict)
        style_code = encode_category(style, STYLE_MAPPING)
        yeast_code = encode_category(yeast, YEAST_MAPPING)
        
        features = np.array([[
            float(norm_feat.get("og_normalized", 0)),
            float(norm_feat.get("velocity_normalized", 0)),
            float(norm_feat.get("temp_normalized", 0)),
            float(variance),
            float(style_code),
            float(yeast_code)
        ]])
        
        total_days = model.predict(features)[0]
        days_remaining = max(0.5, total_days - days_elapsed)
        
        return {
            "days_remaining": round(float(days_remaining), 1),
            "total_estimated_days": round(float(total_days), 1),
            "method": "ml_model",
            "confidence": "high"
        }
    except Exception as e:
        logger.error(f"Time prediction failed: {e}")
        return {"error": str(e)}


def get_model_info() -> Dict[str, Any]:
    """Get information about trained models."""

    
    training_data = load_training_data()
    
    # Count unique batch IDs
    batch_ids_set = set()
    for row in training_data:
        bid = row.get('batch_id')
        if bid is not None:
            batch_ids_set.add(bid)
    
    info = {
        "fg_model": {"exists": os.path.exists(FG_MODEL_PATH)},
        "time_model": {"exists": os.path.exists(TIME_MODEL_PATH)},
        "training_records": len(training_data),
        "unique_batches": len(batch_ids_set)
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
