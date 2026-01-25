"""
Batch Export Service for Brew Brain

Exports batch fermentation data to Parquet format for ML training.
Integrates InfluxDB sensor data with Brewfather metadata.
"""

import os
import logging
import base64
import requests
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from app.core.config import get_config
from app.core.influx import query_api, INFLUX_BUCKET
from app.ml.features import extract_features_from_batch

logger = logging.getLogger(__name__)

EXPORT_DIR = "data/exports"


def ensure_export_dir():
    """Create export directory if it doesn't exist."""
    os.makedirs(EXPORT_DIR, exist_ok=True)


def get_completed_batches() -> List[Dict[str, Any]]:
    """
    Query Brewfather API for completed batches.
    
    Returns:
        List of batch metadata dicts
    """
    bf_user = get_config("bf_user")
    bf_key = get_config("bf_key")
    
    if not bf_user or not bf_key:
        logger.error("Brewfather credentials not configured")
        return []
    
    try:
        auth = base64.b64encode(f"{bf_user}:{bf_key}".encode()).decode()
        url = "https://api.brewfather.app/v2/batches?status=Completed&include=recipe"
        headers = {"Authorization": f"Basic {auth}"}
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            logger.error(f"Brewfather API error: {response.status_code}")
            return []
        
        batches = response.json()
        logger.info(f"Retrieved {len(batches)} completed batches from Brewfather")
        return batches
        
    except Exception as e:
        logger.error(f"Failed to fetch completed batches: {e}")
        return []


def export_batch_to_parquet(
    batch_id: str,
    batch_name: str,
    start_time: datetime,
    end_time: datetime,
    og: float,
    fg: float,
    yeast: str,
    style: str
) -> Dict[str, Any]:
    """
    Export a single batch to Parquet format.
    
    Args:
        batch_id: Unique batch identifier
        batch_name: Batch name
        start_time: Fermentation start
        end_time: Fermentation end
        og: Original Gravity
        fg: Final Gravity
        yeast: Yeast strain
        style: Beer style
        
    Returns:
        Dict with export status and file path
    """
    ensure_export_dir()
    
    try:
        # Query sensor data from InfluxDB
        start_str = start_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_str = end_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        query = f'''
        from(bucket: "{INFLUX_BUCKET}")
            |> range(start: {start_str}, stop: {end_str})
            |> filter(fn: (r) => r["_measurement"] == "sensor_data")
            |> filter(fn: (r) => r["_field"] == "Temp" or r["_field"] == "SG")
            |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
        '''
        
        tables = query_api.query(query)
        
        # Convert to pandas DataFrame
        records = []
        for table in tables:
            for record in table.records:
                records.append({
                    "timestamp": record.get_time(),
                    "temp": record.values.get("Temp"),
                    "sg": record.values.get("SG"),
                    "batch_id": batch_id,
                    "batch_name": batch_name,
                    "yeast": yeast,
                    "style": style,
                    "og": og,
                    "fg": fg
                })
        
        if not records:
            return {
                "status": "error",
                "error": "No sensor data found for this batch"
            }
        
        df = pd.DataFrame(records)
        
        # Export to Parquet
        filename = f"{batch_id}_{batch_name.replace(' ', '_')}.parquet"
        filepath = os.path.join(EXPORT_DIR, filename)
        
        df.to_parquet(filepath, engine='pyarrow', compression='snappy')
        
        logger.info(f"Exported batch {batch_name} to {filepath} ({len(records)} records)")
        
        return {
            "status": "success",
            "filepath": filepath,
            "records": len(records),
            "size_kb": round(os.path.getsize(filepath) / 1024, 2),
            "columns": list(df.columns)
        }
        
    except Exception as e:
        logger.error(f"Batch export error: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


def aggregate_training_data(batch_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Aggregate multiple batches into a single training dataset.
    
    Args:
        batch_ids: Optional list of batch IDs to include (defaults to all)
        
    Returns:
        Dict with aggregation status and file path
    """
    ensure_export_dir()
    
    try:
        # Get all Parquet files in export directory
        parquet_files = [
            os.path.join(EXPORT_DIR, f) 
            for f in os.listdir(EXPORT_DIR) 
            if f.endswith('.parquet')
        ]
        
        if not parquet_files:
            return {
                "status": "error",
                "error": "No batch exports found. Export batches first."
            }
        
        # Filter by batch_ids if provided
        if batch_ids:
            parquet_files = [
                f for f in parquet_files 
                if any(bid in f for bid in batch_ids)
            ]
        
        # Read and combine all Parquet files
        dfs = [pd.read_parquet(f) for f in parquet_files]
        combined_df = pd.concat(dfs, ignore_index=True)
        
        # Export combined dataset
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"training_data_{timestamp}.parquet"
        filepath = os.path.join(EXPORT_DIR, filename)
        
        combined_df.to_parquet(filepath, engine='pyarrow', compression='snappy')
        
        logger.info(f"Aggregated {len(parquet_files)} batches into {filepath}")
        
        return {
            "status": "success",
            "filepath": filepath,
            "batches_included": len(parquet_files),
            "total_records": len(combined_df),
            "size_kb": round(os.path.getsize(filepath) / 1024, 2),
            "unique_batches": combined_df['batch_id'].nunique()
        }
        
    except Exception as e:
        logger.error(f"Training data aggregation error: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


def get_batch_metadata_from_brewfather(batch_id: str) -> Optional[Dict[str, Any]]:
    """
    Get metadata for a specific batch from Brewfather.
    
    Args:
        batch_id: Brewfather batch ID
        
    Returns:
        Dict with batch metadata or None
    """
    bf_user = get_config("bf_user")
    bf_key = get_config("bf_key")
    
    if not bf_user or not bf_key:
        return None
    
    try:
        auth = base64.b64encode(f"{bf_user}:{bf_key}".encode()).decode()
        url = f"https://api.brewfather.app/v2/batches/{batch_id}?include=recipe"
        headers = {"Authorization": f"Basic {auth}"}
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Brewfather batch fetch error: {response.status_code}")
            return None
            
    except Exception as e:
        logger.error(f"Failed to fetch batch metadata: {e}")
        return None
