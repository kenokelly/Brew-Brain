"""
Feature Engineering Module for Brew Brain ML Pipeline

Extracts and calculates features from fermentation data for ML training.
"""

import logging
import numpy as np
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from app.core.influx import query_api, INFLUX_BUCKET

logger = logging.getLogger(__name__)


def calculate_sg_velocity(sg_readings: List[float], timestamps: List[datetime]) -> float:
    """
    Calculate SG velocity (points dropped per day).
    
    Args:
        sg_readings: List of SG values
        timestamps: Corresponding timestamps
        
    Returns:
        Average points per day (positive = fermenting)
    """
    if len(sg_readings) < 2 or len(timestamps) < 2:
        return 0.0
    
    try:
        # Calculate time span in days
        time_span = (timestamps[-1] - timestamps[0]).total_seconds() / 86400.0
        if time_span <= 0:
            return 0.0
        
        # Calculate SG drop in points (1 point = 0.001)
        sg_drop = (sg_readings[0] - sg_readings[-1]) * 1000
        velocity = sg_drop / time_span
        
        return round(velocity, 2)
    except Exception as e:
        logger.error(f"SG velocity calculation error: {e}")
        return 0.0


def calculate_temp_variance(temp_readings: List[float]) -> float:
    """
    Calculate temperature variance (standard deviation).
    
    Args:
        temp_readings: List of temperature values
        
    Returns:
        Standard deviation in degrees
    """
    if len(temp_readings) < 2:
        return 0.0
    
    try:
        return round(float(np.std(temp_readings)), 2)
    except Exception as e:
        logger.error(f"Temp variance calculation error: {e}")
        return 0.0


def calculate_time_in_phase(start_time: datetime, end_time: Optional[datetime] = None) -> float:
    """
    Calculate days in fermentation phase.
    
    Args:
        start_time: Fermentation start time
        end_time: Fermentation end time (defaults to now)
        
    Returns:
        Days elapsed
    """
    if end_time is None:
        end_time = datetime.now(timezone.utc)
    
    try:
        delta = end_time - start_time
        return round(delta.total_seconds() / 86400.0, 1)
    except Exception as e:
        logger.error(f"Time calculation error: {e}")
        return 0.0


def query_batch_data(start_time: datetime, end_time: datetime) -> Dict[str, Any]:
    """
    Query InfluxDB for batch sensor data within a time range.
    
    Args:
        start_time: Start of batch
        end_time: End of batch
        
    Returns:
        Dict with temp_readings, sg_readings, timestamps
    """
    try:
        # Format times for Flux query
        start_str = start_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_str = end_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        # Query temperature data
        temp_query = f'''
        from(bucket: "{INFLUX_BUCKET}")
            |> range(start: {start_str}, stop: {end_str})
            |> filter(fn: (r) => r["_measurement"] == "sensor_data")
            |> filter(fn: (r) => r["_field"] == "Temp")
        '''
        temp_tables = query_api.query(temp_query)
        
        temp_readings = []
        temp_times = []
        for table in temp_tables:
            for record in table.records:
                temp_readings.append(record.get_value())
                temp_times.append(record.get_time())
        
        # Query SG data
        sg_query = f'''
        from(bucket: "{INFLUX_BUCKET}")
            |> range(start: {start_str}, stop: {end_str})
            |> filter(fn: (r) => r["_measurement"] == "sensor_data")
            |> filter(fn: (r) => r["_field"] == "SG")
        '''
        sg_tables = query_api.query(sg_query)
        
        sg_readings = []
        sg_times = []
        for table in sg_tables:
            for record in table.records:
                sg_readings.append(record.get_value())
                sg_times.append(record.get_time())
        
        return {
            "temp_readings": temp_readings,
            "temp_times": temp_times,
            "sg_readings": sg_readings,
            "sg_times": sg_times,
            "data_points": len(sg_readings)
        }
        
    except Exception as e:
        logger.error(f"Batch data query error: {e}")
        return {
            "temp_readings": [],
            "temp_times": [],
            "sg_readings": [],
            "sg_times": [],
            "data_points": 0,
            "error": str(e)
        }


def extract_features_from_batch(
    batch_name: str,
    start_time: datetime,
    end_time: datetime,
    og: float,
    fg: float,
    yeast: str,
    style: str
) -> Dict[str, Any]:
    """
    Extract all features from a completed batch for ML training.
    
    Args:
        batch_name: Name of the batch
        start_time: Fermentation start
        end_time: Fermentation end
        og: Original Gravity
        fg: Final Gravity
        yeast: Yeast strain
        style: Beer style
        
    Returns:
        Dict with all calculated features
    """
    # Query sensor data
    data = query_batch_data(start_time, end_time)
    
    # Calculate features
    features = {
        "batch_name": batch_name,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "og": round(og, 3),
        "fg": round(fg, 3),
        "yeast": yeast,
        "style": style,
        
        # Calculated features
        "sg_velocity": calculate_sg_velocity(data["sg_readings"], data["sg_times"]),
        "temp_variance": calculate_temp_variance(data["temp_readings"]),
        "time_in_phase": calculate_time_in_phase(start_time, end_time),
        
        # Derived features
        "attenuation": round(((og - fg) / (og - 1.0)) * 100, 1) if og > 1.0 else 0.0,
        "abv": round((og - fg) * 131.25, 1),
        
        # Data quality
        "data_points": data["data_points"],
        "avg_temp": round(float(np.mean(data["temp_readings"])), 1) if data["temp_readings"] else 0.0,
        "min_sg": round(min(data["sg_readings"]), 3) if data["sg_readings"] else fg,
        "max_sg": round(max(data["sg_readings"]), 3) if data["sg_readings"] else og,
    }
    
    return features


def normalize_features(features: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize numerical features for ML input.
    
    Args:
        features: Raw feature dict
        
    Returns:
        Dict with normalized features
    """
    normalized = features.copy()
    
    # Normalize OG/FG to 0-1 range (typical range 1.000-1.120)
    if "og" in features:
        normalized["og_normalized"] = (features["og"] - 1.000) / 0.120
    if "fg" in features:
        normalized["fg_normalized"] = (features["fg"] - 1.000) / 0.120
    
    # Normalize temp (typical range 10-30°C)
    if "avg_temp" in features:
        normalized["temp_normalized"] = (features["avg_temp"] - 10.0) / 20.0
    
    # Normalize velocity (typical range 0-20 points/day)
    if "sg_velocity" in features:
        normalized["velocity_normalized"] = features["sg_velocity"] / 20.0
    
    return normalized
