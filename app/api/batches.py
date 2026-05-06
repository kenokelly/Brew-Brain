import base64
import requests
from datetime import datetime, timezone
from typing import Tuple, Response
from flask import Blueprint, request, send_file
from app.core.config import get_config, set_config, logger
from app.core.auth import require_api_token
from app.api.routes import api_response, handle_error

batches_bp = Blueprint('batches', __name__)

@batches_bp.route('/api/sync_brewfather', methods=['POST'])
@require_api_token
def sync_brewfather() -> Tuple[Response, int]:
    u, k = get_config("bf_user"), get_config("bf_key")
    if not u or not k: 
        return api_response(status="error", error="Missing Credentials", code=400)
    
    try:
        auth = base64.b64encode(f"{u}:{k}".encode()).decode()
        r = requests.get("https://api.brewfather.app/v2/batches?status=Fermenting&include=recipe", headers={"Authorization": f"Basic {auth}"}, timeout=10)
        
        if r.status_code != 200: 
            return api_response(status="error", error=f"API Error {r.status_code}", code=400)
        
        batches = r.json()
        if not batches: 
            return api_response(status="error", error="No Fermenting batch found", code=404)
        
        b = batches[0]
        rec = b.get('recipe', {})
        date_str = b.get('brewDate', datetime.now().strftime("%Y-%m-%d"))
        if isinstance(date_str, int): date_str = datetime.fromtimestamp(date_str/1000).strftime("%Y-%m-%d")
        
        # Capture Yeast
        yeasts = rec.get('yeasts', [])
        yeast_name = "Unknown"
        if yeasts and len(yeasts) > 0:
            y = yeasts[0]
            yeast_name = y.get('name', 'Unknown')
            # Extract Metadata
            set_config("yeast_min_temp", y.get('minTemp'))
            set_config("yeast_max_temp", y.get('maxTemp'))
            set_config("yeast_attenuation", y.get('attenuation'))
            set_config("yeast_flocculation", y.get('flocculation'))
        
        # Ensure global yeast_strain is set even if not found in yeast array
        set_config("yeast_strain", yeast_name)
        
        set_config("batch_name", b.get('name'))
        set_config("og", rec.get('og'))
        set_config("target_fg", rec.get('fg'))
        set_config("batch_notes", b.get('notes') or rec.get('notes'))
        set_config("start_date", date_str)
        set_config("yeast_strain", yeast_name)
        
        # Capture Style
        style_obj = rec.get('style', {})
        style_name_val = style_obj.get('name') or "Unknown"
        set_config("style", style_name_val)
        
        return api_response(status="synced", data={"name": b.get('name'), "style": style_name_val, "yeast": yeast_name})
            
    except Exception as e:
        return handle_error(e, "Sync Error")

@batches_bp.route('/api/export/batch/<batch_id>', methods=['GET'])
def export_batch(batch_id: str) -> Tuple[Response, int]:
    """
    Export a batch to Parquet format for ML training.
    Requires batch metadata in query params or fetches from Brewfather.
    """
    try:
        from app.services.batch_exporter import export_batch_to_parquet, get_batch_metadata_from_brewfather
        from datetime import datetime
        
        # Try to get metadata from Brewfather
        metadata = get_batch_metadata_from_brewfather(batch_id)
        
        if not metadata:
            return api_response(status="error", error="Batch not found in Brewfather", code=404)
        
        # Extract required fields
        batch_name = metadata.get('name', 'Unknown')
        recipe = metadata.get('recipe', {})
        
        # Parse dates
        brew_date = metadata.get('brewDate')
        if isinstance(brew_date, int):
            start_time = datetime.fromtimestamp(brew_date / 1000)
        else:
            start_time = datetime.fromisoformat(brew_date) if brew_date else datetime.now()
        
        # Use bottling date as end time, or now if not bottled
        bottling_date = metadata.get('bottlingDate')
        if bottling_date:
            if isinstance(bottling_date, int):
                end_time = datetime.fromtimestamp(bottling_date / 1000)
            else:
                end_time = datetime.fromisoformat(bottling_date)
        else:
            end_time = datetime.now()
        
        og = recipe.get('og', 1.050)
        fg = recipe.get('fg', 1.010)
        
        # Get yeast
        yeasts = recipe.get('yeasts', [])
        yeast = yeasts[0].get('name', 'Unknown') if yeasts else 'Unknown'
        
        style = recipe.get('style', {}).get('name', 'Unknown')
        
        # Export to Parquet
        result = export_batch_to_parquet(
            batch_id=batch_id,
            batch_name=batch_name,
            start_time=start_time,
            end_time=end_time,
            og=og,
            fg=fg,
            yeast=yeast,
            style=style
        )
        
        if result.get('status') == 'success':
            # Return the Parquet file
            return send_file(
                result['filepath'],
                mimetype='application/octet-stream',
                as_attachment=True,
                download_name=f"{batch_name}.parquet"
            )
        else:
            return api_response(status="error", error=result.get('error'), code=500)
            
    except Exception as e:
        return handle_error(e, "Batch Export Error")

@batches_bp.route('/api/batches/history', methods=['GET'])
def batches_history() -> Tuple[Response, int]:
    """
    List all completed batches from Brewfather.
    """
    try:
        from app.services.batch_exporter import get_completed_batches
        
        batches = get_completed_batches()
        
        # Format response
        formatted = []
        for batch in batches:
            formatted.append({
                "id": batch.get('_id'),
                "name": batch.get('name'),
                "status": batch.get('status'),
                "brewDate": batch.get('brewDate'),
                "style": batch.get('recipe', {}).get('style', {}).get('name')
            })
        
        return api_response(data={"batches": formatted, "count": len(formatted)})
        
    except Exception as e:
        return handle_error(e, "Batch History Error")

@batches_bp.route('/api/batches/aggregate', methods=['POST'])
def aggregate_batches() -> Tuple[Response, int]:
    """
    Aggregate multiple batches into a single training dataset.
    
    Request body (optional):
        {"batch_ids": ["id1", "id2", ...]}
    """
    try:
        from app.services.batch_exporter import aggregate_training_data
        
        data = request.json or {}
        batch_ids = data.get('batch_ids')
        
        result = aggregate_training_data(batch_ids)
        
        if result.get('status') == 'success':
            return api_response(data=result)
        else:
            return api_response(status="error", error=result.get('error'), code=500)
            
    except Exception as e:
        return handle_error(e, "Batch Aggregation Error")

@batches_bp.route('/features/<batch_id>', methods=['GET'])
def batch_features(batch_id: str) -> Tuple[Response, int]:
    """
    Extract features from a batch for ML training.
    """
    try:
        from services.batch_exporter import get_batch_metadata_from_brewfather
        from ml.features import extract_features_from_batch
        from datetime import datetime
        
        # Get metadata
        metadata = get_batch_metadata_from_brewfather(batch_id)
        
        if not metadata:
            return api_response(status="error", error="Batch not found", code=404)
        
        # Extract fields (similar to export_batch)
        batch_name = metadata.get('name', 'Unknown')
        recipe = metadata.get('recipe', {})
        
        brew_date = metadata.get('brewDate')
        if isinstance(brew_date, int):
            start_time = datetime.fromtimestamp(brew_date / 1000)
        else:
            start_time = datetime.fromisoformat(brew_date) if brew_date else datetime.now()
        
        bottling_date = metadata.get('bottlingDate')
        if bottling_date:
            if isinstance(bottling_date, int):
                end_time = datetime.fromtimestamp(bottling_date / 1000)
            else:
                end_time = datetime.fromisoformat(bottling_date)
        else:
            end_time = datetime.now()
        
        og = recipe.get('og', 1.050)
        fg = recipe.get('fg', 1.010)
        yeasts = recipe.get('yeasts', [])
        yeast = yeasts[0].get('name', 'Unknown') if yeasts else 'Unknown'
        style = recipe.get('style', {}).get('name', 'Unknown')
        
        # Extract features
        features = extract_features_from_batch(
            batch_name=batch_name,
            start_time=start_time,
            end_time=end_time,
            og=og,
            fg=fg,
            yeast=yeast,
            style=style
        )
        
        return api_response(data=features)
        
    except Exception as e:
        return handle_error(e, "Feature Extraction Error")
r")
)
r")
